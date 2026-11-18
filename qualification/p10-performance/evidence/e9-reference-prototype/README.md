# E9 reference equal batch mean prototype

The frozen E9 profile requires nine inputs grouped `4+4+1` with equal contributions from the three batch results. The pinned ChimpStackr source `ab7a92708269c01c6094729f6cdfaf1415677364` applies another Mertens fusion to those three intermediates on both CPU and OpenCL. A red/green checker, a blue plane and a black plane make the distinction observable. Stock CPU returns RGB approximately `[255, 0, 0]` and `[0, 255, 0]` at adjacent red and green positions. Equal batch weights yield `[85, 0, 85]` and `[0, 85, 85]`. See [stock witness](stock-witness.json).

The prototype dispatches only E9 CPU and GPU qualifications through a hashed adapter. The adapter calls the pinned CLI and per-batch CPU or OpenCL implementation, then sums the batch outputs in order and divides by the count in float32. The OpenCL reduction uses the reference fuser’s existing device queue. The CPU loop retains the pin’s progress, pause, cancellation and singleton source behavior. The pinned version sorts absolute input paths, and the frozen nine paths are already in that order. Decode, registration, crop, clipping, export and diagnostics remain with the pinned CLI. The descriptor, source pin, runtime lock, case IDs and frozen thresholds are unchanged.

Within a batch, the OpenCV image pipeline supplies BGR arrays. The pinned CPU grayscale routine and the OpenCL grayscale coefficient order assign 0.299 to channel zero and 0.114 to channel two. The resulting named-color luma is `0.114 R + 0.587 G + 0.299 B`. Pancake evaluates `0.299 R + 0.587 G + 0.114 B` in RGB order. This separate per-batch weighting difference remains in the prototype. The export witness checks the BGR-to-RGB storage convention separately. [OpenCV color conversion documentation](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html)

## Functional evidence

- [CPU control](cpu-oracle.json) runs nine generated PNGs through the actual CLI with the frozen E9 flags. Two original Mertens calls consume four aligned sources each and the last aligned source passes through. The independent float64 mean agrees with the pre-crop output within `1.02e-5` on the `0–255` scale. The observed crop and independent RGB16 conversion match every decoded pixel. A direct uninstrumented launch produced the same TIFF bytes.
- The same control verifies missing path and single-image admission failures. In two late-corruption controls, the original first four-frame Mertens call completed, then the pinned decoder reported the corrupt fifth input and exited 1. The destination stayed absent in one run. In the other, a pre-existing valid TIFF remained byte-for-byte unchanged.
- [Real CPU replay](real-cpu-functional.json) runs one instrumented corrected reference job and one normal Pancake CPU job from the locked `c1e2cac` Debian package. The [input receipt](input-receipt.json) authenticates all nine original Waterloo exposures before and after the jobs. The actual pinned multisample calls consumed `4+4` and the ninth aligned image was the third partial. The maximum error versus the independent float64 mean was `1.91e-5` on the `0–255` scale. The CLI export exactly matched the independently converted and cropped reference output. Both applications emitted genuine `337×510` RGB16 with the same nine identity registration maps and a one-pixel margin on each side. Hardware was a Ryzen 9 7950X3D, Linux `6.8.0-147-generic`, CPU affinity `14,15`, with Python `3.12.3`, OpenCV `4.14.0` and NumPy `2.5.4` on the frozen reference environment.
- The real same-grid comparison was MAE `510.171`, RMS `634.898` and maximum `4999` in unsigned 16-bit sample units. The Pancake encoded and decoded hashes reproduce the earlier [stock reference comparison](../integrated-e9-12f2151/cpu-review.json), whose CPU pair MAE was `2823.781`. Review of the corrected representative regions and equal output quality remains pending. The synthetic and real receipts contain functional observations only. They supply no P10 warm, cold, memory, GUI or quality acceptance credit.

The real inputs are the Balloons exposure set by Erik Reinhard distributed in the Waterloo MEF subjective database, Image and Vision Computing Laboratory, University of Waterloo. The source page documents reuse and its attribution requirements. See Ma, Zeng and Wang, *Perceptual Quality Assessment for Multi-Exposure Image Fusion*, IEEE Transactions on Image Processing 24(11), 2015. [Source and rights](https://ivc.uwaterloo.ca/database/MEF/MEF-Database.html)

## Reproduce the CPU checks

Use the existing P10 reference environment and stage the exact corpus using the acquisition helper recorded in the input receipt. Run from the clean detached reference root at the pinned revision. `ROOT` is the repository worktree, `PRIVATE` an owned scratch directory, `REF_PY` the pinned Python, `DEB` the preserved exact Debian artifact, and `CANDIDATE` its privately extracted CLI. Create the empty `PRIVATE/empty-icd` directory to disable OpenCL selection for these CPU checks.

```sh
export PYTHONPATH="$ROOT/pancake-conformance/src:$ROOT/qualification/p10-performance:$PWD"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 NUMBA_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export NUMBA_CACHE_DIR="$PRIVATE/numba" OCL_ICD_VENDORS="$PRIVATE/empty-icd"
export XDG_CONFIG_HOME="$PRIVATE/ref-config" CHIMPSTACKR_CACHE_DIR="$PRIVATE/ref-cache"
oracle="$ROOT/qualification/p10-performance/evidence/e9-reference-prototype/verify.py.txt"
taskset -c 14,15 "$REF_PY" "$oracle"
taskset -c 14,15 "$REF_PY" "$oracle" --input-root "$PRIVATE/real/input" --candidate "$CANDIDATE" --package "$DEB"
```

To reproduce the stock arithmetic witness, build three `16×16×3` float32 BGR arrays. Set alternating positions of the first array to `[0,0,255]` and `[0,255,0]`, every pixel of the second to `[255,0,0]` and every pixel of the third to zero. Call the pin’s `src.algorithms.stacking_algorithms.cpu.mertens_fuse_batch` on these three arrays. Compare the adjacent pixels with their coordinate-wise float64 mean after reversing channels for RGB display.

The CPU verification leaves its TIFFs in temporary directories that are removed at exit. The source archive and privately extracted application binary were rehashed before removal. Nine originals were held briefly for the separately scheduled physical check. No source photos or derived TIFFs are included in the evidence.

## Physical OpenCL validation pending

Use one instrumented run and one clean, direct reference launch under an exclusive GPU lease. Identify the pinned selection’s PCI address and UUID on the same RTX 3090, verify the queue’s device and prove the CLI stayed on OpenCL. Observe actual `ExposureGPU._flush` results after `4+4+1` and evaluate their independent float64 mean against the normal pre-crop output. Verify the physical result’s registration, RGB16 encoding and BGR-to-RGB conversion. Require file and decoded pixel hashes to match the clean run with the same arguments and input hashes. Retain any fallback or disagreement as failure evidence. Physical OpenCL remains unrun in this receipt.
