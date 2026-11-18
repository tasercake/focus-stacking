# Matched R50 CPU component comparison

The single CPU diagnostic per arm ran 20:19:26–20:22:04 SGT on
2026-11-18. Each locked headless release used Ryzen 9 7950X3D logical
CPUs 0–14, matching thread settings and a 32 GiB per-process address
space cap. The launches ran in fixed order with fresh private
application caches and common OS file cache after corpus verification.
One existing completion observer captured actual backend and all
matrices. The timer covers process spawn through completed export
and exit. [Lease](quiet-lease.txt) [Host at start](window-start.txt)
[End](window-end.txt) [Exact launch command](compare-r50.command)

Every arm used all 50 original Canon CR3 files, with 442,098,996
authenticated bytes from the pinned CC BY 4.0 source. The frozen
settings were Hybrid CPU, first-frame similarity, scale 6, kernel 6,
eight pyramid levels, auto crop, no slabs and RGB16. The corpus and
executable hashes were verified before and after the comparison.
[Original file hashes](acquisition.json.gz) [Corpus preflight](input-preflight.json)
[Stock and candidate build preflight](three-arm-preflight.json)
[RAW build](raw-build-receipt.json) [RAW source lineage](raw-source-lineage.json)

| Arm and source | Wall time | Relative to baseline | Kernel child peak RSS |
| --- | ---: | ---: | ---: |
| Owned-upload baseline `07816a2` | 39.928490 s | 1.0000× | 2,445,996,032 B |
| Hybrid band `903836c` | 37.024288 s | 0.9273× | 2,255,192,064 B |
| Luma lattice `f034185` | 40.361237 s | 1.0108× | 2,465,366,016 B |
| RAW packing `c8f68cf` | 38.098156 s | 0.9542× | 2,465,042,432 B |

The Hybrid and RAW changes reduced this completed-job observation by
7.27% and 4.58% respectively. The luma lattice was 1.08% slower in
this run. Its prior small-fixture thumbnail improvement did not
translate into a lower completed R50 time in this observation. The
Hybrid arm used 7.80% less kernel child peak RSS. Results describe one
serial matched series. Frozen warm, cold and process-tree RSS gates
remain separate. [Summary and per-arm launch/exit boundaries](summary.json)

Each CLI completed genuine CPU work with no fallback. All four
produced byte-identical 5086×3390 RGB16 TIFFs. Every independently
decoded pixel matched, reproducing the historical candidate digest
`9316387ed669f3e5cde04a009d2e7b12114ab3411e54448fee1447c07a689492`.
Each arm's 50 alignment and 50 sequential matrices also matched their
historical source-ordered IEEE f32 digest
`510dcebedcee928da7a9bf16f8e23b046a2b1d4b8582ed4643c6b3e12554711b`.
That comparison includes the published images and transform evidence.
[Exact process observations, events and report](raw-comparison.tar.gz)
[Archive checksum](raw-comparison.sha256)

For replay, place the supplied scripts in an owned scratch directory
with their trailing `.txt` suffix removed. Acquire the frozen originals
with the [existing verified acquisition procedure](../p10-r50-integrated-quality/README.md).
Use the frozen conformance Python environment, the authenticated release
ELFs and a coordinated CPU lease. The [runner](run-comparison.sh.txt)
takes the scratch path and exact RAW build receipt with
`--raw-provenance`. The [four-arm harness](compare-r50-local.py.txt)
extends the [original three-arm recipe](p4-provided-compare-r50.py.txt)
with the RAW artifact identity and per-arm failure preservation. The
same [process observer](diagnose.py.txt) launches every arm.
[Binary and source verifier](verify-three-arms.py.txt)

The 50 originals, four TIFFs, runtime caches and private conformance
environment were removed after their receipts and hashes were retained.
The immutable candidate ELFs remain in the local artifact store.
[Cleanup](cleanup.json)
