# One matched E9 diagnostic on the registration-fixed Linux CLI

The explicit-CPU E9 exposure-fusion profile was measured against pinned
ChimpStackr on 2026-11-18. Candidate application revision was
`5e102447ad95c641eb773d9fdf94f2bc3757b81d`, with actual locked release
CLI SHA-256
`3ac6abaecc1bbd5743efd2abc6879a43d4b17294514b7bc209a05227d613ccbb`.
Reference revision was
`ab7a92708269c01c6094729f6cdfaf1415677364` with the frozen runtime.
All jobs used the Ryzen 9 7950X3D with the same 32 logical CPUs and the
same host power policy, with the desktop, assurance and packaging work
paused. All nine original Balloons PNG hashes were checked before and
after the campaign.

Exactly two complete warmups, ten measured warm runs, and five measured
cold runs completed for each application. Within each pair the target
order alternated. The primary runs used uninstrumented fresh processes,
separate scoped caches, and the full frozen profile. Independent
backend-provenance jobs ran after the primary samples. Both completed on
the explicit CPU path.

| Gate | Pancake | ChimpStackr | Candidate/reference | Numeric result |
|---|---:|---:|---:|---|
| Warm completed-job median | 1.08585 s | 0.89903 s | 1.20781 | Misses the 0.50 maximum |
| Cold completed-job median | 1.07501 s | 6.53525 s | 0.16449 | Within the 1.00 maximum |
| Peak process-tree RSS | Pending | Pending | Unavailable | Collection exceeded the 20 ms interval |

The warm profile failed. Its 0.44951 s target median is 2.42 times below
the observed Pancake median. The run remained a diagnostic for one profile
and one reviewed source revision. The other twelve recipes/method sets
and release candidate measurements remain open.

The 20 ms observation limit was exceeded in seventeen of seventeen
candidate jobs and three of seventeen reference jobs. The largest gaps
were 34.19 ms and 26.70 ms respectively. The preserved raw traces observed
at most one OS process per app session and sampled RSS lower bounds of
120,430,592 bytes for Pancake and 349,495,296 bytes for ChimpStackr.
Those lower bounds cannot establish a peak-memory ratio. Future records
also collect Linux reaping `ru_maxrss` and its CPU-time counters, while
retaining the concurrent tree sampler to account for overlapping child
processes. This run was not repeated to replace the missing RSS gate.

The isolated warm candidate cache held zero files after its warmups.
The reference warm cache held ten files and 725,627 bytes before its
first measured warm job. That is an observed persistence difference.
Additional phase attribution remains separate from the completed-job
samples.

Every closed export independently decoded as genuine 337 × 510 RGB16.
Each application's decoded hash was identical across its timed runs and
matched its own earlier [paired quality inspection](../registration-recheck/README.md).
Full image MAE between applications was 2823.78 of 65535, and the inspected
regions still need equal-quality review. All output TIFFs and per-run
caches were removed. The raw archive contains commands, exact build and
source provenance, timing samples, resource traces, diagnostics, and
cleanup records.

[Outcome summary and per-run memory observations](summary.json) ·
[Original paired-run receipts](raw-paired-run.tar.gz)
