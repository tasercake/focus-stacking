# Image I/O regressions

The image I/O production files at `bbb4767` match the retained coverage source
at `3dc9bcf`. The Rust 1.100.0 focused campaign exercised file-based profile
retention, malformed PNG/TIFF/DNG data, Bayer orientation, RGB and grayscale
precision, numeric frame limits, and the publication boundary after source or
staging changes. All fixtures were generated from the tests or checked into the
workspace.

The first regression exposed missing TIFF ICC bytes on import after exporting
a profiled RGB frame. PNG and JPEG passed. The direct TIFF directory reader
returned the exact 588-byte input profile from the emitted TIFF file. Calling
`image::ImageReader::into_decoder().icc_profile()` on that TIFF returned
`None` before any orientation call. The first application failure is retained
with the unchanged image implementation at `bbb4767`.
[Red test output](tiff-icc-red.log)

The application now recovers valid profile bytes from the original TIFF stream
through the pinned TIFF decoder's bounded directory API when the image decoder
has no profile. RGB8 and RGB16 export and import preserve the exact metadata,
samples and dimensions. The raster decode still owns native orientation and
color precision. The metadata fallback follows the existing handling of
missing or invalid optional profile tags.

## Native checks

The final focused run at `a5965a2` passed 35 tests across four targets.
Both TIFF RGB precisions preserve the embedded ICC bytes and source samples.
The invalid optional-tag control retains a valid TIFF raster without
reporting the malformed tag as a profile. Strict Clippy passed with the
workspace's generated, reviewed policy configuration.
[Focused native tests](focused-tests.log) · [Strict Clippy log](focused-clippy.log)

The unchanged `bash scripts/check.sh coverage-cpu` ran at the same revision.
It used four build jobs, Rust 1.100.0, Linux x86-64 and the AMD Ryzen 9
7950X3D host. The selected inventory ran 110 tests in 19 suites with zero
failures and zero ignored tests. The gate returned exit 1 for uncovered
source. The workspace report contains 3,951/5,792 covered lines, 392/674
functions and 4,022/6,568 regions.
[Strict CPU log](coverage-cpu.log.gz) · [LLVM report](coverage-cpu.json.gz)

| Image I/O file | Lines before → after | Functions before → after | Regions before → after |
|---|---:|---:|---:|
| `export.rs` | 247/281 → 261/281 | 21/31 → 22/31 | 237/304 → 248/304 |
| `mod.rs` | 135/156 → 156/175 | 21/35 → 26/39 | 145/175 → 165/194 |
| `npy.rs` | 133/135 → 133/135 | 23/25 → 23/25 | 168/173 → 168/173 |
| `raw.rs` | 57/101 → 60/101 | 10/28 → 11/28 | 63/118 → 66/118 |

The original export, NumPy and RAW source files and their LLVM denominators
match exactly. The TIFF metadata fallback adds source and changes the shared
image input file's denominator. The stable report records no branch counters.
[Source and denominator comparison](coverage-comparison.json)

## Independent P2 replay

The unchanged suite passed all 84 P2 case IDs with zero failures and zero
unsupported cases. The suite's existing CLI command override selected the
locked debug executable so the public regression could reuse the native build.
The tested application source is `a5965a2`, identical to the harness commit
`8e5dd19` across the application crates and Cargo lock. The raw completion
events report 43 CPU jobs and 16 physical NVIDIA RTX 3090 jobs via wgpu Vulkan
on driver 580.178.04. The release assurance receipt is separate.
[Command and binary receipt](p2-replay-receipt.json) · [Harness provenance](p2-provenance.json) · [Case report](p2-report.json.gz) · [Completion events](p2-completion-events.json.gz)

## Nightly branch check

The unchanged `bash scripts/check.sh branches-cpu` ran at `cfc2037` on the
pinned `nightly-2026-11-15`. Application code and tests match the stable
candidate. All 110 tests passed. The required gate returned exit 1 for
uncovered CPU lines and the nightly report counted 477/614 covered branches.
Export improved from 31/38 to 35/38 branches, NumPy from 20/22 to 22/22, and
RAW from 6/8 to 7/8 with identical source files and denominators. The changed
image input module went from 22/24 to 26/26.
[Branch comparison](branches-comparison.json) · [Nightly log](branches-cpu.log.gz) · [Nightly LLVM report](branches-cpu.json.gz)

## TIFF metadata allocation boundary

The first ICC fix used TIFF's typed byte-buffer reader. Source inspection
showed that this entry point charges reads against the TIFF decoding buffer,
which defaults to 256 MiB. A real TIFF with a 1 MiB plus one byte ICC field
confirmed that the first fix retained metadata beyond the native IFD budget.

The application now uses one direct reader for TIFF ICC and gives its
buffered-tag reads the pinned decoder's 1 MiB default IFD budget. With an actual
RGB16 fixture, an ICC payload at the budget is retained byte-for-byte. A TIFF
with a one-byte larger field still returns the original valid raster without
retaining that optional metadata. The raster and orientation path is unchanged.
The focused image tests passed 36/36 and the generated Clippy and cross-host
source policy validations passed. The earlier report snapshots identify the
preceding source.
[Limit regression before the fix](tiff-icc-limit-red.log) · [Focused tests after the fix](tiff-icc-limit-tests.log)

The exact bounded revision `1276ed6` ran `bash scripts/check.sh branches-cpu`
with the same pinned nightly. All 111 selected executable tests passed. No
doctests ran. The strict gate remained exit 1 for uncovered CPU lines. It
counted 3,957/5,799 lines, 392/674 functions, 4,028/6,574 regions and 481/618
branches. Compared with the prior nightly baseline, the unchanged export,
NumPy and RAW files retain the same denominators and improvements above.
The shared image input module reaches 162/182 lines, 26/39 functions,
171/200 regions and 30/30 branches. These denominators include the bounded
TIFF metadata path.
[Bounded source and coverage comparison](bounded-branch-comparison.json) · [Nightly log](bounded-branches-cpu.log.gz) · [Nightly LLVM report](bounded-branches-cpu.json.gz)

The exact bounded revision also passed a fresh run of all 84 P2 case IDs,
using the same locked debug invocation and clean source. The replay recorded
43 CPU and 16 physical RTX 3090 Vulkan completions. No cases failed, were
unsupported or remained unrun.
[Bounded replay receipt](bounded-p2-replay-receipt.json) · [Provenance](bounded-p2-provenance.json) · [Case report](bounded-p2-report.json.gz) · [Completion events](bounded-p2-events.json.gz)
