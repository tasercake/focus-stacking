# Source coverage transport through frozen conformance

On Linux, the unchanged frozen runner launched the actual debug CLI built with
Rust 1.100.0 LLVM instrumentation at `3dc9bcf3c30605badea2f7b2ee2840075507b6c3`.
The experiment retained the published Pancake descriptor. A temporary symlink in
this worktree's build output mapped the expected CLI launch path to the real
instrumented executable. The original output path was restored after the run.

`cli.help` passed with `--no-coverage` on the conformance command. The target
inherited an absolute `LLVM_PROFILE_FILE` pattern and wrote a 50,360-byte
profile on normal exit. The LLVM tools bundled with Rust successfully merged
the profile and exported line coverage against the exact binary, including
15/99 lines in the actual CLI entry point.

[Execution and hashes](receipt.json) · [Conformance provenance](provenance.json)
· [Runner log](runner.log) · [Raw profile](cli.profraw.gz)
· [LLVM coverage report](llvm-coverage.json.gz)

The Linux runner's inherited environment reaches native GUI subprocesses
through the same case context. A GUI extension should stage the actual
instrumented GUI executable with the unchanged descriptor, acquire the native
isolation lease, and use a case that explicitly requires a clean exit.
`interface.recovery.close-unsaved` already requires a zero exit after a real
Discard action. Qualifying profile inputs must match that exit's PID and
executable hash. Forced termination remains in the native shutdown receipt
and supplies no atexit coverage. Supplemental GUI coverage and threshold
acceptance remain open.
