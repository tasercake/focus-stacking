# Numerical conformance contract

The algorithm suite executes target CLI processes. It never imports application
modules, calls algorithm classes, mocks their internals, or runs the target's
internal unit tests. Target argument syntax belongs to the target descriptor.
Generated fixtures and image validators are shared across implementations.

## Coverage of observable behavior

The catalog covers all five stacking methods; odd dimensions; all five alignment
modes; first, middle and previous references; sequential high precision; the
legacy rotation/scale switch; automatic parameters and crop; custom kernels and
pyramid levels; slab boundaries, overlap, and aligned slabs; deterministic repeat
runs; grayscale, alpha, mixed formats, non-ASCII paths, normalized and unnormalized
float TIFF, float EXR, 16-bit grayscale, generated Bayer DNG, mixed input
dimensions, and EXIF orientations 2–8; JPEG, PNG, TIFF,
and float EXR export; real 16-bit RGB precision; and cross-format decoded-pixel
parity. CPU/GPU selection and backend parity have their own device suite.

Inputs are generated on demand. The fixture manifest records generator version,
shape, dtype, count, selected regions, and known geometry transforms. There are
no source photographs or downloaded image fixtures. The locked dependency set
is part of the reference environment. These synthetic scenes cannot establish
quality on every real photograph or reproduce all camera RAW decoder behavior.

## Independent oracles

Pillow generates 8-bit images and EXIF data; tifffile writes uncompressed TIFF;
OpenEXR writes float EXR. PNG decoding uses pypng so RGB16 is never silently
reduced to eight bits. TIFF decoding uses tifffile and imagecodecs. Float export
is decoded through OpenEXR. Validators use RGB channel order, independent of
any target's internal channel order.

Tests check structure before numerical error. Focus quality is measured in both
focus planes, not only over the full image. Each region must retain at least 65%
of its all-in-focus truth's Laplacian variance. The global focus error budget is
15 code values on an 8-bit scale. This budget permits the reference's deliberate
Laplacian tone mapping and Hybrid detail boost; it does not imply pixel identity
between different methods. A selected source alone fails the second focus-plane
check. Frozen baseline comparison supplies a tighter per-case regression check.

Alignment quality uses independently generated transforms, blurred RGB residuals
inside a border-free region, and a mean-error limit of 3 code values for weighted
average with the first frame as reference. Geometry scenes contain weak texture
throughout each region so this test does not accidentally combine alignment with
the separate zero-contrast weighted-average defect.

Mixed-dimension inputs contain a fine checker that necessarily changes sampling
phase when resized. These tests require first-frame output coordinates and
compare Gaussian-blurred interior residuals rather than treating resampled fine
texture as pixel-identical ground truth. Mean error limits are 10 code values
for Laplacian tone mapping and 3 for the other methods; observed reference values
were 7.10, 0.20, 1.06, 0, and 2.06 respectively. Full-resolution error is retained
in report notes and full-resolution pixels remain subject to frozen baselines.

Identical 16-bit gradient sources contain values not restricted to multiples of
257 and substantially more than 256 levels. Four focus methods must preserve
real 16-bit output precision. Weighted average and depth map must round-trip
within one 16-bit code value. Hybrid permits its documented contrast boost.
PNG16 and TIFF16 outputs must decode to identical pixels for the same method.

CPU repeat runs are pixel-exact except exposure fusion. Mertens floating-point
reductions produced isolated one-code-value differences during repeated reference
runs. Its repeat budget is maximum error 1, mean error 0.001, and at most 0.1% of
pixels differing. This is a numerical reproducibility budget, not an allowance
for alignment drift or image resampling.

The synthetic RAW fixture is a 112×160, uncompressed RGGB Bayer DNG 1.4 with
explicit CFA, black/white level, identity color matrix, neutral white balance,
and crop tags. Each file is 36,352 bytes and has no embedded thumbnail. All five
methods must decode the Bayer data to RGB at the declared dimensions. Four focus
methods must retain true 16-bit output precision. This exercises an actual
LibRaw decode without downloading camera files; it does not replace coverage of
proprietary compressed RAW formats, embedded thumbnails, or camera-specific
metadata and white-balance behavior.

Native lifecycle tests use a separate on-demand workload: 64 unique 1024×1536
RGB input paths backed by one generated PNG through hardlinks (about 2.77 MB of
image storage). Source transforms are identity. The application must still
perform its normal per-frame decoding, alignment and fusion; no artificial
sleep, processing barrier or business-operation hook extends runtime. This
fixture exists to permit real native pause/resume/cancel interaction and is not
part of the small numerical accuracy corpus.

## Explicit reference defects and limits

The suite preserves the following outcomes under identifiers containing
`compatibility`. These are characterization assertions, not image-quality
endorsements. Improving them in a future port requires an explicit contract
revision or an approved compatibility exception.

| Case family | Observed reference behavior | Contract treatment |
| --- | --- | --- |
| `compatibility.flat.weighted_average` | Identical spatially constant RGB inputs produce black. Zero contrast gives zero accumulated weights. | Requires the observed black result and records the defect. Other methods have their own constant-color assertions. |
| `compatibility.exposure_fusion_8bit_internal_precision` | Exposure fusion processes source data through 8-bit Mertens inputs. The generated RGB16 gradient yields no more than 256 distinct output values even in a uint16 container. | Requires the current quantization and records the limitation. The four focus methods retain separate true-precision tests. |
| `compatibility.input.orientation5` and `orientation7` | EXIF transpose and transverse transforms are interchanged. | Stores standards-correct generated truth, then explicitly compares to the reference's swapped result. Orientations 2, 3, 4, 6 and 8 use standards-correct truth directly. |
| `compatibility.translation_overcrop` | DFT translation on the small 257×321 texture can estimate large shifts although true drift is at most 3 pixels horizontally and 1.5 vertically. Observed crop was about 39 pixels per vertical side and 62 per horizontal side. | Preserves the problematic request and excessive-crop characterization. Separate crop-quality case uses the Euclidean estimator on the same known translations. |
| `compatibility.ambiguous_breathing_slabs.*` | Breathing alignment on the 65×99 repeated focus checker can select ambiguous transforms and lose substantial detail. | Preserves all four affected method requests, validates output structure, records truth error, and retains output for baseline comparison. Numerical aligned-slab quality uses the textured 257×321 breathing scene instead. |

The ambiguous small-checker cases deliberately do not assert that their quality
is correct. Their measured error is visible in the report. Baseline capture must
be reviewed with these known defects in mind; a baseline records behavior and
cannot establish that the reference behavior is desirable.

## Scope of coverage claims

Passing these cases establishes tested external behavior for the generated
corpus. It does not establish 100% source line or branch coverage. Coverage is
measured by optional target instrumentation and must retain unexecuted code in
its denominator. Platform-specific branches, network updater behavior, defensive
failure handlers, unexposed low-level helpers, RAW camera variants, and compiled
OpenCL/Numba bodies are not proven by these numerical scenarios alone.
