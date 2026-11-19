# Exact 11cfcf8 E9 CPU evidence

The complete 8 ms campaign used Pancake
`11cfcf8aac5921dfa843bfc5777eb4b2643a6ca6`, its notice-bearing Debian package
SHA-256 `74a764f99ba72be40f02e6b3b9faf3981f19e35f0b46e0231f665b1ccbe8c729`,
and actual extracted CLI SHA-256
`d54c4aaa135c9d2bef0fcbfcdefab82915038afa09af3f48fd067714f1188fdd`.
The exact package's 376 Linux cases passed across 341 host, 34 isolated GUI
and one physical GPU GUI case. The raw ledger SHA-256 is
`d1e803f05e2a961b36795265c1fb28c253a93e60ef465aa14c28e70b4c9e0a4a`.
The reference used pinned ChimpStackr `ab7a927` and the adopted corrected
equal-final-batch mean for the same frozen 4+4+1 exposure groups.
[Exact preflight](preflight.py.txt) · [Ledger binding](verify-ledger.py.txt)

## Completed fixed 8 ms run

The original frozen 34-job primary schedule and two separate CPU witnesses
all completed, with no repetitions. The process ran from 11:18:10 to
11:19:21 SGT on November 19, 2026, using CPUs 0–31 and 32 worker threads
on the Linux Ryzen 9 7950X3D host. Each witness matched the 10 measured
warm pixel hashes for its application. All nine original input hashes
and their ordering reverified unchanged. The independent replay used
the same reducer and preserved the raw original result.
[Typed summary](8ms-full/numeric-summary.json) · [All 36 observations](8ms-full/samples.csv)
· [Preregistration](8ms-full/preregistration.json) · [Raw evidence](8ms-full/raw-paired-runs.tar.gz)

| Frozen measure | Pancake | ChimpStackr | Ratio | Result |
| --- | ---: | ---: | ---: | --- |
| Warm completed-job median | 0.373322134 s | 0.903272565 s | 0.413299538 | Pass |
| Cold completed-job median | 0.372137981 s | 6.608340910 s | 0.056313375 | Pass |
| Peak process-tree RSS | Pending | 345,837,568 B | Pending | Pending |

All 17 primary reference RSS traces met 20 ms; the worst gap was
9.377806 ms. Sixteen of 17 primary candidate traces met the bound. Candidate
cold-05 had an interior gap of 28.073483 ms. Its second observation began
14.208167 ms after its scheduled time, and that acquisition took
1.180651 ms. The raw observed 108,158,976 B for that job remains recorded
as a sampled value. The required strict campaign memory result remains
pending, and this exact E9 CPU profile remains unqualified.

Independent decoding confirmed true RGB16 at 510×337 and exact equality
to the earlier independently reviewed corresponding corrected CPU files
and pixel hashes for both apps. Whole-image difference against the
reference was MAE 510.171 u16 and RMS 634.898 u16. The three original
fixed-window metrics and zero endpoint clipping inside those windows
reproduced exactly. The previously recorded localized extra endpoint
incidence still applies. [Current independent review](8ms-full/independent-first-warm-review.json)
· [Earlier qualitative review of these exact pixels](../integrated-e9-corrected-cpu-c1e2cac/independent-quality-review.md)

## Interrupted 3 ms attempt

The separate preregistration reused the same exact package, conformance
ledger, reference, real corpus, settings and CPU mask, using qualification
tool `cae209e4aabe488eb38030a6df65ebaabd58b074` and a 3 ms nominal
period under the same 20 ms validity rule. Unrelated npm, esbuild,
workerd and infrastructure test workloads appeared in the fresh census.
The launch script recorded that census and started the runner before
the finding was reviewed. The exact owned runner was interrupted at
11:24:59 SGT with exit 130. Its processes and common lock were then
verified terminal.

The partial run retained 23 completed primary samples, zero separate
witnesses, and the original interruption. It supplies zero profile or
metric credit. Its records are independent of the full 8 ms run. Any
future launch needs the completed fresh census and a distinct launch
decision before the first app starts.
[3 ms preregistration](3ms-contended-invalid/preregistration.json)
· [Invalid attempt receipt](3ms-contended-invalid/invalid-attempt.json)
· [Partial raw evidence](3ms-contended-invalid/raw-paired-runs.tar.gz)

The two raw packets contain 192 and 130 verified files. They include
allowlisted launch data and scoped console output, with no original
photo bytes, derived TIFFs, application binaries or ambient process
environment dumps. The two independently reviewed private TIFFs were
rehash-checked and removed, and both work scopes held zero derived
outputs and case caches after cleanup. The sole nine-file owner stage
remains available for separate authorized read-only work.
[Cleanup receipt](cleanup.json) · [Checksums](SHA256SUMS)
