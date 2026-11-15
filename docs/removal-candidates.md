# Uncovered-code removal review

Target: ChimpStackr `046266223945cc1cbf8eacd295c00ee08d42d095`. No application
code changed. Recommendations predict conformance impact; deletion was not
experimentally tested.

Evidence: final frozen-baseline replay
`artifacts/conformance-vm-release-replay/report.json` — **294 passed, zero failed,
one explicit guest-GPU unsupported case; all 295 cases completed**. Raw coverage:
`artifacts/conformance-vm-release-replay/coverage/coverage.json`. Fresh checks
confirm all 22 unused DFT routine bodies (256 missing executable lines) and four
old CPU batch helpers (58 missing lines) remain unexecuted. Target submodule is
clean at the pinned commit. Exact symbols, ranges and call-graph evidence:
[coverage scope audit](coverage-scope-audit.md).

| Code | Take | Evidence / conformance risk |
| --- | --- | --- |
| Unused DFT RST/log-polar and resampling subtree: `compute_similarity`, `transform_img`, `frame_img`, old `im_reg.register_image_*` wrappers | **Delete candidate; high internal confidence.** Check external Python API users first. | No application callers. Actual alignment uses `estimate_translation_matrix` or newer estimator. Retain translation callback closure, `get_apofield`, peak/interpolation helpers and shared FFT dependencies. Do not delete whole module. |
| Old CPU batch weighted/depth helpers: `weighted_average_fuse_pair/multi`, `compute_depthmap_index`, `depthmap_fuse_multi` | **Delete duplicate recipes, or retain compatibility wrappers.** | Active API uses streaming weighted accumulation and multiresolution depth selection. Current CLI/GUI should stay unchanged. Upstream unit tests call old helpers directly; removing supported Python APIs could break users beyond conformance scope. |
| Legacy UI/icon aliases; unused `Logger`, `AppConfig`, accessors/setters and old alignment/configure entry points | **Prune unused scaffolding; deprecate public aliases before deletion.** | No application call sites; Logger module is never imported. Current actions use replacements. Some helpers still have upstream Python tests. Exact 49-symbol inventory is in linked audit; search scripts/plugins before deleting aliases. |
| Foreign-platform branches; frozen-app update and packaged Lightroom setup | **Retain, or extract behind platform/package service boundary.** | Unreachable in this macOS source launch, but implement distribution features. Current suite could remain green while shipped apps lose installation/update support. Add packaged/platform integration contracts before removal. |
| Device/IO recovery, background GPU calibration, Numba bodies and Qt virtual/event callbacks | **Retain; not proven dead.** Refactor repeated recovery only with failure contracts. | Real errors and guest capability limits explain missing paths. JIT can escape Python tracing; Qt dispatch is dynamic. Deletion can break fallback, processing or rendering while current happy-path cases pass. |

Paths/symbols are relative to `submodules/ChimpStackr/src/`. Excluding code from a
coverage target does not prove it safe to delete. Next: review first DFT candidate
against external API users; any later removal needs a separate branch and frozen
full-suite replay.
