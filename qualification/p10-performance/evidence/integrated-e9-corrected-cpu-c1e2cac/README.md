# E9 CPU with the corrected reference

The exact Debian Pancake CLI from `c1e2cac93ad41c02b328d87bdd5d01e1ce2b46eb` and the locked ChimpStackr `ab7a92708269c01c6094729f6cdfaf1415677364` reference ran all 34 primary jobs in the frozen CPU schedule. Each target completed two warmups, ten fresh-process warm jobs and five fresh-cache cold jobs. Two separate backend witnesses confirmed explicit CPU execution and reproduced all ten warm decoded output hashes per target. The nine original Balloons PNG hashes and ordering matched before and after. The reference adapter applied `4+4+1` with equal final weights and kept the pinned per-batch kernels. [Prior CPU and physical OpenCL validation](../e9-reference-prototype/README.md)

| Frozen metric | Pancake | ChimpStackr | Ratio | Limit | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Warm median completed job | 0.377574641 s | 0.886587335 s | 0.425874 | 0.50 | Pass |
| Cold median completed job | 0.372393204 s | 6.516783979 s | 0.057144 | 1.00 | Pass |
| Peak process-tree RSS | 110,604,288 B | 346,869,760 B | 0.318864 | 0.50 | Pass |

The exclusive CPU campaign ran on November 18, 2026 at 21:35:20.972926–21:36:29.838861 Singapore time. Both jobs used logical CPUs `0–31`, 32 threads and the same Ryzen 9 7950X3D Linux host and `powersave` frequency policy. Process-tree RSS used an 8 ms nominal observation interval. The largest measured acquisition gap across all 17 primary jobs per target was 11.209162 ms for Pancake and 11.751608 ms for ChimpStackr, below the frozen 20 ms maximum. The raw report records heat observations, resource traces, fresh-cache checks, full job endpoints and distinct diagnostic completions. [Summary](summary.json) · [All 36 job rows](samples.csv) · [Raw archive](raw-paired-runs.tar.gz) · [Archive digest](raw-paired-runs.sha256)

Every export had the same `337×510` geometry and genuine RGB16 depth. The corresponding first-warm images reproduced the earlier functional receipt hashes. Full-image MAE was 510.171 unsigned 16-bit levels. Fixed upper-left, center and lower-right window MAEs were 302.447, 260.205 and 649.201 levels, with zero floor or ceiling fractions in both images within these windows. The runner retains its original `pending` quality gate while the separate representative-region assessment is recorded. [First-warm review inputs and metrics](fixed-roi-review.json) · [Exact Linux package and conformance evidence](../../../../pancake/docs/p9-linux-package-evidence/c1e2cac/summary.json)

## Reproduction

Use a clean benchmark checkout at `e9b20f47ffb69fe7366e8dfe7c4907086d1fc014` with the frozen reference environment, the exact originals and the verified P9 package. The bridge binds the original function code to an isolated candidate provenance check. It validates the P9 package, read-only extracted CLI, the build log, matching complete product tree, descriptor and `Cargo.lock`. The benchmark checkout and reference launcher retain separate commit and file hashes. The original parser, paired job schedule, subprocess calls, cache rules, clocks, validators and reducers execute unchanged. Two no-device tests covered wrong source, descriptor, routing and private function namespace rejection. The real no-job preflight verified both immutable identities and all 34 scheduled entries.

Place the exact `./usr/bin/pancake-cli` member from the verified `.deb` in the owned benchmark checkout at `pancake/target/release/pancake-cli` with mode `0555`. Configure the pinned Python environment at the reference descriptor's `.venv`. Run the archived bridge from an ignored path in that worktree. `QUAL_PY` points to the installed qualification Python, `RELEASE_LOG` is the existing P9 release build log, `PACKAGE` is the exact Debian archive alongside `package-verification.json`, and `PRIVATE` is the case-owned artifact directory.

```sh
export PYTHONPATH="$ROOT/pancake-conformance/src:$ROOT/qualification/p10-performance"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
bind="$PRIVATE/bind_c1_candidate.py"
input="$PRIVATE/../real/input"
receipt="$PRIVATE/candidate-attachment.json"
taskset -c 15 "$QUAL_PY" "$bind" --self-test
taskset -c 15 "$QUAL_PY" "$bind" --preflight --package "$PACKAGE" --release-log "$RELEASE_LOG" \
  --input-root "$input" --receipt "$receipt"
taskset -c 0-31 "$QUAL_PY" "$bind" --run --package "$PACKAGE" --release-log "$RELEASE_LOG" \
  --input-root "$input" --receipt "$receipt" --output "$PRIVATE/paired"
```

The archive retains the explicitly selected launch and observation files. It includes the build attachment and preflight, raw per-job traces and statuses, original timestamps and data and tool hashes. Its 189 members were verified byte-for-byte against staged originals. The recorded process environment is limited to the runner's explicit allowlist and case-specific configuration. The original photos and TIFFs are excluded from the archive. [Binding implementation](bind_c1_candidate.py.txt) · [Waterloo MEF dataset and rights](https://ivc.uwaterloo.ca/database/MEF/MEF-Database.html)
