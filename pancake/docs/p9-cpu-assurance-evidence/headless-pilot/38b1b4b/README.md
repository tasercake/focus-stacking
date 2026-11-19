# Headless CPU LLVM coverage pilot

Clean experimental revision `38b1b4bbb15fd9e6812da99351131be8342a36bb`.
The local branch `codex/pancake-p9-headless-llvm-pilot` retains the runner
and test-first guard tests. The evidence commit ships this receipt. The
experimental runner is outside the required assurance workflow.
[Plan and exact selection](../../headless-coverage-plan.md) and
[experimental diff inventory](tested-source-diff.txt).

The standard CPU lane ran 125 tests across 19 suites with zero failed or
ignored. The frozen headless replay passed all 18 cases, with zero failed or
unsupported. The CPU debug executable was the `-object` from the standard
LLVM export and its SHA-256 was
`8c8304559580781347f9c00e33a653ba47d56fa434abbb76d829ed64489b261e`.
No separate instrumented application build ran. The 20 real subprocesses
produced 950,880 bytes of raw counters. Seventeen exited 0, including
help and 16 explicit CPU stack completions, and three expected application
rejections exited 1. Each PID, ELF build ID, and raw profile's internal
binary ID matched. No GPU execution or desktop session was used.
[Original report](conformance-report.json.gz), [suite provenance](conformance-provenance.json),
[capture](capture.json) and [case invocations and events](process-receipts.tar.gz).

The merged export kept the original objects and filename filter. The
denominators and mappings matched and every previously covered region
remained covered. Both the standard and combined strict coverage gates
exited 1 for uncovered lines.

| Metric | Standard | With headless cases | Change |
| --- | ---: | ---: | ---: |
| Lines | 4,193 / 5,922 | 4,194 / 5,922 | +1 |
| Functions | 425 / 683 | 425 / 683 | 0 |
| Regions | 4,290 / 6,697 | 4,293 / 6,697 | +3 |

Newly covered source regions at the tested revision are
`src/job/mod.rs:286:6–286:7`, `src/job/mod.rs:298:10–298:11` and
`src/registration/estimate.rs:242:5–242:6`. The historical native GUI
counter cohort was separate. Stable 0/0 branches signifies absent branch
instrumentation. The pinned nightly branch gate requires its separate
collection and remains unresolved by this pilot.
[Summary](summary.json), [standard map](coverage-cpu.json.gz),
[combined map](combined.json.gz), [re-export command](coverage-cpu-reexport.log.gz)
and [strict gate output](workflow.log).

The run used Linux x86-64 on AMD Ryzen 9 7950X3D, Rust 1.100.0 with LLVM
23.1.5, cargo-llvm-cov 0.9.1 and uv 0.13.8. The standard instrumented build
took 3m 03s and the case durations sum to 10.14s. These durations describe
assurance. Replay from `pancake/` in the experimental checkout using its
clean revision and a fresh ignored output directory.
[Platform details](platform.txt) and [standard build and tests](coverage-cpu.log.gz).

```sh
export PATH=/tmp/pancake-tools/bin:/tmp/pancake-uv/bin:$PATH
CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
  RUSTC_WRAPPER=/tmp/pancake-tools/bin/pancake-rust-cache \
  bash scripts/check.sh coverage-cpu-headless \
  --output ../artifacts/pancake-assurance/headless-pilot/run-38b1b4b
```

The new process-attribution tests failed before the collector existed.
The final focused Python run passed 26 tests and ShellCheck and Bash syntax
checks passed. The receipt includes the standard and combined indexed
profiles and the original accepted raw profiles. Archive verification
matched every accepted profile, CPU event and launch receipt against its
capture record before cleanup. Generated case images, binaries and build
scratch stay outside Git. [Test-first run](unit-red.log),
[final checks](unit-green-exact.log), [raw profiles](raw-profiles.tar.gz),
[standard profile](standard.profdata.gz), [combined profile](combined.profdata.gz)
and [artifact checksums](SHA256SUMS).
