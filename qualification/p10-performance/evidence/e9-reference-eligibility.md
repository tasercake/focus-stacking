# E9 reference eligibility and correction plan

The [frozen E9 specification](../../../pancake/docs/performance-targets.json)
requires `4+4+1` exposures and equal final weights for the three batch
results. The measured `12f2151` Pancake implementation reconstructs each
batch, adds its float32 image to a running sum, and divides by the batch
count. The measured pinned ChimpStackr CPU and OpenCL implementations group
the nine frames correctly and use a second content-weighted Mertens fusion
to combine the resulting three images. Their final aggregation does not meet
the frozen equal-weight requirement.

## Verified source and retained outputs

All three retained E9 campaigns used reference `ab7a92708269c01c6094729f6cdfaf1415677364`,
the pinned Python lock and the ordinary `python -m src.cli` entry. The archive
reports show the `exposure_fusion` method with explicit `--cpu` or `--gpu`
selection. The benchmark launcher selects the camera-corrected wrapper only
for R50. There is no equal-weight override in the E9 invocation.
[Reference descriptor](../../../pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference/chimpstackr.toml) ·
[Launcher and selection](../p10.py) · [CPU and Vulkan receipts](integrated-e9-12f2151/README.md) ·
[CUDA and OpenCL receipts](integrated-e9-cuda-12f2151/README.md)

- CPU `LaplacianPyramid._exposure_core` calls `CPU.mertens_fuse_batch` for each
  four-image group and retains the last singleton. It calls the same Mertens
  function again on the three intermediate images. That function recomputes
  contrast and saturation from those arrays and normalizes the resulting
  weights through the pyramid. [Pinned CPU batch path](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/API.py#L1044-L1077) ·
  [Pinned CPU batch kernel](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/stacking_algorithms/cpu.py#L648-L685)
- The pinned GPU dispatch constructs `ExposureGPU` with the same group size.
  Its `_flush` implements group reconstruction and singleton passthrough.
  `result()` calls `merge` on the three uploaded partials, again evaluating
  the content-dependent weighting kernels. The archived GPU diagnostics
  confirm actual OpenCL execution for those launches.
  [Pinned GPU dispatch](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/API.py#L714-L729) ·
  [Pinned OpenCL batch and final merger](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/stacking_algorithms/ocl.py#L1287-L1378)
- Pancake's `AdvancedAccumulator::finish` and `finish_exposure_batch` use the shared
  CubeCL `accumulate_batch` and `average_batches` kernels. The same tree
  applies to CPU, Vulkan and CUDA. The inspected historical source is
  `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f`.
  [Exposure tree](../../../pancake/src/fusion/advanced/mod.rs) ·
  [Equal accumulation and division](../../../pancake/src/fusion/advanced/levels.rs)

The retained exports were genuine 337 × 510 RGB16 in all lanes. Full-image
Pancake/reference MAE was 2,823.78 u16 codes on CPU and about 2,825.18 on the
GPU comparisons. The matching-geometry exports differed in all three
reviewed regions. Attributing the error requires the intermediate partials
and a controlled comparison. The recorded timings and telemetry remain
historical diagnostics under the documented algorithm mismatch, including
the original numeric misses. [CPU region review](integrated-e9-12f2151/cpu-review.json) ·
[Vulkan region review](integrated-e9-12f2151/vulkan-review.json) ·
[CUDA region review](integrated-e9-cuda-12f2151/cuda-review.json)

## Separate color convention

The reference's normal PNG path supplies BGR working data. CPU applies
`COLOR_RGB2GRAY` to that data. OpenCL applies the same storage-index
coefficients `0.299, 0.587, 0.114`. In named RGB primaries both actions
therefore measure `0.114R + 0.587G + 0.299B` before the contrast calculation.
The exact Pancake implementation measures `0.299R + 0.587G + 0.114B` in RGB
storage order. This changes within-batch contrast weighting independently
of the final combine. Matching a canonical RGB luma convention would require
changing the weight input in both reference backends. The frozen final-weight
requirement can be enforced without changing the pinned per-batch color
behavior. Any color convention change needs separate evidence and review.
[Reference input order](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/ImageLoadingHandler.py#L145-L212) ·
[OpenCL luma](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/stacking_algorithms/ocl.py#L397-L434) ·
[Pancake RGB weights](../../../pancake/src/fusion/advanced/weights.rs) ·
[OpenCV conversion definition](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html)

## Test-first launcher plan

Use a scoped E9 reference launcher under the allowed Pancake adapter, selected
only by the qualification runner for the E9 exposure-fusion profile. Invoke
the pinned `src.cli` in the measured reference process with the same ordered
native inputs, alignment, crop, writer, backend selection, caches and exit
contract. Record the launcher hash alongside the untouched reference commit,
descriptor and runtime lock. Keep the correction within the E9 launcher
and the qualification runner's dispatch.

1. **CPU.** Substitute a scoped `_exposure_core` implementation with the
   same batching, pause, cancellation, progress and singleton behavior. Call
   the actual pinned `CPU.mertens_fuse_batch` on each multisample group. Add
   each reconstructed image once and divide by the number of batches in
   float32. A length-based interception of `mertens_fuse_batch` could confuse
   an incomplete source batch with the final merge. Keep the interception at
   this API boundary.
2. **OpenCL.** Scope the substitution to `ExposureGPU.result`. Keep `add`,
   `_flush`, `merge`, singleton passthrough, and the reference upload path.
   Sum the partials on the existing OpenCL queue using supported device-array
   arithmetic and divide by their count there. The normal result path then
   crops and exports the same type of device result. This keeps the equal
   combine in the explicitly selected GPU path.
3. **Meaningful failing witnesses before code.** Hold three distinct,
   already reconstructed partials fixed. Values 20, 80 and 200 must give
   100 per channel under equal batch weights. Counting original exposures
   again would give 66⅔. For a nonconstant witness, use a red/green
   checkerboard, a constant blue image and a constant black image as the
   three partials. With RGB values in 0–255, their mean is `(85, 0, 85)`
   at red pixels and `(0, 85, 85)` at green pixels. Under the stock BGR
   contrast convention, the checkerboard has unit-scale four-neighbor
   Laplacian magnitude `4 × (0.587 − 0.114) = 1.892` before saturation
   weighting. The two constant partials have zero contrast and only the
   epsilon weight, so a second Mertens merge favors the checkerboard.
   Check generic incomplete groups, the singleton-only path, input order,
   unchanged calls into the pinned batch functions, and physical OpenCL
   dispatch when a later device check is authorized.

For the independent real-input check, capture the registered full working
canvas and reconstructed pre-export partials from the exact nine originals.
Compute the expected per-channel mean independently in a wider accumulator
and compare both launcher paths before applying the common output crop and
RGB16 quantization. Use the same crop afterward for region and whole-image
comparison. To attribute the color contribution, hold registration, source
bytes, batch order, border/pyramid operations and final combiner fixed while
varying only luma storage semantics in an independent diagnostic. Derive
the expected contrast response from separate red and blue edge controls.
Record intermediate arrays or hashes and the original pinned-output control.
Only the unchanged frozen quality checks govern a later qualification.

This is a source and receipt audit with a test plan. The launcher correction,
independent recomputation and qualification have not run.
