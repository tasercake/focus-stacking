# P9 headless CPU coverage follow-up

Static review at `4c32f17e3b3fc6ca8f8acf6e9325632b632feb10`. R50 had exclusive
machine use during the review. This note records a proposed experiment and
historical evidence. The experiment has no new test or coverage result.

## Reuse the exact object

The `5443cdf066df120de96ac3258d7beabe843cb1fd` stable CPU re-export already
lists `-object target/llvm-cov-target/debug/pancake-cli` among the Cargo
objects and uses `target/llvm-cov-target/pancake.profdata`. That executable
is the proposed headless producer. The compressed re-export log has
SHA-256 `d52773fd7ca67417b9a24bfb865e53e3e77aa881ae9c10e8ceb380b6a42e1dc9`.
Take the path from the fresh exporter command and hash its actual bytes at
capture time. The archived capture's recorded CLI identity belongs to its
separately built continuous executable. Its 14 tolerated parity CLI profiles
were outside the authenticated GUI session list and outside the merge.
[Re-export command](native-gui-continuous/5443cdf/coverage-cpu-reexport.log.gz)
and [capture receipt](native-gui-continuous/5443cdf/capture.json).

The historical union recorded 5,315/5,775 lines, 550/670 functions, and
5,489/6,554 regions. It missed 298 non-GUI lines and 162 GUI lines. Large
non-GUI deficits included RAW (44), runtime selection (38), export (34),
focus (27) and decode (21). The CLI's four remaining line gaps are in its
progress/report/warning writer paths. Ordinary CLI success can add executed
regions or instantiations. Writer I/O failures, rare codec or resource errors,
CR3-specific logic, accelerator setup and GUI-only paths require separate
targeted evidence. [Historical totals](native-gui-continuous/5443cdf/summary.json)
and [source map](native-gui-continuous/5443cdf/combined.json.gz).

## Pilot selection

The frozen cases below are exact IDs. Each appears as passed in the archived
`12f2151` package host report. All stack calls with recorded request options
use `device=cpu`. The two direct-call cases were checked in source.
`cli.help` passes only `--help`; `cli.export.failed-retention` sets
`device=cpu` in its direct command. `CaseContext.stack` overlays options
onto the descriptor's CPU default and maps CPU to `--cpu`. The pilot has
seven CLI, ten algorithm and one explicit CPU device case. Its archived
release case durations sum to 4.53 seconds. Instrumented elapsed time is
unmeasured. [Frozen CLI cases](../../../pancake-conformance/src/pancake_conformance/cases/cli.py),
[descriptor](../../../pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml),
and [host report](../p9-linux-package-evidence/12f2151/host-report.json.gz).

```text
cli.help
cli.progress-and-quality
cli.export.jpeg-16bit-warning
cli.export.failed-retention
cli.coverage.reject.dng
cli.coverage.raw.legacy-alignment
cli.coverage.input.npy
algorithms.coverage.gray_array.depth_map.cpu
algorithms.input.float255
algorithms.input.exr
algorithms.precision16.tif.weighted_average
algorithms.export.exr
algorithms.parameters.kernel_11
algorithms.exposure_precision.9.tif
algorithms.coverage.partial_corrupt.hybrid.breathing
algorithms.coverage.precision.affine
algorithms.coverage.featureless.affine
devices.cpu.depth_map
```

GPU/parity cases and automatic device requests belong to their other lanes.
Even `cli.reject.output-parent` and `cli.export.overwrite` may select Auto,
because they bypass `CaseContext.stack` and omit a device flag. Preserve
those cases in the full conformance matrix. Select explicit IDs for this
extra instrumented run.

## Capture and gate

1. Extend the existing optional workflow with repeatable headless IDs.
   Reuse its fresh standard CPU collection, export-argument parser, clean
   checkout checks, conformance report checks and provenance helpers. Run
   the frozen descriptor via `uv run --frozen` and `--no-coverage`. The
   latter leaves Rust counters independent of Python coverage.
2. Use a fresh sibling process/profile directory and an ordinary process-exit
   pattern `pancake-%p-%b.profraw` for the exported CLI object. Archive each
   actual launch's PID, argv, executable hash, exit status and raw profile
   hash. The frozen command receipt has argv and cwd but no PID. A small
   coverage-only launcher can inherit streams and process group, record those
   fields around the real child, preserve status, and pass its arguments
   through after verifying the exact `--help` or `--cpu` invocation. Reuse
   the existing ELF build-ID and nonzero LLVM profile checks. Require a
   profile for every accepted call, complete exact passed IDs and CPU events
   for completed jobs. Expected failure cases may exit normally with a
   nonzero code and a genuine profile. Missing, mutated, stale or unrelated
   profiles fail collection. Record exact Cargo and uv locks, suite/descriptor
   hashes, compiler, executable, source, and distinct GUI/headless cohorts.
   [Existing CLI profile transport proof](native-profraw-transport/README.md).
3. Merge only authenticated raw profiles with the standard indexed profile.
   Use the same object list and filename filter. The optional GUI union
   keeps its existing GUI object and unchanged-count control. Headless uses
   the CLI object already in that list. Require identical mappings between
   the control and combined export and preserve all covered regions and
   branch outcomes. Leave the original strict comparator and required
   standalone gate in place. [Existing runner](../../scripts/gui_coverage.py)
   and [strict comparator](../../scripts/compare_assurance_coverage.py).
4. Keep branch coverage on its separate pinned nightly build and branch
   profile. Stable 0/0 branches reflects absent branch instrumentation. A
   future branch replay must use the real nightly `--branch` object, raw
   counter and export cohort, require a nonzero branch denominator, and
   enforce zero uncovered lines, functions, regions and branches. The
   archived nightly baseline covered 466/612 branch outcomes.
   [Nightly receipt](5216ba4-nightly/README.md).

The portable CI route for this proposal is Linux x86-64 with the existing
locked Rust/Cargo and `cargo-llvm-cov` 0.9.1, Rust's `llvm-tools-preview`,
GNU `readelf`, Bash, Python 3.12.12 and the existing conformance uv pin
0.13.8. Headless execution needs no GPU, display services, ChimpStackr
submodule, or reference runtime. The shared workspace build still uses
the existing native build dependencies. The optional GUI run keeps its
isolated display dependencies. Darwin retains the required separate
assurance job. Estimate one focused tooling iteration plus fail-closed
tests and one timed pilot with the already-built instrumented object.
