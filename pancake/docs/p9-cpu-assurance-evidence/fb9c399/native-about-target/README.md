# Native About through a normal CPU integration target

The clean product reference `fb9c399a96658331cb76b843a1e565b503e94fdd`
has the same Pancake code and lock as `c1e2cac`. Its unchanged stable
`coverage-cpu` run passed 146 tests and exited 1 on uncovered CPU lines.
The original mapped report and indexed profile are separate.
[Baseline output](standalone/coverage-cpu.log.gz) [Baseline map](standalone/standalone.json.gz)

Local test-only commit `1b5ab0c678833e56bc9784426ca82da5c6c93dbb`
adds the Linux `cpu_gui_native` integration target to the existing GUI
crate. The existing classifier selects it automatically. Cargo's
`CARGO_BIN_EXE_pancake-gui` embeds the exact instrumented application path
into that test. The pinned ordinary exporter included both ELF objects
after a build-only `--no-run` without changing any authored source
coordinates, per-file counters or metric denominator.
[Fixture source](cpu_gui_native.rs.txt) [Build-only control](no-run/no-run-control.json)

A single ordinary instrumented Cargo test invoked the frozen
`interface.about` case in the existing private desktop harness.
It displayed version 0.1.0 and the real app exited cleanly with
status 0 and no forced shutdown. The test passed in 2.74s.
The app inherited the standard cargo-llvm-cov profile pattern.
Its 80,080-byte raw profile matched the exact GUI build ID
and the PID recorded by the actual desktop runner.
[Observed About session](live/integration.log.gz) [Raw profile](live/about-app.profraw.gz)
[Process and ELF provenance](live/live-control.json)

The unchanged exporter automatically collected the new counter file.
Its named mappings, previously covered regions, files and denominators
matched the before-execution control. The added authored line hits
were 152 in session, 22 in main, 18 in pointer handling, nine in
preferences and four in the panel boundary. The strict comparator
still exited 1 on uncovered lines.

| Metric | Before About | With About | Gain |
|---|---:|---:|---:|
| Lines | 4,658 / 6,475 | 4,863 / 6,475 | 205 |
| Functions | 476 / 756 | 498 / 756 | 22 |
| Regions | 4,776 / 7,288 | 4,986 / 7,288 | 210 |

The proof adds one real CPU application witness through the normal test
and export mechanism. The original standalone gate result and the
separate optional native coverage cohort remain recorded independently.
The test-only branch is retained locally for review of runtime
provisioning before any integration into CI.
[Actual exporter commands](live/live-export.log.gz) [Live map](live/live-map.json.gz)
[Strict verdict](live/ordinary-comparator.status)
