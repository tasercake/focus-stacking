# Two-shard native CLI mutation pilot

At exact `f9af478`, pinned cargo-mutants 27.1.0 and Rust 1.100.0 executed
all six mutation candidates in `crates/pancake-cli/src/main.rs`. Both
round-robin shards had three candidates and each unmutated baseline passed
132 tests across 19 targets. The aggregate verified five mutants caught
and one compiler-unviable, with zero survivors and zero timeouts. The
unviable variant supplied `JobConfig::default()` where the type lacks a
`Default` implementation. Its raw compiler log records `E0277`.
[Summary](summary.json) · [Unchanged CPU target list](cpu-targets.txt) ·
[Source and tool provenance](provenance.txt) · [Raw producer artifacts](raw-pilot.tar.gz).

| Shard | Baseline build | Baseline tests | Caught | Compiler-unviable | Exit |
|---|---:|---:|---:|---:|---:|
| 0/2 | 207.773 s | 9.824 s | 2 | 1 | 0 |
| 1/2 | 4.826 s | 14.914 s | 3 | 0 | 0 |

Both shards used the same task-owned target, with two Cargo/jobserver jobs,
a registry-only dependency compiler cache, and no skipped baseline. The
native JSON files record the build and test argv for every case. The
emitted `mutants.out/mutants.json` of each run exactly matched its independent
shard list. The local verifier reconciled both native outcome files against
that partition and the separately generated six-row list. Each run restored
the clean production source.

## Baseline package selection

The first two launches stopped with exit 4 before testing a mutant. With a
single-file selection, cargo-mutants 27.1.0 builds the baseline only for
packages represented in the selected mutants. The baseline therefore selected
only `pancake-cli`, and the unchanged `--lib` test selector failed because
that package has no library. Adding `--test-package` flags still left the
baseline narrow. The raw archive retains both setup failures.
[Pinned cargo-mutants baseline implementation](https://docs.rs/crate/cargo-mutants/27.1.0/source/src/lab.rs).

The successful diagnostic passed `--cargo-arg=--workspace` to build and test
commands and set `--test-workspace false` so the tool emitted an explicit
mutated package rather than a second `--workspace` flag. Cargo 1.100.0 expands
`--workspace` alongside an explicit package. The successful baselines and
mutants therefore used the full workspace and all features, with the unchanged
`--lib --bins`, 16 CPU integration targets and `--include-ignored`. Build and
mutation test timeouts retained their 180 s and 60 s settings. The only mutation
selection was the six-row CLI file. [Exact commands and logs](raw-pilot.tar.gz).

A future full shard matrix also has to preserve workspace baseline selection
when candidates in a shard omit a member. This pilot establishes that the
artifact reconciliation and command routing work on two genuine shards.
The remaining full-workspace mutation gate is open.
[Full scope and timing audit](../d6ac366/README.md).
