# Reachable macOS coverage scope audit

> Historical adapter record. Commands and paths describe the prior layout.
> See [current setup](../README.md) for this adapter.

This audit concerns ChimpStackr commit `046266223945cc1cbf8eacd295c00ee08d42d095`.
The execution roots are `python -m src.cli` and `src.run.main()` through the
native GUI launcher. It audits every Python file under `src/`. The existing
project's source unit tests and external Python consumers are not execution
roots for this application conformance scope.

Raw coverage must remain available. A separate scoped report may remove only
reviewed ranges, with category, source pin and evidence. A missing line is never
evidence of unreachability. The manifest does not claim that all remaining paths are covered. Ranges are inclusive and relative to target `src/`.

## Unused routines

`rg` and AST reference inspection found the following isolated application call
graphs. Imports, qualified attribute reads, string-based `getattr` dispatch,
Qt signal connections and Qt virtual methods were checked separately.

| Cluster | Call graph evidence |
| --- | --- |
| DFT similarity/log-polar implementation | `Algorithm._estimate_translation` calls only `DFT_Imreg.estimate_translation_matrix` at `algorithms/__init__.py:368,373`. That method calls `translation` and `resize_image`. `compute_similarity` has exactly one caller: `im_reg.register_image_RST:1011`. No application code references `register_image_RST` or `register_image_translation`. The proposal removes their exclusive transitive callees, retaining the shared translation helpers. |
| CPU batch weighted/depth implementations | `weighted_average_fuse_pair`, `weighted_average_fuse_multi` and `depthmap_fuse_multi` have no application callers. `compute_depthmap_index` is called only by `depthmap_fuse_multi:626`. The used streaming implementations live in `algorithms/API.py`; depth selection calls `compute_multires_sharpness:965`, and weighted fusion calls `compute_focus_weights:891`. Both used helpers remain in scope. |
| Configuration, loader and old API helpers | `AppConfig`, `ImageLoadingHandler.is_supported`, `settings.get`, `LaplacianPyramid.configure`, `Algorithm.align_image_pair` and `Algorithm.is_paused` have no application call sites. Some are called by upstream Python unit tests; that does not make them reachable from CLI or GUI. |
| Placeholder logging module | `algorithms/ProgressLoggingHandler.py` is never imported by application code. Its `Logger` is an unimplemented placeholder. |
| Old GUI aliases | Five `Window` methods are explicitly labelled `old name` or `old entry point`. Actions and signals connect to their replacements: `add_paths`, `new_stack`, `export_result`, `export_view`, and `toggle_inspector`. No application caller uses these aliases. |
| Icon compatibility wrappers | `icons.icon_open` through `icon_stack` have no application callers. Current UI uses `icons.icon(name, role)`. The `QIconEngine` implementation remains in scope. |
| OptionGroup setter | `OptionGroup.set_current` has no application caller; initialization sets each card directly. Card state and Qt event methods remain in scope. |

The current DFT translation subtree **must stay**: `get_apofield`, `_argmax2D`,
`_argmax_ext`, `_get_subarr`, `_interpolate`, `_get_success`, `_phase_correlation`,
`argmax_translation`, `translation`, `resize_image`, and
`im_reg.estimate_translation_matrix`. Their shared globals and imports also stay.

## Native code is reachable, but Python tracing cannot observe its bodies

Five `@numba.njit` functions run as compiled machine code. They are not dead.
`run.main` executes the warm-up; Laplacian fusion calls thresholded or hard
selection through `Algorithm.fuse_pyramid_levels`. The manifest lists function body ranges separately. Keep decorators and definitions in the Python report. Never
switch JIT off or treat compile-time notifications as execution coverage. Report
this exclusion as a measurement limit; output conformance still tests the real
compiled execution.

## Pinned exclusion manifest

The reviewed ranges now live in [the target manifest](../chimpstackr-coverage.json).
It contains exact source intervals, reasons, evidence, source hash and target pin.
The native compiled bodies are listed separately as measurement limits and stay
in the scoped denominator. The manifest is the authoritative machine-readable
input; this document supplies call-graph and environment evidence.

## Platform and packaging branches

These are conditional exclusions for the **source-launched Darwin arm64**
profile. They are not deletable dead code. Preserve platform predicates when
executed on macOS; remove only impossible bodies and corresponding branch exits.
A Windows/Linux or packaged profile must restore their ranges.

| File | Inclusive ranges | Evidence and boundary |
| --- | --- | --- |
| `run.py` | 48–53, 58, 79–81 | Windows taskbar/ICO and Linux Qt platform initialization. `sys.platform == "darwin"` cannot select these bodies. |
| `run.py` | 109 | Frozen app icon early return; `sys.frozen` is false for this source launcher. Keep the normal source icon path and its IO errors. |
| `run.py` | 114–131 | The Darwin arm returns at 113. Remaining multi-size platform icon construction is unreachable on macOS. |
| `algorithms/__init__.py` | 32–46 | Windows `MEMORYSTATUSEX` implementation. Keep the macOS memory lookup and exception handler. |
| `algorithms/__init__.py` | 48–51 | Linux `/proc/meminfo` implementation; stock macOS has no procfs. This filesystem assumption must be explicit in profile provenance. |
| `compute.py` | 71, 144–147 | Windows CPU-usage fallback, Windows and XDG cache paths. Keep Darwin cache path and cache override. |
| `lightroom.py` | 30–31, 53–55, 60–61, 74–88 | Windows registry/process paths and unsupported-platform fallbacks. Parameters permit explicit platform injection in Python tests, but GUI never supplies another platform. |
| `lightroom.py` | 37–40 | Frozen application discovery; source launch returns `None` at 36. This is packaging-only, not unused functionality. |
| `updater.py` | 146, 150–159 | Linux AppImage and frozen executable discovery. Source launch returns at 149. |
| `updater.py` | 198–233, 242–245, 248–303 | Staging, replacement helper generation and detached installation launch. Source GUI uses the release-page action because `can_install()` is false; no installed app is replaced. Restore for an isolated packaged update profile. |
| `MainWindow/MainLayout/ImageWidgets.py` | 32–34 | Explorer and generic file-manager bodies. Keep Finder, and retain the exception fallback at 35–36 because Finder launch can fail. |

`lightroom.PluginInstaller` install/repair/remove flows and update download UI
are packaging-gated in the current source app. They are **deferred packaged
integration coverage**, not unused routines. Source-level status/error reporting
remains reachable. The application hides Lightroom management and disables its
install button when source launch has no packaged `.app` connection
(`LightroomSetup.py:64–67`). Updater `UpdateDialog._main_action:215–222` opens the
release page for source launch. Do not delete these components. Do not add them
to unconditional unused-code exclusions. Any larger source-profile exclusion
must state these UI guards and keep reachable unavailable/error paths.

## Active caller invariants

These additional exclusions apply only to the pinned CLI/GUI application call
graph. They do not imply that the helpers' standalone Python API accepts no
other arguments. Every excluded body is rejected if a later run executes it.

| File and ranges | Proof |
| --- | --- |
| `algorithms/__init__.py:366–371` | `coarse_fine` defaults to `False`. The two `API.py` pair-estimation calls and sequential `_estimate_pair_step` omit it; translation fallbacks omit it. The only forwarding compatibility method, `align_image_pair`, has no application caller. Therefore the preliminary quarter-size translation branch is unreachable, even with large input images. |
| `algorithms/__init__.py:892–895`, `algorithms/API.py:575–577` | On stock Darwin, `SC_AVPHYS_PAGES` is absent from `os.sysconf_names`; calling it raises `ValueError: unrecognized configuration name`. With Windows and procfs branches already excluded, `_available_memory_bytes` always returns `None`. These memory-known worker caps cannot run. Keep the probe, exception handler and CPU-count worker selection. A future memory-probe fix must restore these ranges. |
| `algorithms/API.py:66` | All three constructors—CLI, GUI and compute calibration—pass `config=AlgorithmConfig(...)` or an existing configuration object. No application caller uses the optional constructor default. |
| `algorithms/dft_imreg.py:419,653,661–674,954` | Active DFT translation is called only from `_estimate_translation`, which supplies cached `ref_gray`. The disabled coarse/fine branch and unused registration wrappers are the only callers that omit it. `estimate_translation_matrix` calls `translation` without options: `filter_pcorr=0`, `constraints=None`; `translation` always supplies `argmax_translation` as callback. Consequently default-callback, minimum-filter, non-default constraint bodies and reference-gray fallback are unreachable. Confidence and 180-degree fallback remain reachable and measured. |
| `algorithms/stacking_algorithms/cpu.py:140,142` | The sole active `compute_focusmap_fast` caller consumes Laplacian levels from loaded float32 frames. Gaussian/Laplacian operations and grayscale conversion preserve float32. Keep the 2D grayscale branch: NPY input can reach it. |
| `algorithms/stacking_algorithms/cpu.py:152` | The sole active `feather_focusmap` caller is inside `if use_soft`, where `use_soft = feather_radius > 0`, and passes that same radius. |
| `algorithms/stacking_algorithms/cpu.py:225` | All four active `local_tone_map` calls in `API.py` pass literal `strength=0.3`; no application parameter changes it. |
| `ImageLoadingHandler.py:300` | The only callers are CLI input/output quality reports. Input sharpness is guarded by `img is not None`; output sharpness follows successful output validation. |

The Windows `MEMORYSTATUSEX` class definition at line 34 is also inside the
impossible Windows body; retain the full 32–46 range in that conditional rule.

## Missing behavior that stays in scope

Retain recoverable IO errors, corrupt cache handling, invalid image/parameter
paths, decoder fallbacks, CPU/GPU fallback, calibration, OpenCL build/allocation
failures, failed alignment, cancellation, pause/resume, GUI worker errors, and
service/network errors. Their absence from one run does not prove impossibility.
Hardware failure paths may need an isolated fault environment; until then they
remain measured gaps.

Retain Qt callbacks (`paintEvent`, `enterEvent`, `leaveEvent`, `wheelEvent`,
drag/drop, `closeEvent`, `drawForeground`, `QIconEngine.clone` and `pixmap`). Qt
calls these without Python source references. Retain `Window.is_stacking`:
`SettingsWidget.py:709` reads it with `getattr(window, "is_stacking", False)`.
Retain `Algorithm._identity_chain`: it handles fewer than two input paths.
Retain the Lightroom dynamic `getattr(self.installer, action)` dispatch.

## Denominator rules

Resolve each proposed symbol through AST on the pinned source and fail if its
range changes. Preserve raw executable statement and branch-exit sets. The
scoped statement set is the raw set minus reviewed inclusive ranges. A branch
exit is excluded only when its origin is excluded or its destination is in a
reviewed impossible body; a retained decision's possible exit stays measured.
Function exit arcs use coverage.py's negative line convention and must be mapped
to the owning AST function before applying a body exclusion. Do not classify a
negative destination as an ordinary source line.

Raw and scoped reports must show category counts, removed lines/arcs, retained
missing sets, interpreter, platform, architecture and target source hash. Never
union percentages; combine raw execution data before applying one audited scope.
A scoped 100% claim requires empty retained missing sets for both statements and
branch exits. Native runtime opacity must still be stated beside that claim.

## Whole-source review inventory

All 31 Python files were inspected through AST/reference analysis and targeted
source review. The unused-symbol proposal touches
`ImageLoadingHandler.py`, `settings.py`, `config.py`, four algorithm modules,
`cpu.py`, and three GUI modules. Platform/packaging findings additionally touch
`run.py`, `compute.py`, `lightroom.py`, `updater.py`, and `ImageWidgets.py`.
No static deletion/exclusion is justified solely by missing coverage in
`__init__.py`, `_version.py`, `cli.py`, `utilities.py`,
`algorithms/stacking_algorithms/__init__.py`, `ocl.py`, `MainWindow/MainLayout/__init__.py`,
`MainWindow/MainLayout/ImageViewers/__init__.py`, `MainWindow/ImageSavingDialog.py`,
`MainWindow/LightroomSetup.py`, `MainWindow/Preview.py`, `MainWindow/Threading.py`,
`MainWindow/TimeRemainingHandler.py`, `MainWindow/UpdateDialog.py`, or
`MainWindow/theme.py`. These include native callback and packaging paths already
qualified above; they are not empty files or automatically ignorable code.


On the archived full-run raw report (`conformance-vm-record-final`), a preliminary calculation removing unused symbols and native bodies removed 475 executable statements: 53
previously covered definitions and 422 missing statements. It removes 136 branch
exits, all previously missing. That old report would become **81.60% scoped line
coverage and 62.77% scoped branch coverage**, before any conditional platform or
packaging exclusions. These are preliminary denominator calculations, not new executions. The actual
manifest keeps native JIT bodies measured and adds reviewed conditional regions;
use the final run scoped.json for authoritative totals.
