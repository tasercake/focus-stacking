# P0.01 conformance snapshot review

Reviewed: 2026-11-17. Source commits: historical
`22ef292bb135d69e30801b473736aaf85a646c84`, current
`00bd1371e1ee8873a90e462d8cef3ef0c5d05e92`.

**Disposition: adopt the current committed suite as the P0 acceptance source,
while preserving the historical snapshot and existing baselines.** The drift
is understood; no core conformance file was edited during this review. This
closes the snapshot-review subtask, not the whole P0.01 gate: performance targets,
hardware scope, and the other P0 conditions require their own evidence.

## Fingerprints and catalog

The original roadmap's 86 file hashes exactly match historical commit
`22ef292`. Current inventory under the same selection rule has 90 files:
70 byte-identical, 16 modified, four added, and none removed. The old check
correctly detected modifications but did not inventory new files.

| Snapshot | Files | Combined SHA-256 |
|---|---:|---|
| Historical, retained in `case-roadmap.json` | 86 | `c976c4d8915c07080f530b06c40a5223928034e142b37e33f223d8c420f7423f` |
| Reviewed current, `contract-current.json` | 90 | `2d17fb4f570dcfae47e355b63e18650c325c586f47620c565b568f4fdcce20b2` |

All **376 catalog records are unchanged**, including order, IDs, suite,
description, and required capabilities: 46 CLI, 223 algorithms, 72 devices,
and 35 interface cases. Canonical catalog metadata SHA-256:
`0c287412662c0c47fb50fb90d3058c6dac864ba777275f9e8a9d0195c3a58705`.
Unchanged IDs alone would not establish unchanged behavior: one existing case's
execution request changed as described below.

## Every modified historical file

Paths are relative to `pancake-conformance/`. Each disposition accepts the
current committed content without changing the test suite.

| File | Reviewed change | Acceptance effect/disposition |
|---|---|---|
| `README.md` | Documents Linux private desktop and `--gui-desktop` pytest opt-in alongside macOS VM. | Adopt broader execution route; previous macOS-only planning assumption is stale. |
| `docs/ui-protocol.md` | Linux AT-SPI observations and XTest clicks; same separately observed postconditions. | Presentation/transport extension. No business-operation shortcuts or inferred success added. |
| `pyproject.toml` | Paramiko/vncdotool become cross-platform dependencies; Apple Vision remains Darwin-only. | Adopt new locked runner requirements. No image validator version or tolerance edited here. |
| `src/pancake_conformance/cases/recovery.py` | `interface.recovery.device-request` sends observed completed backend to host CLI parity request. | Material case-execution change. GUI/CLI delivery now compares like-for-like backend; CPU/GPU equivalence remains independently checked by unchanged device cases. Mean/max parity limits stay 1/257. |
| `src/pancake_conformance/cli.py` | Groups interleaved suites for full VM runs; automatically owns a private Linux desktop for interface execution. | Adopt routing change. Linux physical-GPU GUI execution is no longer removed by macOS VM capability filtering. |
| `src/pancake_conformance/macos_ui.py` | Shared `open_session` dispatches Linux session; rejects Linux launch without isolated-desktop marker. | Adopt native driver boundary. No automatic launch on inherited Linux host desktop. |
| `src/pancake_conformance/target.py` | Recursively merges current platform's `[platforms.*]` overrides. | Adapter may express Linux/macOS controls and environment without core changes. Arrays/scalars replace; nested tables merge. |
| `src/pancake_conformance/vm_bootstrap.py` | Capture failure is checked before importing Apple Foundation/Vision. | Preserve macOS behavior while avoiding irrelevant Apple imports on failed capture. |
| `tests/conftest.py` | Adds Linux native-smoke opt-in and exposes target startup logs on failure. | Test infrastructure change; native smoke still requires explicit target and UI route. |
| `tests/test_cli_entrypoint.py` | Adds regression for grouping interleaved GUI cases in full VM execution. | Added orchestration self-test; catalog unchanged. |
| `tests/test_external_target.py` | Compiles portable C target with `cc` instead of `xcrun cc`. | Portable self-test command; no target result manufactured. |
| `tests/test_gui_vm.py` | Makes Darwin/ARM64 assumptions explicit in mocked VM tests. | Allows portable execution of VM unit tests; not evidence of a real guest run. |
| `tests/test_native_pointer_variants.py` | Removes two Apple SDK event/focus construction tests. | Native transport self-test coverage reduction; record gap below. Pointer request-construction test remains. |
| `tests/test_recovery_cases.py` | Adds two parameterized assertions that GUI/CLI comparison uses actual CPU/GPU backend and unchanged thresholds. | Tests the material recovery request change. |
| `tests/test_ui_protocol.py` | Removes five Apple native-helper/SDK tests and centralizes imports. | Native transport self-test coverage reduction; shared portable tests remain. |
| `uv.lock` | Cross-platform transport dependency markers and platform wheel records expand. | Adopt current immutable resolution. Package names/versions are unchanged; transport selection markers and available distribution artifacts differ. |

## Added files missed by the old inventory

| Added file | Reviewed role |
|---|---|
| `docs/linux.md` | Linux native dependencies, private display/session, platform override and invocation instructions. |
| `src/pancake_conformance/linux_ui.py` | Owns Xvfb, Openbox, private D-Bus/accessibility environment and native session; preserves observed popup selection and sandboxed file paths. |
| `src/pancake_conformance/native_linux.py` | AT-SPI tree/values and XTest keyboard/pointer transport. Normalizes role vocabulary, not target business state. Requires isolation marker. |
| `tests/test_linux_ui.py` | Five routing, platform-override, dependency failure, private D-Bus environment, and inherited-host-display rejection self-tests. Two are Linux-only. |

## Consequences for the execution plan

An isolated **GPU-capable Linux host** can run all 35 interface cases, including
`interface.compute.gpu`, on a private desktop. Therefore **a dedicated physical
Mac GUI session is not the only route to 376/376**. The macOS VM route still
cannot prove physical GPU execution and remains capped at 375 passed plus one
unsupported when the whole catalog is selected through that route. Actual Slint
AT-SPI exposure, dialogs and GPU execution must still be qualified; source
review is not a native GUI pass.

Linux `pancake-conformance run` creates the desktop automatically when interface
cases are selected. `--gui-desktop` is a pytest fixture option, not a required
runner flag. `[platforms.linux]` mappings belong in Pancake's adapter. Linux
documentation mentions OpenCL for the existing reference target; the portable
device assertions require truthful completed GPU execution and decoded-pixel
quality, not OpenCL as Pancake's backend API.

The owning reference adapter contains a historical Linux record of 376/376 on
an RTX 3090, including all 35 interface cases. It establishes prior reference
coverage only. This review did not replay that target or validate Pancake on
that hardware.

Seven upstream macOS self-tests were removed by `1600763`, rather than skipped:

| Removed test | Evidence no longer supplied by current core self-tests |
|---|---|
| `test_native_helper_reports_accessibility_trust` | Actual helper accessibility-trust response. |
| `test_native_helper_rejects_unknown_command` | Actual helper error response for unknown command. |
| `test_native_helper_returns_error_for_missing_application` | Actual helper missing-application rejection. |
| `test_native_snapshot_distinguishes_running_process_from_missing_app_registration` | Actual native-helper observation of a running unregistered process. |
| `test_scroll_event_targets_requested_viewport_before_native_post` | Apple SDK scroll-coordinate construction. |
| `test_native_pointer_constructor_preserves_click_count_and_button` | Apple SDK button/count construction. |
| `test_focus_guard_polls_fresh_os_attribute_instead_of_cached_workspace` | Native focus-query freshness. |

These are not any of the 376 behavioral catalog cases. Their removal leaves a
macOS transport-assurance gap; it is not evidence of a new Pancake conformance
failure. P0 native-UI qualification must rely on actual native execution, not
historical self-test counts. This task neither restores nor removes core tests.

## Validation and limits

Executed in this isolated Darwin ARM64 worktree:

```sh
uv run --project pancake-conformance --frozen pytest pancake-conformance/tests
```

Result: **307 passed, 4 skipped** in 14.13 seconds; 311 collected. Two skips are
live native-smoke wrappers without explicit target/UI lane. Two skips are Linux
desktop routing/boundary cases on Darwin. No GUI input was sent to the host.
These are suite self-tests, not Pancake target passes or full source coverage.

The reviewed current snapshot pins all 90 non-adapter files, including added
Linux sources. Existing historical hashes, reference baselines, case records,
and core files remain untouched. Native Linux, real macOS GUI, physical GPU,
and remote/platform replays remain unverified by this review.

Relevant upstream history: `45a2a25` adds isolated Linux support and observed
backend parity; `b4a6c8d` adds Linux startup/loader diagnostics; `1600763` removes
seven Apple-specific native-driver self-tests. `00bd137` adds the Pancake
scaffold/planning adapter without changing the reviewed core contract.
