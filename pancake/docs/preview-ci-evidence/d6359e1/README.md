# Hosted CI for the M4 preview

The initial push-triggered attempts both ran on
`d6359e129737f1a9077fb4abc2a8f783fa1f7b38`. The
[Pancake workflow](https://github.com/tasercake/focus-stacking/actions/runs/44277150143)
concluded **failure**. The
[reference conformance workflow](https://github.com/tasercake/focus-stacking/actions/runs/44277150146)
concluded **success**. These results apply to the published preview and
leave the final release acceptance open. [Attempt, job, step and log receipts](receipt.json).

## Pancake

| Job | Outcome | First decisive result |
| --- | --- | --- |
| [Windows MSVC build and link](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708072873) | **Passed** | Native Windows Server 2025 with Visual Studio 2026 finished the locked all-target, all-feature `x86_64-pc-windows-msvc` build/link in 10m40s. Cargo listed 25 linked test executables, including CLI and GUI. Windows tests were unrun under `--no-run`. |
| [Sanitizer (address)](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708072864) | **Passed** | 127 tests passed across 19 target groups, zero ignored. |
| [Platform (macos-15)](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708073091) | **Failed** | ARM64 `check.sh fast` stopped at `clippy::doc_markdown` for `MenuBar` in `crates/pancake-gui/src/session.rs:1205`. CPU platform tests were skipped. |
| [macOS Miri, randomized layouts, and branch coverage](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708072584) | **Failed** | Canonical ARM64 Miri passed 18/18. The first randomized layout then failed `observer_handles_non_unicode_paths_without_fabricating_geometry` in `cpu_job` with `Illegal byte sequence (os error 92)`. The second layout seed and branch step were unrun. |
| [Coverage, dependencies, mutation, and guardrails](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708073017) | **Failed** | All 127 tests passed. The coverage report failed the zero-uncovered-lines gate, and the remaining steps were skipped. |
| [Sanitizer (thread)](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708073132) | **Failed** | All 127 tests passed. TSan reported two warnings in system Fontconfig through Slint/fontique's parallel test initialization, involving `FcNameUnparse` and `FcConfigAppFontAddFile` / `FcDirCacheCreateUUID`. The job exited 66. |
| [Platform (ubuntu-24.04)](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134708072907) | **Cancelled** | `fast` and 127/127 debug CPU tests passed. GitHub's check-run annotation records the 20-minute job limit. Cancellation occurred during the release compilation in `test-cpu`. |
| [Pancake required](https://github.com/tasercake/focus-stacking/actions/runs/44277150143/job/134718958824) | **Failed** | The aggregate reported `failure,success,failure,failure,failure`. |

## Reference conformance

| Job | Outcome | Scope |
| --- | --- | --- |
| [Ubuntu 24.04](https://github.com/tasercake/focus-stacking/actions/runs/44277150146/job/134708072595) | **Passed** | Suite and adapter regressions 326 passed, 2 skipped. Native ChimpStackr reference GUI smoke 5 passed. |
| [macOS latest](https://github.com/tasercake/focus-stacking/actions/runs/44277150146/job/134708072742) | **Passed** | Suite and adapter regressions 324 passed, 4 skipped. Linux native smoke is Linux-scoped. |

The receipt captures each workflow's metadata with
`gh api repos/tasercake/focus-stacking/actions/runs/$run_id`, the job and step
metadata with `gh api "repos/tasercake/focus-stacking/actions/runs/$run_id/attempts/1/jobs?per_page=100"`,
and each raw log with `gh api repos/tasercake/focus-stacking/actions/jobs/$job_id/logs`.
Raw and compressed digests in the receipt bind every job log. The reference
workflow exercises the harness and ChimpStackr adapter. The Pancake package's
frozen 376-case ledger and later local runs have separate provenance.
