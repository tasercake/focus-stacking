# Candidate-base audit

Read-only inspection on **2026-11-15**. No changes to either upstream project, build, algorithm run, quality comparison, or precision round-trip test were performed. Findings describe the pinned paths inspected, not every possible application/API configuration.

| Item | ChimpStackr | focus-stack |
|---|---|---|
| Revision | `49490aeff420fc031cec94e7b91e8bc4cc1af0ca` | `0cd289e224fe24aead5b146faeaa46950775f346` |
| Main implementation | Python, NumPy/OpenCV/Numba; OpenCL path | C++/OpenCV; OpenCL wavelets |
| Inspected license | GPL-3.0, full file preserved in `../sources/` | MIT, full file preserved in `../sources/` |
| Fusion choices | Laplacian pyramid, Hybrid, weighted average, sharpness/source selection; exposure fusion is a separate control | Complex-wavelet merge, consistency/denoising, color reassignment |
| Alignment | Several global modes; neighboring transform chain for breathing | Neighboring affine ECC by default; global-reference option; photometric matching |
| Photographic sample precision | High-bit-depth samples converted to float32 without an immediate uint8 image round trip | Inspected file-loading and color-reassignment path is explicitly 8-bit |
| Stack-length strategy | Streaming cores and optional recursive slabs; concurrent load/prepare | Task graph, batched wavelet merge and compact color map |
| Strong research advantage | Accessible Python experimentation across multiple method families | Distinct, interpretable wavelet baseline with a compact compiled pipeline |
| Main quality concerns to test | Pairwise accumulation/order; tone mapping; first-frame noise estimates; slab changes; registration validity | Precision floor; halo/color reassignment behavior; grayscale focus representation; batch/consistency sensitivity |

## 1. ChimpStackr: verified implementation facts

**Input precision.** [ImageLoadingHandler.py](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/ImageLoadingHandler.py#L143) reads regular photographic data with `IMREAD_UNCHANGED`. Its uint16-to-float32 scaling maps the sample range to 0–255 without reducing the number of sample levels to 256. [RAW processing](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/ImageLoadingHandler.py#L254) requests `output_bps=16` and disables auto brightening. This supports a useful native-precision path, but does not establish a fixed linear-light, color-managed, or unbounded-HDR contract. No explicit linear gamma is specified there. Float range inference uses a small sample; RAW failure can fall back to embedded preview/ordinary postprocessing. These paths need qualification before benchmark use.

**Pyramid fusion and rendering.** [API `_laplacian_core`](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L362) repeatedly merges each new source pyramid with the accumulated pyramid. This is not a simultaneous maximum over independently measured original frames. [The output path](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L425) applies local tone mapping at strength 0.3. [CPU `local_tone_map`](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/stacking_algorithms/cpu.py#L211) clips to 0–255, transforms through float LAB, and interpolates CLAHE lookup curves. The histogram bins are uint8, but the image output is float32; it would be incorrect to call this an ordinary uint8 image round trip. It still deliberately changes radiometry and clips headroom.

**Hybrid.** [HybridAccumulator](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/stacking_algorithms/cpu.py#L392) accumulates weighted coefficients and independent per-frame local-variance maxima. Noise/background estimates are initialized from the first added frame. Fine detail has a default 0.08 gain. Inference: image reversal, exposure/noise changes in the first frame, and gain-off output are relevant controls. The documentation's halo-free descriptions are hypotheses to test, not guarantees established by this code inspection.

**Weighted and depth methods.** [Weighted accumulation](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L858) uses float64 sums before final float32 division. [The depth-map core](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L932) keeps the pixel with the best smoothed multiscale sharpness; it sets `self.depth_map = None` on completion. A method called depth_map therefore does not, in this path, provide an exported depth or source-index map suitable for scoring. Do not mistake an unused helper function for this active implementation.

**Geometry and slabs.** [Sequential warps](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L255) use Lanczos and replicated borders; these can preserve detail but replicated pixels are not observed scene coverage. [Slabbing](https://github.com/noah-peeters/ChimpStackr/blob/49490aeff420fc031cec94e7b91e8bc4cc1af0ca/src/algorithms/API.py#L487) fuses slab results again. CPU slabs use float32 temporary arrays, with a final pyramid tone map where applicable. Inference: overlap does not mathematically guarantee equivalence to a single full-stack pass or the absence of seams. Slab size/overlap are method parameters.

GPU behavior was documented but not fully traced or numerically checked. CPU/GPU path, auto device choice, fallback, interpolation, and output type must be recorded; an upstream parity claim is not independent validation.

## 2. focus-stack: verified implementation facts

**Actual sample precision.** [Task_LoadImg](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_loadimg.cc#L53) uses `cv::IMREAD_ANYCOLOR`, without `IMREAD_ANYDEPTH`. More decisively, [color-map construction](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_reassign.cc#L49) requires `CV_8U` gray and `CV_8UC3` color, and [reassignment output](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_reassign.cc#L186) allocates `CV_8UC3`. Supporting a TIFF filename does not establish preservation of 16-bit sample precision. Float wavelet coefficients and a 16-bit depth/index map do not change that color-output contract.

**Alignment and photometry.** [Task_Align](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_align.cc#L271) uses affine ECC; [resampling](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_align.cc#L405) uses cubic interpolation and reflected borders. The [algorithm documentation](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/docs/Algorithms.md) describes default neighboring alignment and exposure/white-balance matching. Thus “source value” in later reassignment means an aligned, potentially photometrically changed source sample, not an unchanged camera measurement.

**Merge and color.** [Task_Merge](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_merge.cc#L20) selects maximum-magnitude complex coefficients, then applies subband and neighbor consistency at enabled levels. Its persistent state is merged between batches. The documentation explicitly acknowledges halo trouble and that color reassignment can make halos more conspicuous when a good color match does not exist. That is direct upstream evidence of a failure mode, not a new measured defect rate. Its depth-map visualization branch is separate from the main fused-color reconstruction.

**Memory and order.** Batched processing and compact grayscale-to-color entries avoid retaining all full-color frames indefinitely. The README gives memory estimates, but these were not reproduced. Consistency filters, ties, batch boundaries, and denoising make order/batch invariance something to test, not assume from the raw maximum operation. Global PCA grayscale conversion and later color reassignment motivate isoluminant-color test patterns; this is an inference requiring experiments.

## 3. Provisional engineering decision

Use **ChimpStackr as the provisional experimental host** if preserving photographic precision and rapidly testing multiple fusion rules are the near-term priorities. Retain **focus-stack as an independent wavelet baseline**. Do not yet call either the better algorithm. If a permissive licensing requirement or a C++ production core later becomes decisive, reconsider the host after precision and architecture requirements are explicit.

Before a quality-based base decision, qualify five bounded items:

1. Fix external RAW conversion and color/range contract, then compare shipped native input as a separate end-to-end track.
2. Preserve pre-tone/pre-sharpen output and final delivered output as separate measured stages where interfaces allow it.
3. Run both with identical supplied registration, and separately test their native alignment with coverage masks.
4. Test order, frame count, noise, slab/batch size, CPU/GPU path, and parameter sensitivity on the same independent scenes.
5. Verify high-bit-depth ramps, dark gradients, highlights, and export round trips before accepting a 16-bit label.

These are proposed qualification checks. No implementation changes or experiment results are claimed. Source snapshots record exactly what was read; upstream links and immutable revisions remain the owning evidence.
