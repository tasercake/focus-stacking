# Numerical conformance contract — version 2

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
dimensions, and EXIF orientations 1–8; JPEG, PNG, TIFF,
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
throughout each region. Geometry is also checked directly against generated
reference-to-source maps at corners and center, with a one-pixel maximum error.
Middle references must use middle-frame coordinates for every alignment mode.

Mixed-dimension inputs contain a fine checker that necessarily changes sampling
phase when resized. These tests require first-frame output coordinates and
compare Gaussian-blurred interior residuals rather than treating resampled fine
texture as pixel-identical ground truth. Mean error limits are 10 code values
for Laplacian tone mapping and 3 for the other methods; observed reference values
were 7.10, 0.20, 1.06, 0, and 2.06 respectively. Full-resolution error is retained
in report notes and full-resolution pixels remain subject to frozen baselines.

Identical 16-bit gradient sources contain values not restricted to multiples of
257 and substantially more than 256 levels. All five methods must preserve
real 16-bit output precision. Exposure fusion, weighted average and depth map must round-trip
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
methods must decode the Bayer data to RGB at the declared dimensions. All five
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

## Corrected behavior in version 2

Version 1 characterized six defects. Version 2 requires corrected behavior.
Generator version 2 adds orientation 1, zero-weight regions, and a small
non-repeating control; the original repeated 65×99 checker is unchanged.
Old baselines are immutable and must stay in their existing directories.
A version-1 baseline is not a version-2 quality oracle. Record a new baseline
only from cases which have passed their independent assertions.

| Version-1 family | Version-2 family | Required behavior |
| --- | --- | --- |
| `algorithms.compatibility.flat.*` | `algorithms.flat.*` | Constant source color; first source in input order supplies pixels with zero total focus weight. `weighted.zero_regions` checks zero weights inside a textured image on CPU and GPU. |
| `algorithms.compatibility.exposure_fusion_8bit_internal_precision` | `algorithms.precision16.*.exposure_fusion`, `algorithms.exposure_precision.{2,4,9}.{png,tif}` | Full floating-point samples through fusion and intermediate batches; independent identity gradient round-trip within one 16-bit code value. CPU/GPU parity has separate checks. |
| `algorithms.compatibility.input.orientation{5,7}` | `algorithms.input.orientation{5,7}` | EXIF transpose and transverse per independent Pillow truth; no compensating 180° rotation. All eight orientations use asymmetric non-square sources. |
| `algorithms.compatibility.translation_overcrop` | `algorithms.alignment.translation_bounded_crop` | Original translation-mode request; estimated matrix error ≤0.3; symmetric crop removes 2–4 vertical / 4–5 horizontal pixels per side for generated 3/-1.5px drift, including one-pixel interpolation margin and estimation rounding. |
| `algorithms.compatibility.ambiguous_breathing_slabs.*` | `algorithms.alignment.repeated_breathing_slabs.*` | All four focus methods retain original small checker and slab request; motion drift <0.3px, ≥65% focus recovery in both regions, mean truth error ≤20. Nearby non-repeating controls enforce the same geometry and detail tests. |
| `algorithms.coverage.partial_corrupt.*`, `cli.coverage.partial.*`, `devices.gpu.decode_fallback` | Strengthened partial cases and `devices.gpu.corrupt_input_rejected` / `devices.gpu.corrupt.*` | Any undecodable requested input fails the complete job, identifies input, preserves an existing export, publishes no partial output and reports no successful completion or backend fallback. All methods, all alignment modes, CPU and GPU are covered. |

`exposure_constant_mix.{4,9}` independently checks actual fusion, including a
one-frame last batch: zero contrast gives equal weights, so output equals the
analytic mean of batch means. Identity checks alone cannot detect source-only
selection. Exposure still uses four-frame batches and equal final batch weights;
it is not defined as one global mean for unequally sized batches.

Ambiguous motion uses a documented conservative fallback: identity, with zero
confidence. Alignment remains enabled. A transform needs plausible geometry,
correlation improvement and reduced detail error. Small refinements on already
well-correlated images can pass with strong detail-error reduction. No prior
motion is extrapolated into unsupported pairs. A fallback can leave real but
unidentifiable motion uncompensated; it must not invent a confident transform.

GPU-index normalization and symmetric crop policy remain unchanged. Sixteen-bit
exposure baselines now use the same strict precision tolerances as other
sixteen-bit outputs. No test requires nondeterminism or CPU/GPU differences.

Input hashes are checked after every stack call, including failed calls.
Corrupt-input rejection is not evidence of GPU runtime recovery. No portable,
repeatable real driver-failure trigger is available; that fallback-test gap
remains explicit. Injected backend errors or fabricated completion events do
not count as conformance evidence.

## Scope of coverage claims

Passing these cases establishes tested external behavior for the generated
corpus. It does not establish 100% source line or branch coverage. Coverage is
measured by optional target instrumentation and must retain unexecuted code in
its denominator. Platform-specific branches, network updater behavior, defensive
failure handlers, unexposed low-level helpers, RAW camera variants, and compiled
OpenCL/Numba bodies are not proven by these numerical scenarios alone.
