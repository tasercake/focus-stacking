# Native GUI counters on Linux

The independently invoked `coverage-cpu-gui` check runs the standard CPU
coverage gate and records its actual status. It then executes the explicitly
requested frozen CPU interface cases with the real locked application and
conformance-owned Xvfb, Openbox and D-Bus. It requires a complete, fully
passing report and associates each desktop process's raw Rust counters with
its reported PID and exact ELF build ID. Both the ELF note and the raw
counter header must agree. CPU profiles require CPU stack events when the
application emits them. A forced cleanup remains forced in the receipt.

The native binaries use LLVM runtime counter relocation and the
`LLVM_PROFILE_FILE` formatter `%p-%b%c`. The pinned Linux toolchain probe
in this directory executed a known branch before an external SIGTERM.
The ordinary atexit profile was empty. The continuous profile retained
count one for the functions that ran and zero for the untaken branch.
The probe used Rust 1.100.0, LLVM 23.1.5, and
`rustc -C instrument-coverage -C llvm-args=-runtime-counter-relocation`.
[LLVM source-based coverage documentation](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html)

The aggregation preserves every standard LLVM source coordinate, named
function mapping, and per-file denominator. Running the standard CPU
profiles through the same object list with the GUI executable added is
the control. The control must keep the original covered counts. The
combined export must keep exactly that object's mapping and all previously
covered regions. The existing zero-uncovered-source comparator decides
the result.

From the `pancake` directory with the frozen project's prerequisites
and a private desktop available, run the explicit check with a fresh
evidence directory. Select a short absolute path so GTK can open its private sockets.

```bash
coverage_dir="$(mktemp -d /tmp/pcg.XXXXXXXX)"
bash scripts/check.sh coverage-cpu-gui \
  --output "$coverage_dir/run" \
  --case interface.about \
  --case interface.recovery.close-unsaved
```

The pilot ran these cases with the exact production source and Cargo.lock
at `bbb4767`, using the capture helper commit `113076d`. Both passed and
exited cleanly. The standard CPU coverage run had 98 passing tests.
The two-case native profile brought LLVM to 4,482 / 5,773 lines, 455 / 670
functions and 4,608 / 6,549 regions. The selected case and profile records
preserve each exact native executable digest, PID, build ID and fixture
identity. The standard and combined results remain below the required
coverage threshold.
