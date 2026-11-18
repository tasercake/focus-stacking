# Full R50 Hybrid CPU functional comparison

On 2026-11-18, Pancake `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` and the
corrected independent ChimpStackr reference processed all 50 original Canon
CR3 files. The exact locked release CLI was built by the separate P9 producer.
Its SHA-256 is
`32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055`.
Reference source is `ab7a92708269c01c6094729f6cdfaf1415677364` with the locked
RawPy 0.26.1/LibRaw 0.22.0 runtime and the integrated R50 launcher.
[Exact job provenance](jobs.json.gz) [Independent release build](independent-build.log.gz)

The selected 442,098,996 bytes matched all 50 ordered input lengths and hashes
before the first job and after the second. On every frame, ExifTool 12.76's
camera metadata agreed with RawPy on the 5088×3392 recommended crop at
(272,172), the 5376×3574 sensor and the native orientation. Every original passed
camera WB, calibration and saturation validation. All had black level 2048,
white level 14,888 and the same finite calibration matrix. One frame's red WB
coefficient was 1513 and the other 49 used 1515. The frozen capture and source
rights remain documented in the original manifest.
[Acquisition receipt](acquisition.json.gz) [Per-frame metadata](metadata.json.gz)

Both actual Hybrid CPU jobs used first-frame similarity alignment, no
slabs, kernel 6, eight pyramid levels, alignment scale 6, auto-crop and
16-bit export. Each completion reported 50 identity transforms on the same
verified inputs. Independent TIFF validation confirmed RGB16 and genuine
high-depth samples. After the one-pixel inset on every side, both exports
measured **5086×3390** and matched the same physical first-frame rectangle.
[Pancake completion](candidate-events.jsonl.gz) [Reference completion](reference-events.jsonl.gz)

## Observed output quality

Whole-image mean absolute difference was **506.42** out of 65,535
(about 1.97 u8 codes). RMS was 669.39 and the largest single-channel
difference was 52,299. Mean signed color differences were between −226.67
and −260.78 u16 codes across RGB. The exports have different pixel digests.

Texture inspection used identical coordinates in both outputs. The first
quadrant-based variance selection picked isolated hot points in smooth
background in three quadrants. A reference-only ranking by 90th-percentile
absolute luma derivative identified four distinct 256-pixel specimen tiles.
Both images resolve the specimen boundary, a thin filament crossing it, and
green surface texture at the same locations. Pancake is slightly darker in
the shared field. In those four tiles, Pancake's 90th-percentile absolute
luma Laplacian was 1.16–1.40 times the reference's. Local contrast, texture,
noise and isolated color points can all affect these measurements.
[Full-frame and crop metrics](comparison.json)

This one instrumented pair establishes full-workload completion, matching
geometry, genuine precision and observed differences for Hybrid CPU. The
difference metrics are descriptive. The frozen performance campaign and quality
review still require the specified sampling, methods, devices and artifacts.

## Reproduce

Run from a clean checkout of the tested integration revision. Initialize the
pinned reference checkout and runtime, and point the runner at an independently
verified release artifact. Create a fresh ignored scratch directory before
acquisition. Use the saved producer log for binary and lock provenance.

```sh
proof=pancake/docs/p10-r50-integrated-quality
ref=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
mkdir -p artifacts/r50-quality
git submodule update --init submodules/ChimpStackr
uv sync --frozen --project "$ref"
python3 "$proof/acquire.py.txt"
export PYTHONPATH="$PWD/qualification/p10-performance"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 "$ref/.venv/bin/python" "$proof/inspect_sources.py.txt"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 taskset -c 12-15 \
  "$ref/.venv/bin/python" "$proof/replay_quality.py.txt" \
  "$release_source/pancake" "$release_source/pancake/target/release/pancake-cli" \
  32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055 "$producer_log"
taskset -c 12-15 "$ref/.venv/bin/python" "$proof/compare_quality.py.txt"
```

The two jobs ran serially on Linux x86-64 (Ubuntu 24.04.5, Ryzen 9 7950X3D),
with CPU affinity 12–15, two OpenMP and Numba threads, a 32 GiB child
address-space cap and a 12 GiB host available-memory floor. Both completed
without a resource abort. The diagnostic record retains the exact commands,
observer events, sampled upper-process-memory counters and failures if
encountered. The photos, TIFF exports, inspection panels and scratch caches
were deleted after retaining hashes and receipts. [Cleanup](cleanup.json)
