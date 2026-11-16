# Execution diagnostics contract, version 1

> Historical adapter record. Commands and paths describe the prior layout.
> See [current setup](../README.md) for this adapter.

Device conformance needs proof of completed execution. A selected device label
or successful image export alone cannot prove GPU execution because a target
can fall back to CPU. Any implementation language may write these JSON records.
The future port must implement equivalent evidence; it need not use Python
profiling or retain ChimpStackr's internal names.

The runner sets `CONFORMANCE_EVENTS_PATH` to a per-process JSON Lines file.
The ChimpStackr adapter maps that portable setting to its opt-in
`CHIMPSTACKR_CONFORMANCE_EVENTS` startup hook. Records carry
`schema_version: 1`, `event`, `pid` and `time_ns`. Times and process IDs are
observations, not stable golden values.

Optional diagnostic metrics can be non-finite for degenerate inputs, such as
phase-correlation confidence on all-zero images. The reference observer encodes
these as explicit strings `"NaN"`, `"Infinity"` and `"-Infinity"`, including nested
arrays. It preserves the application's original values and image output. These
strings are not numerical success evidence; required completion and backend
fields retain their ordinary types.

| Event | Required evidence |
| --- | --- |
| `stack_start` | `algorithm`, `requested_backend`, `effective_parameters`, `input_order` |
| `stack_complete` | `completed`, `actual_backend`, `actual_backend_by_stage`, `output_shape` |
| `backend_fallback` | `stage`, `requested_backend`, `actual_backend` |
| `crop_complete` | `bounds` in top/bottom/left/right order, or null |
| `export_complete` | `path`, `shape`, `dtype` when emitted by CLI export observation |

`stack_complete.actual_backend` is `cpu`, `gpu`, or null for incomplete output.
Its `actual_backend_by_stage` contains `fusion`, `alignment_estimation` and
`warping`. `not_requested` marks alignment/warping when no alignment was
requested. `cpu+gpu` denotes mixed alignment estimation, not a claim that all
registration runs on GPU. Maximum-precision refinement can remain on CPU while
fusion and image warping complete on GPU.

Completed records also include algorithm, requested backend, effective
parameters, input order, optional device name, alignment matrices and optional
sequential matrices. Matrix coordinates use x/y image order. Output shape is
height/width/channel order. Crop can occur after stacking, so final exported
geometry is checked independently from the file.

The reference hook emits `observer_ready` on startup and `observer_error` if
its own observation fails. Device cases fail on observer errors, absent
completion evidence, incomplete stacks or wrong completed backend. Forced-CPU
cases also reject GPU fallback events. Ordinary algorithm cases validate image
files without relying on these Python-specific observations.

## Reference adapter mechanics

The startup observer profiles function boundaries through `sys.setprofile`
and `threading.setprofile`. Coverage uses tracing separately. Only boundaries
inside the declared target root are observed. A completed GPU fusion is
recorded only after the GPU path returns with an output, not when OpenCL is
selected or initialized. A failed GPU attempt followed by CPU completion is
reported as CPU completion. No target business operation is initiated by the observer. Native-created
worker entry hooks attach and restore tracing/profiling for the duration of
the original callback; Python-created threads inherit normal instrumentation.

## Numerical device parity

CPU/GPU comparisons use independently decoded RGB pixels. Geometry and shape
must agree before pixel comparisons. Error units are 8-bit code levels;
16-bit TIFF comparisons divide values by 257 without quantizing them.
Precision cases separately require real uint16 variation beyond expanded
8-bit values.

Typical limits are MAE 0.3 and at most 1% of pixels with any channel error above
2 levels. Aligned stacks allow MAE 0.5 (depth-map 0.6), with larger exceptional
pixel fractions because independently estimated subpixel transforms and frame
selection amplify floating-point differences. Slabs use separate limits.

Small odd-size Laplacian fixtures have an explicit reference-specific budget:
MAE <= 0.8, no more than 5% of pixels above 2 levels, maximum channel error <= 12.
Measured on Apple M4 Pro: focus MAE 0.5653/p99 4/max 10; overlapping slabs MAE
0.7357/p99 3/max 9. Source GPU tone mapping uses exact sRGB curves while CPU
OpenCV LAB conversion uses approximations; small CLAHE tiles amplify the known
difference. Other methods retain tighter limits. These are documented fixture
budgets, not a rule to increase limits whenever a future target fails.

Out-of-range GPU indices are normalized by the current reference. The macOS
single-GPU cases characterize zero, negative and above-range selection. This
behavior is part of the reference contract, not an assertion that a new device
was tested by each index.

## Automatic selection and real fallback

`measurement_complete` records one completed real calibration and its measured
CPU/GPU timings. `measurement_lookup` records `available`, `cache_hit` and
`calibration_performed`; `device_decision` records requested/selected backend,
reason and optional measured speedup. The observer reads normal function
returns. It never reads, creates or edits the application's private cache file.

The measured-auto case resizes two generated focus frames to 1100x1000, above
the reference's small-frame threshold. It requests normal calibration, then
starts a second process with the same case-isolated user/cache directory.
Assertions require one completed cold calibration, warm reuse without a second
calibration, valid output and identical output on reuse. Either measured winner
is valid. Profiling and coverage add overhead; these timings are execution
observations, not uninstrumented performance benchmarks.

The decode-fallback case supplies two valid images with one real corrupt PNG
between them. The GPU pipeline rejects the corrupt frame and returns to CPU;
weighted-average CPU processing skips it. The suite requires an actual fallback
event, completed CPU execution and pixels identical to a valid-only CPU run.
This characterizes existing behavior without simulating driver failures or
replacing application code.
