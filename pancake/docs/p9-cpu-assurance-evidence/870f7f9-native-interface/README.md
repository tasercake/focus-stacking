# Stable CPU Nextest and private interface coverage at `870f7f9`

The clean revision `870f7f923d70b1a7b0e7fe73d5f9a4987770fdc4` ran the unchanged locked CPU
classifier through Nextest with Rust 1.100.0, cargo-nextest 0.9.152 and
cargo-llvm-cov 0.9.1. All 151 tests passed on CPUs 2 and 3. The stock LLVM
export used the standard workspace object list and source exclusion regex.
Both normal instrumented CLI and GUI ELFs were present in that list before
any private desktop cases started. This is a supplemental Nextest baseline.
The canonical `coverage-cpu` command retains its ordinary test runner and
unchanged strict comparator. [Baseline identity](baseline-audit.json).

The unchanged runner passed all 33 selected CPU interface cases using actual
native X11 input, normal Cargo binaries, Slint software presentation, and
case fixtures and exports. The physical GPU and GPU-request cases remain in
the release conformance evidence. The overlay authenticated
36 GUI profiles and 14 CLI profiles.
GUI attribution uses shutdown PID and internal ELF build ID. CLI attribution
uses exact command roster, actual CPU parity completions, profile counts and
internal build ID. Native GUI events record 22
completed CPU jobs. [Case report](native-report.json.gz).

| Metric | CPU Nextest | CPU Nextest and 33 GUI cases | Newly covered |
| --- | ---: | ---: | ---: |
| Lines | 4,731 / 6,516 | 5,925 / 6,516 | 1,194 |
| Functions | 485 / 760 | 618 / 760 | 133 |
| Regions | 4,850 / 7,328 | 6,134 / 7,328 | 1,284 |
| Branches | 0 / 0 | 0 / 0 | 0 |

Every paired export used identical ELF objects and filename filter. The stock
export independently discovered every authenticated raw app profile and
reproduced the explicit merge's mappings and coverage. All previous positive
regions and per-file denominators were preserved. The unchanged strict
comparator exited 1 for the overlay. Stable LLVM
reports zero branch mappings. This run is separate from the nightly branch
and packaged 376-case assurance. [Detailed verdict](coverage-overlay.json).

The first native preflight exited 2 before launching a Pancake app because
its short path omitted the existing Openbox wrapper's required `artifacts`
segment. The passing run added that segment and preserved the same inputs,
case set and build. The first baseline wrapper stopped after the passing
Nextest run because its post-test guard expected user flags inside
`show-env` output. The replay retained the Nextest profiles and used the
explicit already selected coverage target for the normal app build.
[Desktop preflight](first-preflight-desktop.log.gz).
[Post-test command](replay-post-nextest.sh.txt).

Raw app profiles, typed process records, indexed maps, and the digest and
size of each generated case output are retained. Generated media and private
runner state were cleaned after rehash. The source logs and index also remain
under `artifacts/p9-coverage-870f7f9`.
[Raw profiles](raw-app-profraw.tar.gz) · [Process receipts](native-process-records.tar.gz)
· [Case output hashes](case-output-manifest.json) · [Archived checksums](SHA256SUMS).
