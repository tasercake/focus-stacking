# E9 overlap diagnostic runner

The runner executes at most four launches, in Vulkan serial, Vulkan overlap,
CUDA serial, CUDA overlap order. Each arm uses the exact `12f2151` release
binary and settings recorded by the prior physical E9 diagnostics. It uses
fresh task-owned caches and matching archived CPU affinity. The receipt has
no qualification credit or frozen performance verdict. Absence of a long
compute call in either arm makes the comparison inconclusive.

For a diagnostic bypass, the second worker must start its compute call
during the first worker's long compute call and finish its whole pair before
the first compute call returns and before job exit. Workers use independent
buffers and preserve both raw lists, their actual call windows, PID/session
and start ticks observed for each record, and the paired result. The merger
matches the primary per-PID aggregate, using the larger value for a PID seen
in both API lists. PID reuse, unknown attribution, unavailable bytes and
query failures are retained as unusable records. Observed completion gaps,
the separate conservative window bound, long or post-exit rows, and actual
bypass witnesses are all retained. NVML still provides no atomic shared
snapshot time for the two lists.

The runner shares the repository performance lock. A diagnostic operator
must also have the device lease before executing it. The monotonic interval
covers spawning the real CLI through observed wait completion. A watchdog
ends a synthetic or real job that exceeds its 12-second budget. The observer
prearms each lane and starts at most two pairs at once, using the same 8 ms
absolute slots and skipping missed or busy slots. It drains the active lanes
after exit, then closes NVML before releasing the lock. If a native call
will not drain, the runner records which slots were active and exits without
closing NVML or unwinding the lock. The kernel reclaims it when the process
actually terminates. Verify termination before transferring the device
lease. The normal path deletes owned caches and output TIFFs after retaining
the independently checked output shape, decoded RGB16 pixels and hashes.

## Preflight and bounded run

The preflight reads local files only. Omitting `--run-diagnostic` never opens
NVML, queries a device, starts a measured job, or acquires the performance
lock. The earlier bundle contains the acquisition reproducer that verifies
the Waterloo archive and extracts only the nine selected originals. Keep
the creator's copyright notice with the staged copies. [Archived E9 source and reference provenance](../integrated-e9-12f2151/README.md) ·
[University of Waterloo source and reuse terms](https://ivc.uwaterloo.ca/database/MEF/MEF-Database.html)

```sh
runner=qualification/p10-performance/nvml_overlap_diagnostic.py
export PYTHONPATH=pancake-conformance/src
"$qualification_python" "$runner" --input-root "$e9_root" \
  --vulkan-cli "$sealed_12f_vulkan_cli" --cuda-cli "$sealed_12f_cuda_cli"
```

During the reserved device window, add `--run-diagnostic "$fresh_receipt"`
to that same command. Keep the whole terminal receipt even when either arm
is inconclusive or invalid. Remove staged images after the final read.

The initial preflight verified both immutable binaries, both historical
paired archive digests, frozen target hash and all nine source-file hashes.
Thirteen new device-free tests cover deduplication, identity errors, distinct
result buffers, absolute slots, a blocked lane, exit and gap bounds, a real
synthetic child reaped by the watchdog, and process-exit lease cleanup. All
47 qualification tests passed.
The physical stage has not run.
