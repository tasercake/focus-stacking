# R50 evidence and residual work at e81079d

This source and receipt audit uses selected revision
`e81079dee4078d7a1149da0f5950aab8c89f8d44`. The R50 contract
requires the same 50 native Canon CR3s for four methods on explicit
CPU and explicit physical GPU. The warm cap is 0.50× the matched
reference median, the cold cap is 1.00×, and each required memory
ratio has a 0.50× cap. More recent exact E9 and T50 results describe
their own recipes and backends. [Frozen targets](../performance-targets.json)
[Profile ledger](../../../qualification/p10-performance/evidence/release-completeness.md)

| R50 method | Explicit CPU | Explicit physical GPU |
| --- | --- | --- |
| Hybrid | Historical full schedule at packaged `12f2151` | Full schedule open |
| Laplacian | Full schedule open | Full schedule open |
| Weighted average | Full schedule open | Full schedule open |
| Depth map | Full schedule open | Full schedule open |

Both targets completed 2 warmups, 10 warm profiles and 5 cold profiles
plus a separate backend witness per application in the historical
Hybrid CPU campaign. Warm medians were 94.403 s Pancake and 40.598 s
ChimpStackr (2.3253×). Cold medians were 95.290 s and 46.767 s
(2.0376×). Both speed gates failed. Process-tree RSS remains open
because the gaps exceeded 20 ms in 9/17 Pancake and 17/17 reference
samples. Both genuine RGB16 outputs shared the 5086×3390 camera-correct
crop, with 506.42 u16 mean absolute RGB difference. The cross-application
color and representative detail verdict remains open.
[Historical full schedule and image review](../../../qualification/p10-performance/evidence/integrated-r50-12f2151/README.md)

## What the later diagnostics resolve

- One packaged `287828a` forced CPU pair completed in 50.792 s for
  Pancake and 47.811 s for the corrected reference. Another diagnostic
  pair measured 51.521 s on that package and 42.072 s on `07816a2`
  after the one-copy registration upload. Separate exact-binary
  traces put thumbnail preparation at 17.206 and 7.944 s. In the
  latter trace, RAW decode took 17.808 s at 4.49 busy CPU cores,
  Hybrid frame fusion 14.219 s at 13.88 cores, and transform estimation
  0.401 s. Repeated outputs and both transform families matched their
  historical digests.
  [Package pair](../p10-r50-phase-287828a/README.md)
  [Owned-upload pair and trace](../p10-r50-phase-287828a/owned-upload/README.md)
- The four-arm CPU observation used the same authenticated R50 bytes.
  Its `07816a2` control took 39.928 s, its isolated five-buffer Hybrid
  arm took 37.024 s and its isolated RAW packing arm took 38.098 s.
  All published TIFFs and both ordered f32 map families matched.
  Hybrid used 244.96 CPU-seconds versus 292.83 for the control.
  RAW used 293.44 CPU-seconds, so its wall gain accompanied roughly
  the same total CPU use. The isolated luma lattice took 40.361 s.
  These are separate, single observations with a common control.
  Adding their gains cannot establish combined wall time.
  [Four-arm comparison](../p10-r50-component-comparison/README.md)
- The `c1e2cac` package combined the RAW and Hybrid changes and
  has its own 376-case ledger. The matched completed-job profile at
  that package is E9. The native CUDA/OpenCL and revised E9 LUT
  receipts also use nine exposures, a different method and a
  different CPU mask. The two-scan physical result uses generated
  T50 TIFFs. R50 CR3 ingestion goes through the RAW branch, so
  dropping the tiled-U16 TIFF scan does not alter its decode.
  The second scan removal applies only when Hybrid actually has
  an eligible resident RGB upload from registration. The spectral
  LUT accelerates the transform search inside registration, whose
  entire historical R50 CPU interval was about 0.4 s. These receipts
  leave exact `e81079d` R50 stage costs unmeasured.
  [Combined package](../p9-linux-package-evidence/c1e2cac/summary.json)
  [Two-scan T50 observation](../p10-dual-scan-evidence/e5b6260/README.md)
  [Matched E9 native CUDA LUT observation](../../../qualification/p10-performance/evidence/e9-cuda-lut-diagnostic/README.md)

The archived `07816a2` trace supplies a useful ceiling for lookahead.
Verify `raw-owned-upload.sha256`, then use
`owned-upload-phase/owned/candidate/external-stages.jsonl` from
the retained archive. Take the first callback for each
`(stage,start_monotonic_ns)`, sort by start, and split each frame
at `decode`. The 201 intervals give 50 frame groups and 49
adjacent pairs. Sum the smaller of the next decode time and the
preceding frame's interval from decode return through fusion return.
This hides at most 17.374 s of the 42.284 s trace, leaving 24.910 s
even with instantaneous handoff and no resource contention. Limiting
overlap to synchronized fusion hides 13.703 s and leaves 28.582 s.
The separate 47.811 s diagnostic reference would require 23.905 s
at its illustrative half-time. The historical frozen warm median
of 40.598 s corresponds to a different half-time of 20.299 s.
On the measured 15-CPU mask, the old untraced 297.09 CPU-seconds
also impose a 19.806 s arithmetic floor if the same work must run.
These bounds use the old trace, since the combined stage proportions
are unknown. Decode calls then took 346.9–433.4 ms apiece, and one
additional decoded raster alone occupies 207,101,952 B. Lookahead
also changes the ordered file-read and truthful pause/cancel
boundaries. [Exact stage archive](../p10-r50-phase-287828a/owned-upload/raw-owned-upload.tar.gz)
[Lifecycle and read-order review](../p10-decode-overlap-audit/README.md)

## One bounded residual hypothesis

The current normal-orientation three-color RAW path rewrites every
working sample through the locked Rawler quantizer and normalizes
each integer code by `f32::from(u16::MAX)`. It then calls generic
`RgbImage::new`, which traverses the entire buffer for finiteness.
This is a third, distinct scan. The selected crop holds
51,775,488 f32 samples, so one avoided traversal represents
207,101,952 B per original or 10,355,097,600 B across R50.
These are addressable bytes read. Cache and memory behavior and
completed-job savings remain unmeasured.
[Actual RAW return](../../src/image_io/raw.rs)
[Generic RGB validation](../../src/image_io/mod.rs)

If pursued after current assurance, keep the prototype within the
checked Rawler return. Require the original dimension/length guard
and a complete overwrite by exactly one pinned u16 code per source
sample. Verify the converter's per-chunk output length before writing.
A u16 value divided by the same nonzero finite denominator is
a finite f32 in [0,1]. Mark that result U16 with the existing
metadata. Preserve the general constructor for arbitrary f32 buffers,
custom input formats and other decoder branches. Keep the existing
camera development, orientation handling, quantizer, worker pool,
publication and cancellation boundaries.

First create a native red outside the normal timing run. Link a
minimal driver against the exact locked library, call public
`image_io::decode` on the pinned small CR3 pair and Bayer DNG,
and observe the real generic constructor with the external
debugger. Name the exact ELF and verify the callable address before
counting. The old verified normal RAW path should enter generic
validation once per decode and fail a zero-traversal assertion.
A live control must still observe the generic constructor and prove
incorrect length and nonfinite ordinary floats are rejected. Zero
events from an optimized-away address cannot establish the red or
the green. Compare the new path against the old f32 bit stream,
working shape and encoding for the two original CR3s, Bayer DNG
and its mirrored variant, all u16 code values at rounding boundaries,
and existing malformed/oversized cases. Compare actual complete
RGB16 exports, ordered maps, explicit backend and kernel launch
order on each matched device, using a separate launch-observer
run. Retain the existing P2 and registration/fusion oracles.
[Prior RAW bitwise and malformed-input witnesses](../p10-r50-raw-audit/host-aware-workers/README.md)
[Prior exact scan-removal witnesses](../p10-dual-scan-evidence/e5b6260/README.md)

For a later whole-input diagnostic, use a locked exact `e81079d`
baseline and scoped candidate, the same original 50, first-frame
similarity, 6/8/6 settings, auto crop and RGB16. Run a quiet serial
CPU pair with the same 0–14 job mask and 32 GiB cap. Measure from
spawn through completed exit, and validate pixels and 50+50 f32
transform bits afterwards. Separately use the existing external
phase path with the collector on CPU 15 to time actual RAW decode,
count the normal RAW validation path if addressable, and account for
thumbnail, estimate, frame fusion, finishing and TIFF staging.
Capture whole-job `wait4` CPU-seconds and per-stage inferior CPU
ticks, keeping the ordinary process timing separate from tracing.
Explicit same-card Vulkan or CUDA proof can then attribute the
unchanged host decode and real device dispatch. It supplies no
missing R50 GPU gate without a matched OpenCL reference and full
schedule. [Prior exact phase harness](../p10-r50-phase-287828a/README.md)

This report is derived from existing receipts and current source.
No new inputs, builds, device launches or timings were needed for it.
