# Full frozen CPU interface coverage replay

Clean `5443cdf066df120de96ac3258d7beabe843cb1fd` joins the coverage runner with
the application and lock at `044bc58fea365a3b5792755dc885e54d18ee1b1a`.
The standalone standard CPU run executed 106 tests across 19 suites with
zero failures or ignored tests. The existing coverage comparator exited 1.

The runner built both real binaries with the same pinned stable toolchain
and executed the 33 exact CPU interface cases in `cases.txt`. The physical
GPU case and explicit GPU request case belong to their own execution lanes.
All 33 selected cases passed with zero failures, skips or unsupported cases.
All 36 GUI processes exited cleanly and produced 2,590,560 bytes of
individually authenticated raw profiles. Their production events record 22
completed jobs on the CPU. The 14 CLI comparison profiles are archived
separately by executable identity and are outside the merged GUI counters.

| Coverage scope | Standard CPU | Standard CPU with GUI |
| --- | ---: | ---: |
| Lines | 4,019 / 5,775 | 5,315 / 5,775 |
| Functions | 402 / 670 | 550 / 670 |
| Regions | 4,106 / 6,554 | 5,489 / 6,554 |
| GUI Rust lines | 330 / 1,742 | 1,580 / 1,742 |

Every baseline named mapping, source coordinate, covered region and
per-file denominator was retained. The combined strict comparator exited
1 for uncovered lines. The 460 missed lines include 162 in the GUI crate
and 298 elsewhere. This was a stable instrumentation pass. The nightly
branch and separate release assurance lanes require their own executions.

The standard CPU process group paused for the independent harness smoke
at the recorded UTC times. The corpus then ran to completion in one
unchanged conformance invocation. The long worktree path exceeded the
private AT-SPI socket path limit for GTK and made fallback dialog
operations slower. All affected cases still passed and report their actual
durations. Use a short, fresh absolute evidence directory for a new run.

The conformance report preserves the actual fixture/input digests and case
results. The capture and raw files bind every GUI launch to its process
and executable. The logs and indexed profiles retain the standard and
combined verdicts with the unmodified 100% threshold.
