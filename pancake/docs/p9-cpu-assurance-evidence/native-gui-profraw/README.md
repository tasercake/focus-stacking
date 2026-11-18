# Native Rust GUI profiles from frozen conformance

A real debug CLI and GUI with Rust LLVM instrumentation were built from clean
`bc192616ecebad47fef0ced154ca4361c2f0b994` on Ubuntu 24.04.5. The case,
target descriptor, and Linux desktop runner were used unchanged. The product
sources, manifests, lock, and adapter at the graph-review commit
`5216ba4227e14033483a21bb5eca1c6c168ef840` are byte-identical to the measured
commit.

`interface.recovery.close-unsaved` passed in 5.90 seconds inside runner-owned
Xvfb, Openbox, D-Bus, and AT-SPI. The GUI completed the generated three-frame
focus stack on the host CPU. The case canceled the close prompt, canceled
export from that prompt, and explicitly discarded the result. Its native
process returned zero without forced shutdown. The isolated profile directory
contains one 76,808-byte counter file matching that process's PID 308644. LLVM
23.1.5 merged the file and exported its mapping against the exact instrumented
GUI executable. This single execution covered 639 of 1,652 instrumented Rust
lines in the GUI crate, including 393 of 774 lines in the workspace session.
The profile is supplemental diagnostic evidence. The case result here comes
from a coverage build and the delivery ledger requires its own release replay.

The instrumented GUI SHA-256 is
`591c49b4a1100ec4666632eb3ac0f9b45041fba85c41ae5b338679304f2295e4`.
Its ELF build ID is `5fc4d79498671b752d5a8e7775403154b1758969`.
The capture records the command, executable hashes, generated input hashes,
host, clean shutdown, stack event and unmodified conformance report. The
`raw/` counters and compressed source-mapped JSON are retained alongside it.

## Reproduce

Use the pinned Rust, cargo-llvm-cov, desktop prerequisites, and uv environment
from the recorded host. From the measured revision's repository root:

```bash
(
  cd pancake
  export CARGO_TARGET_DIR="$PWD/target/llvm-cov-target"
  export CARGO_BUILD_JOBS=4
  unset RUSTC_WRAPPER
  source <(cargo llvm-cov show-env --sh)
  cargo build --locked --workspace --all-features --bins
)
python3 /path/to/capture-native.py "$(git rev-parse HEAD)"
```

Run the capture with the existing isolated-desktop tool environment and a
workspace-local uv environment. The capture script uses a fresh output
directory, temporarily points the unchanged descriptor's launch paths at the
instrumented binaries, and restores the prior files on exit. It removes
inherited desktop session variables and retains only counters matching a
clean, passing application process.

## Same-revision CPU comparison

The usual `bash scripts/check.sh coverage-cpu` selected 19 test suites. All
97 tests passed with zero failed or ignored tests. The 100% coverage gate
returned 1 with uncovered CPU lines. Re-exporting its profiles with
`cargo llvm-cov report --workspace --include-build-script --json` reproduced
the original totals. Adding the measured GUI executable to the exact object
list preserved every reported denominator and count in the control
containing only standard CPU test profiles. This also accounts for the
test-only Rust lines in the workspace denominator.

| Profile data with the same instrumented objects | Lines | Functions | Regions | GUI Rust lines |
| --- | ---: | ---: | ---: | ---: |
| Standard CPU tests | 3,913 / 5,773 | 385 / 670 | 3,988 / 6,549 | 330 / 1,742 |
| Standard CPU tests and the one isolated GUI process | 4,479 / 5,773 | 455 / 670 | 4,603 / 6,549 | 826 / 1,742 |

The measured profile adds 566 covered lines, 70 functions, and 615 regions
in the existing scope. 496 of those lines belong to the GUI crate. The
unchanged `compare_assurance_coverage.py` also returned 1 on the combined
result. This comparison uses the stable line, function, and region
instrumentation. The nightly branch gate has a separate configuration.

The `comparison/` files retain the standard command output, unchanged
threshold results, indexed profiles, source-mapped JSON, and exact LLVM
merge and export arguments. The instrumented executable and object files
can be rebuilt at the recorded source and toolchain pin.
