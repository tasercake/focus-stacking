# Separate limited T50 process-tree RSS pair

One fresh matched pair is preregistered in normal ChimpStackr → verified
Debian `11cfcf8` order. Both start separate empty application/compiler
caches, use normal OS caches, native frozen `T50.weighted_average.cpu`
options, the same exact 50 of the 52 sealed Stage6 TIFFs, and 15 worker
cores on CPUs 0–14. No timings, peaks, exports, or caches carry forward
from either preceding scope. The recorded ten-job wall/quality result
and its incomplete strict RSS result stay unchanged. [Exact prior ten
scopes](../t50-weighted-11c-limited-measured/README.md)

The canonical Linux sampler on CPU15 uses 2 ms nominal acquisition
through exit and retains the actual process/session roster and timing.
An independent reduction requires every actual gap, including spawn
and reap edges, to be at most 20 ms. The maximum of the fresh eligible
candidate readings divided by the fresh eligible reference peak must
be at most 0.55. An ineligible arm leaves this comparison pending.
The kernel per-process high-water mark remains descriptive. This pair
supplies no frozen-full credit. [Exact static roster](static-prereg.json)
· [Typed strict gate and synthetic checks](rss-pair-gate.py.txt)

Both real complete jobs must reproduce the previously reviewed
5998×3998 RGB16 encoded and decoded hashes, selected CPU/backend,
maps and crop. The paired generated-truth check repeats all 50 regions
for each output. The runner reauthenticates both producers and all 52
source records before and after the pair and holds the common lock
through postflight. Keep both derived outputs private until verified
cleanup. Each child has a 120 s watchdog. Previous exact cold job walls
totaled 90.79 s. Reserve roughly 2 minutes plus any isolated failure
postflight. Use a fresh two-second per-CPU/pidstat census before the
explicit grant and launch. No repeat is automatic.

From the clean operator checkout and existing Stage6 pinned Python:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY \
  PYTHONPATH="$operator_checkout/qualification/p10-performance:$operator_checkout/pancake-conformance/src" \
  PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
  taskset -c 0-14 "$qualification_python" "$evidence/rss-pair.py.txt" \
    --execute-rss-pair --lease "$fresh_quiet_receipt" \
    --producer-source "$exact_11c_checkout" --package-dir "$sealed_deb_dir" \
    --output "$fresh_private_output"
```

The lease must bind the profile, order, sample interval,
`materialization_sha256` and cache state from the static roster and
set `exclusive_host_granted`, `stage6_read_granted`, and
`other_workloads_terminal` to true. The default script only prints the
preflight. This preparation launched no applications or input reads.
