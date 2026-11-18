# R50 Hybrid CPU on the exact Linux release

The Debian package for `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` provided
CLI SHA-256 `32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055`.
ChimpStackr used source `ab7a92708269c01c6094729f6cdfaf1415677364`,
frozen RawPy 0.26.1/LibRaw 0.22.0, and the committed R50 launcher that
develops each CR3 in the measured reference process. All 50 Canon originals
matched the frozen ordered hashes and byte sizes before and after the run
(442,098,996 B). ExifTool and the corrected reference agreed on the
5088×3392 camera-recommended geometry on every frame. The manifest
retains the pinned source and CC BY 4.0 attribution.
[Build and harness provenance](build.json) [Verified package](sealed-package-verification.json)
[Acquisition](acquisition.json.gz) [Per-frame metadata](metadata.json.gz)
[Target and input preflight](preflight.json.gz)

The quiet window ran 15:03:28–15:45:15 SGT on 2026-11-18 with both targets
on the same AMD Ryzen 9 7950X3D. Both used logical CPUs 0–14 (one thread
from each physical core), 15 worker threads in the launcher settings,
32 GiB per-process address-space cap, and separation from the RSS collector
pinned to CPU 15. CPU 31, the collector's SMT sibling, was also outside the
worker affinity. The frozen settings were Hybrid, first-frame similarity
alignment, kernel 6, eight pyramid levels, alignment scale 6, auto crop,
no slabs, and RGB16. [Quiet window](quiet-lease.txt)
[Host and thermal start](window-start.txt) [End and exit status](window-end.txt)

## Frozen results

All 34 primary launches succeeded in schedule order, with two warmups,
ten warm measurements and five fresh-cache cold measurements per target.
Both diagnostic jobs confirmed CPU execution and reproduced all ten warm
pixel digests for their respective target. The strict profile verdict was
**fail**, with both speed gates missed. [Summary](summary.json)
[36 samples](samples.csv)

| Metric | Pancake | ChimpStackr | Ratio | Gate |
| --- | ---: | ---: | ---: | --- |
| Warm median, limit 0.50 | 94.402869 s | 40.597604 s | 2.325331 | Fail |
| Cold median, limit 1.00 | 95.289787 s | 46.766705 s | 2.037556 | Fail |
| Process-tree peak RSS, limit 0.50 | Pending | Pending | Unavailable | Pending |

Even with a separate collector core, gaps exceeded 20 ms in 9 of 17
Pancake runs and all 17 reference runs, with maxima 29.114 ms and
44.593 ms. The largest per-job gap was interior to each affected job.
The longest reference snapshot took 43.020 ms of wall time and 6.396 ms
of collector CPU time. The collector used 24.1% and 57.1% of one core
over Pancake and reference primary wall time respectively. Observed
process-tree lower bounds were 2,695,991,296 B and 8,931,594,240 B.
The kernel's separate child-process high-water values were 2,696,335,360 B
and 8,968,847,360 B. Process-tree peak RSS remains unresolved.
[Recomputed cadence](rss-cadence.json)
[Exact run and resource receipts](raw-paired-runs.tar.gz)
[Archive checksum](raw-paired-runs.sha256)

## Geometry and focus review

All outputs were genuine RGB16 at 5086×3390. Each diagnostic recorded
50 identity alignments. The first warm exports cover the same first-frame
rectangle `[1,1,5087,3391]` in left, top, right, bottom coordinates.
Independent TIFF decoding confirmed both recorded digests. Over
51,724,620 RGB samples, mean absolute error was 506.42 u16 codes
(about 1.97 u8 codes), RMS was 669.39 and the largest error was 52,299.
The different pixel digests and a slight local darkening match the
earlier full R50 functional comparison. Specimen edges, the thin
filament and fine surface texture are resolved at corresponding locations.
The four sustained-texture tiles show a 1.16–1.40 candidate/reference
ratio in 90th-percentile absolute luma Laplacian. This review documents
regional differences at native coordinates and leaves the campaign
quality gate open. [Focus comparison and hashes](focus-comparison.json)
[Earlier independent functional comparison](../../../../pancake/docs/p10-r50-integrated-quality/README.md)

## Replay and cleanup

Prepare a checkout at the exact product revision, initialize the pinned
ChimpStackr submodule and run `uv sync --frozen` in its reference adapter.
Extract the package CLI into `pancake/target/release/pancake-cli` and verify
the build receipt. Apply the retained harness difference, which adds
review-pair retention and optional RSS collector affinity. The CUDA-specific
runner option in that difference is inactive for this profile. The frozen
targets and reference inputs retain their original hashes.
[Exact harness difference](paired-harness.diff.gz)
[Reference input acquisition and inspection commands](../../../../pancake/docs/p10-r50-integrated-quality/README.md#reproduce)

```sh
# Set sealed_checkout to the exact runtime checkout.
# Set scratch to the owned stage with verified inputs, build.json and quiet-lease.txt.
proof="$PWD/qualification/p10-performance/evidence/integrated-r50-12f2151"
ref=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
bash "$proof/run-paired.sh.txt" "$sealed_checkout" "$scratch"
"$sealed_checkout/$ref/.venv/bin/python" "$proof/compare-r50.py.txt" "$scratch/paired"
python3 "$proof/cadence.py.txt" "$scratch/paired"
```

The stage originals, TIFFs, previews, runtime caches and independent package
copy were removed after their hashes and logs were retained. Two originals
were transferred with verified hashes to the separate RAW decode parity
check, whose owner handles their cleanup.
[Cleanup](cleanup.json) [Two-file transfer](staging-transfer.json)
