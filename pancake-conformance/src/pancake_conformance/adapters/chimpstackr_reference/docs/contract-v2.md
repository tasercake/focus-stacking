# ChimpStackr behavior correction — contract v2

Source and case map:

| Family | Application owners | Portable suite owners |
| --- | --- | --- |
| Weighted zero regions | `src/algorithms/API.py::_weighted_avg_core`, `stacking_algorithms/ocl.py::WeightedAverageGPU` | `cases/algorithms.py`, `cases/devices.py`, zero-region fixture |
| Exposure precision | `stacking_algorithms/cpu.py::mertens_fuse_batch`, `ocl.py::ExposureGPU`, `API.py::_gpu_core` | Precision/analytic batch cases, devices, baseline tolerances, RAW checks |
| EXIF | `src/ImageLoadingHandler.py` transform table and gray decode; `MainWindow/Preview.py` consumes native loader | All eight orientation fixtures and CLI truth checks; application tests cover native/float/ordinary/gray/preview loaders |
| Translation | `algorithms/dft_imreg.py::estimate_translation_matrix`; `algorithms/__init__.py` validation | Original translation request, matrix oracle and bounded symmetric crop |
| Repeated breathing | `algorithms/__init__.py` pair validation and chain fallback | Original small checker, all four methods, non-repeating controls, geometry and focus oracles |
| Corrupt input | Strict Algorithm loaders, typed `ImageDecodeError`, GPU propagation, transactional API result clearing, CLI diagnostics | Partial/malformed cases, all method/mode/backend combinations, retention and completion assertions |

The complete old/new case inventory is [case-contract-v1-v2.csv](../../../../../docs/case-contract-v1-v2.csv).
The [v2 numerical contract](../../../../../docs/algorithm-contract.md) records intentional output changes.

Additional defects exposed by stronger checks: grayscale decode could apply
EXIF twice; GPU mixed input conversion could narrow a later 16-bit source to
the first 8-bit source's dtype; nonsequential modes ignored middle reference;
missing explicit CLI paths were warned about and skipped; cancellation or late
slab failure could expose stale/intermediate API output. These are corrected.

Mertens now uses explicit float pyramids on CPU and GPU. Contrast below 1e-6
in normalized units is treated as arithmetic residue; actual image samples and
pyramid coefficients remain float32. This suppresses false contrast generated
by reconstruction of constant regions, without eight-bit quantization.
Four-frame batch grouping and equal final batch weights remain intact.
Eight-bit exposure outputs can differ by final rounding; genuine sixteen-bit
precision, standards-correct orientation and corrected registration intentionally
change previously frozen defect outputs. Weighted outputs change only where
focus evidence is absent. Registration validation also changes unsupported
motion on other fixtures; direct geometry oracles guard identified motion.

No portable real driver-failure fixture is available. Corrupt input never stands
in for a GPU fault. Unit oracle tests contain adversarial diagnostics solely to
prove rejection logic; they do not certify a real fallback. The physical GPU
checks require observed GPU completion. Guest GPU cases remain unsupported.

Historical source-coverage exclusions are tied to old source lines and must
not be blindly repinned after this correction. V2 uses a raw denominator with
no exclusions; the old profile remains archived for historical evidence.


Additional validation binds the original repeated checker and nearby
non-repeating controls to actual Apple M4 Pro GPU completion for all four
methods. All eight runs passed their unchanged geometry and focus oracles with
zero measured transform drift. These are supplementary backend variants of the
canonical CPU cases, not manufactured CPU/GPU differences.

Mixed-dimension, mixed-depth exposure fusion now checks genuine sixteen-bit
export and GPU/CPU parity. The measured mean error was 0.0594 and peak error
16 sixteen-bit code values, with identical identity transforms; its limits are
mean 1 and peak 32. Independent single-batch and multibatch gradient identity
checks remain limited to one sixteen-bit code value. Dimension matching keeps
the later source dtype even when the first source is eight-bit.

The merged native harness needed repairs discovered by full guest replay:
specific file-panel IDs precede broad dialog aliases; error sheets and windows
have explicit alternatives; native About menu/window labels are mapped from
observed UI; source-index regex escaping is corrected; menu clicks wait for
visible items; disabled history placeholders are read without clicking them;
empty-frame count requires actual empty-state text; pan tests first exceed fit
zoom. Lifecycle setup selects the same breathing mode before bulk folder import
and checks the published 64-image total, since the native virtualized list may
publish only one AX row. Pause/resume/cancel still exercise actual processing,
without delays, barriers, backend injection or completion substitution.
