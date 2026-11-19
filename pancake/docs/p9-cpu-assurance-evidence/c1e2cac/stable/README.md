# Integrated stable CPU coverage

On exact clean `c1e2cac93ad41c02b328d87bdd5d01e1ce2b46eb`, the unchanged
`bash scripts/check.sh coverage-cpu` ran 146 tests in all 19 CPU groups.
All tests passed, with zero failures, ignored tests or filters.
The original comparator reported `CPU assurance: uncovered CPU lines`
and the command exited 1.
[Raw log](coverage-cpu.log.gz) [Actual status](coverage-cpu.status)
[Accounting](summary.json)

| Stable map metric | Covered / total | Uncovered |
|---|---:|---:|
| Lines | 4,658 / 6,475 | 1,817 |
| Functions | 476 / 756 | 280 |
| Regions | 4,776 / 7,288 | 2,512 |

Stable instrumentation emitted no branch mappings. The earlier pinned
nightly branch result retains its separate source revision and verdict.
[Stable source map](coverage-cpu.json.gz) [Stable indexed profile](coverage-cpu.profdata.gz)
[Earlier nightly evidence](../../7551f73-nightly/README.md)

The run used pinned Rust 1.100.0, LLVM 23.1.5 and cargo-llvm-cov 0.9.1
with the locked all-feature workspace, default debug profile, CPUs 0
and 1 and two Cargo jobs. GNU time recorded 3m31.68s, including the
fresh build in an isolated target.
[Exact command](command.txt) [Host environment](environment.txt)
[Time and status](time.txt)

## Separate synthetic profile transport

After the official gate exited, a tiny instrumented Rust ELF ran through
the unchanged conformance `ProcessRunner` in two synthetic calls.
The launcher recorded the held ELF and the existing call's PID before
replacing itself with fd-based `execve`. Both calls preserved their PID,
arguments with spaces, glob characters and Unicode, and expected exit
statuses 0 and 17. Each generated a 440-byte continuous LLVM profile
whose internal build ID matched the producer and whose total counts
were positive. The strict indexed merge succeeded. This receipt
establishes transport for the synthetic ELF.
[Sources and command](transport/command.txt) [Per-call proof](transport/result.json)
[Raw synthetic profiles and command receipts](transport/synthetic-raw-and-call-receipts.tar.gz)
