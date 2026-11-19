# Limited T50 Weighted CPU timing and quality replay

All ten scheduled jobs in the corrected `abe1606b` package/reference replay
completed. The notice-bearing `11cfcf8` Debian CLI and pinned ChimpStackr
ran serially in the preregistered alternating order. They used the same
50 ordered generated RGB16 inputs, the unchanged frozen Weighted CPU
settings and 15 distinct worker cores. Each measured cold app started
with its own empty application/compiler cache. The three warm jobs used
per-arm caches primed by that arm's single warmup. The runner completed
all 52 encoded input and provenance rehashes and released the common lock
at **11:54:54.681 SGT** on 2026-11-19. The original failed setup remains
separate. [Preregistered scope](../t50-weighted-11c-limited-prereg/README.md) ·
[Original invalid launcher](../t50-weighted-11c-limited-invalid-launch/README.md)

| Limited metric | Reference | Packaged candidate | C/R | Cap | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Warm completed-job median (3 per arm) | 55.310500861 s | 25.890339449 s | 0.468090852 | 0.555555556 | Pass |
| Cold completed-job time (1 per arm) | 65.125906014 s | 25.667489230 s | 0.394121031 | 1.0 | Pass |
| Strict process-tree RSS max (all 10 eligible required) | Pending | 1,833,574,400 B | Pending | 0.55 | Pending |

The 3 ms nominal process-tree sampler used CPU15 for both roles. Nine
of the ten jobs met the actual 20 ms rule. An independent reduction
from raw acquisition timestamps included both edges of every launched
process interval and found one ineligible job. The reference in the
first measured warm pair had an interior **22.399369 ms** gap at elapsed
8.317709948–8.340109317 s. Both edges observed the same sole recorded
application PID, so the observation establishes no exact app subphase
or causal memory attribution. The second acquisition spent 16.446045 ms
of sampler thread CPU and started 3.752859 ms after its slot. The
affected job's observed sampled lower bound was 3,348,447,232 B.
Its ineligible peak remains in the raw evidence. The other reference
valid maxima include 3,472,818,176 B. That figure gives no strict
comparison with a missing arm observation under this preregistration.
[Typed result, all outputs and exact gap edges](summary.json)

Both roles completed on explicit CPU without fallback. All ten exports
decoded as genuine 5998×3998 RGB16 and reproduced their own previously
reviewed encoded and decoded hashes. Each reference event reported 50
first-reference identity maps, ordered sources, actual CPU stages and
the exact one-pixel crop. Each candidate event reported 50 ordered keyed
identity maps and 50 ordered sequential identity matrices. An exemplar
per arm rechecked all 50 generated sharp-truth regions and full decoded
pixel difference. [Quality and producer evidence](summary.json)

The 68-member packet preserves the ten raw sampler traces, typed
samples, complete events, launcher and census receipts byte for byte.
It contains no input or derived TIFFs and no ambient environment dump.
Derived exports remain in private custody for independent review
and later authenticated cleanup. This result supplies no frozen-full
P10 credit. [Raw packet](raw-limited-ten-jobs.tar.gz) · [Member hashes](archive-members.json)
