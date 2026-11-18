# Exact CPU GUI coverage overlay

The unchanged helper captured About, frame context, and unsaved close from
the real instrumented desktop binary at
`c1e2cac93ad41c02b328d87bdd5d01e1ce2b46eb`. All three selected frozen
cases passed and all three apps exited cleanly. The unsaved-close case
recorded one completed CPU stack. The private desktop used software
presentation and the frozen CPU device default.
[Case report](passing/report.json) [Capture and ELF provenance](passing/capture.json)

Every accepted raw profile was 80,080 bytes and matched its recorded
process PID and internal ELF build ID. The existing helper validated
the baseline-only native-object control and the merged report. It
preserved all standard named mappings, already covered source regions,
source files and metric denominators.
[Control](control.json.gz) [Merge log](merge.log) [Raw profiles](passing/profiles.tar.gz)

| Stable metric | Standalone CPU | CPU with three native cases | Gain |
|---|---:|---:|---:|
| Lines | 4,658 / 6,475 | 5,340 / 6,475 | 682 |
| Functions | 476 / 756 | 559 / 756 | 83 |
| Regions | 4,776 / 7,288 | 5,523 / 7,288 | 747 |

Both the canonical standalone gate and the separate augmented comparator
exited 1 on uncovered lines. The unchanged stable toolchain emits no
branch mappings. The strict zero-uncovered threshold and CI gates
retain their original scope.
[Standalone log](preparation/coverage-cpu.log.gz) [Augmented status](combined-strict.status)
[Augmented map and counters](combined.json.gz) [Indexed profile](combined.profdata.gz)

The initial preparation archive check encountered different Rust symbol
disambiguators in builds from different worktrees and debug settings.
Mapped coordinates, multiplicity, positive coverage signatures and
per-file counts matched exactly. The same-build reexport and native
control retained the original strict named-map checks. The first draft
driver also omitted forwarding the native build environment, producing
binaries in the wrong target directory. Those binaries were ineligible.
The successful build forwarded the original counter-relocation flags and
used the dedicated target.
[Archive comparison](preparation/archived-map-check.json)
[Prepared executable identities](stage.json)

Two earlier private attempts remain separate. The first used an output
path that the retained Openbox wrapper rejected and exited 2 before
launching an app. The second started the desktop, but all three apps
exited 1 because the launch supplied the unsupported override
`PANCAKE_RUNTIME=cpu`. Its three startup profiles remain failure
diagnostics and were excluded from the merge. The successful third
attempt used a short case-owned path, left that override unset, and
kept the frozen device default.
[Both earlier attempts and failed profiles](earlier-failed-attempts.tar.gz)
[Successful launch command](passing/corrected-command.txt)
