# P0 real corpus and preliminary reference baseline

Date: 2026-11-17, Asia/Singapore. Worktree: `codex/p0-performance`, based on
`8fcbc52`. Status: real D150/E9 corpus acquired and pinned; two preliminary
reference CPU jobs completed. **No performance target or P0.16 pass is claimed.**

## Corpus selection

| Workload | Real data frozen | Precision and limits |
|---|---|---|
| D150-native-dorsal | First 150 source-filename-sorted frames from the 152-frame amber mite dorsal optical focal stack; 2304x1728 RGB JPEG | Original 8-bit photographs. No upscale, duplicated frame, or artificial precision promotion. Not the 24 MP RGB16 TIFF workload. |
| E9-native-balloons | All nine Balloons photographic exposure brackets from Waterloo MEF; 512x339 RGB PNG | Original 8-bit exposure images. Correct exposure-fusion domain, separate from focus stacking; nine frames exercise 4+4+1 batching. |
| T50 | Not selected | Still needs 50 real 6000x4000 genuine RGB16 ZIP TIFF sources. |
| R50 | Not selected | Still needs 50 real native RAW frames with pinned provenance. |

The [corpus manifest](../../pancake-conformance/src/pancake_conformance/adapters/pancake/performance-corpus.json)
contains every selected image's path, SHA-256, byte size, shape, mode, order,
archive URL/hash, source revision, and recorded rights evidence. Original
photographs, source archives, generated standardized TIFFs, and output images
remain ignored local data in this worktree. They are not added to Git.

Sources are the existing Bokehforge frozen selections:

- D03 [amber mite focal stacks](https://doi.org/10.6084/m9.figshare.14707077.v1),
  version 1; recorded CC BY 4.0. Dorsal archive SHA-256
  `311ca6aab7d3bff03c714fd2d81c741f3847de1d4d3f2f9cfa767b6eb62cf56a`.
- D28 [Waterloo MEF](https://ivc.uwaterloo.ca/database/MEF/MEF-Database.html),
  creator reuse/attribution terms recorded in config. Archive SHA-256
  `02939e5eb63d0536793e467848c9381e41c71ca1642b9f0291e2fc0843744242`.
- D05 Lytro was also acquired/processed successfully, but is not used in these
  measurements. Its config records unresolved image terms; no image is redistributed.

Total unique native acquisition was **214,404,651 bytes**, below the unchanged
2 GiB budget. D03's configured 150 MiB acquisition cap selected three archives.
Disabled D01 was not resolved or downloaded. No policy or source pin changed.
Acquisition and source conversion completed within approximately three minutes;
the six-minute bounded discovery window did not require fallback data.

Bokehforge generated lossless float32 linear-sRGB TIFFs with conversion recipes
and provenance, but the measured jobs consume the untouched native JPEG/PNG
members. Those photographs have no independent all-focus or calibrated HDR
truth. Output structure can be validated here; equal-quality acceptance still
needs the unchanged synthetic conformance corpus and declared real-image checks.

## Completed-job measurements

Reference: ChimpStackr commit `ab7a92708269c01c6094729f6cdfaf1415677364`;
its own initialized submodule and frozen adapter runtime in this worktree.
Hardware: local Apple M4 Pro, 14 CPU cores, 48 GiB, macOS 26.2 build 25C56.
Both jobs explicitly selected CPU. Environment: `NUMBA_NUM_THREADS=14`,
`OMP_NUM_THREADS=14`, `OPENBLAS_NUM_THREADS=1`; the conformance runtime's
two-thread settings were not used. The exact runtime lock hash is retained.

| Job | Samples | Full process wall time | Peak process RSS | Result |
|---|---:|---:|---:|---|
| D150 Hybrid, breathing alignment, slabs 40/overlap 4 | 1 | 30.585 s | 2,897,117,184 bytes | Exit 0; 2304x1728 RGB uint16 TIFF, finite values, original input hashes unchanged. |
| E9 exposure fusion, no alignment | 1 | 0.877 s | 237,469,696 bytes | Exit 0; 512x339 RGB uint16 TIFF, finite values, original input hashes unchanged. |

Both jobs used kernel 3, pyramid levels 4, scale factor 6, and 16-bit TIFF
export. D150 requested first-reference breathing and reported cumulative scale
1.0000-1.0003 with **145 fallback steps**. That is a useful warning against
claiming real-scene registration quality from completion alone; no independent
geometry truth was evaluated here.

External wall timing includes interpreter startup, import/JIT/cache work,
per-frame decode, alignment when selected, fusion, and complete TIFF export.
The CLI's smaller numerical timers (26.62 s and 0.13 s) exclude parts of that
work and are not substituted for full-job measurements. `/usr/bin/time -l`
reported peak RSS in bytes; this does not measure GPU memory or justify adding
CPU/GPU allocations as independent physical pools on unified memory.

The [baseline manifest](../../pancake-conformance/src/pancake_conformance/adapters/pancake/performance-baseline.json)
retains command templates, environment/cache settings, output hashes/structure,
resource counters, log hashes, and approximate filesystem execution intervals.
Reference stdout/resource logs are committed as small evidence files; terminal
progress stderr is retained losslessly as gzip. Full commands, outputs, and
raw logs remain under ignored `artifacts/p0-performance/` in this worktree.

Approximate job intervals were 00:25:15-00:25:46 UTC. Runtime agent confirmed
no heavy CPU/GPU work immediately before launch. OS background load, frequency,
thermals, and contention were not independently sampled, so controlled-load
performance is not claimed.

## Qualification still required

These are **single fresh-process diagnostic samples**, not warm-engine medians.
A new worktree-local Numba cache was used initially; E9 followed D150 and reused
populated import/kernel caches. OS file caches were not cleared. There were no
two warmups plus ten measured warm jobs or five fresh-cache cold runs.

These jobs also differ from the frozen target profile: kernel 3/levels 4 rather
than 6/8, no auto-crop, and E9 without the target's Euclidean alignment. Exact
profile equality must be established before a future matched comparison;
these single diagnostic values cannot be promoted into qualified baselines.

The integration-owned target specification remains authoritative: at least 2x
warm completed-job speed, no more than 50% reference peak process memory at
equal quality, nonregressing cold median, viewer event-to-present P95 at most
33 ms, and pause/cancel safe-state acknowledgement at most 250 ms.
The present numbers cannot establish any of those relative targets.

Remaining work includes the other three focus methods, full sampling protocol,
actual GPU jobs/runtime identity, same-quality Pancake comparisons, full
precision/geometry validation, and viewer/lifecycle latency. T50/R50 acquisition
remains open. No real photograph is resized or converted from 8-bit into claimed
genuine 16-bit evidence to fill those gaps.

## Reproduction

From this worktree's root, using the unchanged 2 GiB policy:

```sh
git submodule update --init submodules/ChimpStackr
uv sync --frozen --project pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
uv run --project bokehforge --frozen bokehforge data download --dataset D05 --dataset D28
uv run --project bokehforge --frozen bokehforge data download --dataset D03
uv run --project bokehforge --frozen bokehforge data process --dataset D05 --dataset D28 --workers 2
uv run --project bokehforge --frozen bokehforge data process --dataset D03 --workers 2
```

For a measurement, use the manifest's ordered native frame paths and command
template from `submodules/ChimpStackr`, with the recorded thread environment and
worktree-local cache paths. Prefix the actual reference Python command with
`/usr/bin/time -l -o RESOURCE_FILE`, redirect stdout/stderr into a new case
directory, wait for completion, independently decode output, and recheck input
hashes. No executable benchmark implementation is added by this evidence commit.

The captured corpus requires this retained worktree's ignored data or a verified
reacquisition. Moving metadata into main does not copy images or claim a target
comparison. Conformance source outside adapters and all source photographs stay
unchanged.

Verification: local scaffold `scripts/check.sh all`, staged whitespace checks,
manifest/log/archive hashes, unique native input hashes, output decoding, and
local links passed. Scaffold checks still contain zero application tests; no
application coverage percentage is claimed. Remote/platform/sanitizer, GPU,
full statistical, viewer, and lifecycle qualification runs were not performed.
