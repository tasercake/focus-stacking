# D150 alignment and crop discrepancy

The first completed official CPU pair on locked candidate `12f2151` used the
frozen 150 original 2304×1728 JPEG8 frames with Hybrid, breathing, first-frame
reference, scale factor 6, 40-frame slabs with four overlapping sources,
pyramid levels 8, kernel size 6, 16-bit TIFF export, and auto-crop. The preserved
output metadata reports 2130×1530 for Pancake and 2288×1696 for ChimpStackr.
Those shapes imply symmetric left/right and top/bottom trims of 87/99 px and
8/16 px respectively. The candidate contains **16.02% less raster area** than
the reference. The elapsed and memory measurements are separate from this
read-only audit. Neither timed executable was instrumented for alignment.

## Pairing and crop semantics

The pinned ChimpStackr CLI's mode and limit descriptions identify breathing as
sequential and apply the scale bound per consecutive pair. Its API selects
the first or middle **coordinate anchor** independently of that pairing.
It estimates forward maps between adjacent sources, normalizes each source
to the first-frame canvas, composes forward or inverse steps into the
requested anchor, and warps each registered slab frame using its precomputed
map. First-reference breathing therefore does not fit every later source
directly to frame 0.
[Reference CLI](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/cli.py#L69-L113)
· [Reference alignment dispatch](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/API.py#L144-L200)
· [Reference step and composition](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/__init__.py#L1035-L1129).

Pancake's public `AlignmentMode::Breathing` also describes alignment between
adjacent frames. In the archived/current engine, the proxy is updated to
the latest source only for explicit `Previous`. Breathing plus `First`
keeps frame 0 as the estimator template. The published sequential events
then derive relative maps by differencing independent fixed-reference
results. The fixed template compares sources with increasingly different
focused regions. A newly accepted distant match can abruptly replace
identity without establishing that the camera moved by that amount between
neighbors.

Both targets trim symmetric `ceil(max absolute corner displacement)+1`
on each axis. ChimpStackr uses image edges `(w,h)` for corner displacement
and Lanczos interpolation plus replicate borders for sequential warps.
Pancake uses pixel-center corner extrema `(w−1,h−1)` and bilinear sampling
with a clamped border. Neither of those differences explains the 79/83 px
margin gap on the same admitted maps. The estimators and resamplers remain
distinct even if the pairing strategy is corrected.
[Reference crop formula](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/API.py#L112-L141)
· [Reference displacement tracking](https://github.com/tasercake/ChimpStackr/blob/ab7a92708269c01c6094729f6cdfaf1415677364/src/algorithms/__init__.py#L464-L474).

## Archived Pancake geometry

The earlier coherent archived CPU event at `cb5e3a4` has 150 finite
reference-to-source maps. Indices 0–61 are exactly identity, followed by a
single transition to the nonidentity segment. Between consecutive
`P9160577_d2.jpg` and `P9160578_d2.jpg`, maximum corner displacement changes
by **68.52 px**, compared with a **0.40 px** median adjacent change. The
new absolute map turns on a 1.897% isotropic scale change and absolute
translation `[-50.26,+13.81]` px. All 88 remaining maps stay nonidentity.
The continuity break is consistent with a distant fit crossing its
confidence threshold and raises substantial doubt that the crop represents
true adjacent camera motion. Stage movement cannot be ruled out from stored
matrices alone.

For the archived maps, exact inverse-mapping validity gives symmetric native
insets of 85/97 px before an interpolation margin. The existing conservative
corner rule gives 89/102 px and reconstructs the older decoded 2126×1524 crop.
Thus crop arithmetic accounts for four or five pixels of the archived trim.
A smaller border chosen without revisiting the fitted geometry would retain
source samples that are outside the admitted maps. This archived trace is
not attributed to the fresh timed candidate, whose matching full trace is
still pending at this point in the audit.
[Archived calculation](archive-geometry.log) · [Reproducer](archive-geometry.py.txt).

## Held-out geometry after timing

1. Use the exact read-only source pair 61→62 and controls 60→61 and 62→63.
   Confirm source hashes against frozen acquisition. Use a fixed grid of
   small textured patches in the central specimen and prefilter Gray
   samples lightly to tolerate focus changes. Select patches before viewing
   either estimated transform.
2. Match those patches with bidirectional normalized correlation bounded
   to a local search large enough for both motion hypotheses. Exclude weak,
   repeated or nonreciprocal matches. Report the held-out pixel residuals
   of identity and of `M[i+1] · inverse(M[i])` predicted by each independently
   rerun target. The robust local translations across distinct patches
   distinguish a real scale jump from a global estimator changing regimes.
   Report insufficient texture as inconclusive.
3. After acquiring the completed official trace and exports, project
   identical specimen regions into both crops using each actual first-frame
   origin. Confirm matte/edge inclusion and landmark coherence before any
   sharpness, detail or color comparison. Compare native pixels in the
   shared canvas without stretching either export. Preserve evidence from
   regions outside that shared rectangle separately.
4. A corrected adjacent-chain candidate still needs the known-motion
   sequence red/green result, held-out real source confirmation, and all
   unchanged relevant P5, slabbing and CPU/physical GPU regressions.
   Any new release still needs its own frozen performance and quality
   evidence. These diagnostic checks do not modify the reference or any
   acceptance threshold.

The fresh `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` CPU diagnostic returned
all 150 maps. The first 139 are identity. At `P9160654_d2.jpg` →
`P9160655_d2.jpg`, its map changes by up to 129.796 px on the first-source
canvas, with +3.445% isotropic scale and `[-85.19,+38.44]` px absolute
translation. It stays nonidentity for the last 11 frames. The fresh reference
adjacent change has median 0 and maximum 8.492 px at a different pair. These
geometry diagnostics had the same respective decoded pixel hashes as each
target's ten measured warm exports.

The independent check authenticated the eight original JPEGs against the
frozen manifest before and after analysis. It used unmodified thresholds on
72×72 patches selected on a fixed grid, Gaussian prefilter σ1.5, ±96 px search,
minimum normalized correlation 0.8, minimum sidelobe separation 0.025, and
reciprocal error ≤2 px. The three-match minimum was fixed before either
diagnostic. No fitted target maps were used to find image correspondences.

| Target transition | Accepted patches | Observed movement | Median estimated-map error | Identity median |
| --- | ---: | ---: | ---: | ---: |
| `cb5e3a4` 577 → 578 | 17 | ≤1.42 px | 42.24 px | 1.00 px |
| `12f2151` 654 → 655, initial 5×5 grid | 2 | ≤2.24 px | Inconclusive | Inconclusive |
| `12f2151` 654 → 655, separate 9×9 grid | 9 | ≤2.00 px | 102.89 px | 1.00 px |

The supplemental grid expanded the sampled area with disjoint patches while
keeping exactly the same image matching criteria. All nine predicted residuals
at the fresh abrupt transition fell within 74.10–114.35 px. The reference map
has 1.00 px median residual on the same nine. The immediately preceding and
following pairs had nine and seven accepted landmarks respectively, and the
candidate agreed with them within 1.00 px median. The measured jump is a bad
estimate of consecutive source motion. These observations do not determine
the full end-to-end trajectory or certify the reference stack as ground truth.

The first measured warm RGB16 exports independently decoded at 2288×1696 and
2130×1530. Across five prespecified 72×72 regions on their shared first-source
canvas, mean absolute error ranged from 2,539.72 to 4,230.82 u16 codes and
luminance correlation ranged from 0.145 to 0.970. Each export was projected by
its measured crop offset, `[8,16]` and `[87,99]`, without resampling. These ROI
measurements diagnose local disagreement. The frozen run still records a
geometry mismatch.

[Diagnostic source](landmarks.py.txt) ·
[Archived 5×5 grid and warm ROIs](landmarks-old.json.gz) ·
[Fresh 5×5 inconclusive grid](landmarks-new.json.gz) ·
[Fresh 9×9 supplemental grid](landmarks-dense.json.gz).

From the repository root, with the exact acquired originals and traced
outputs staged by the D150 harness:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$reference_python" \
  pancake/docs/d150-geometry-audit/landmarks.py.txt \
  --first-source 653 --dense --source-root "$d150_stage/inputs" \
  --reference "$d150_stage/paired/diagnostic-01/reference/events.jsonl" \
  --candidate "$d150_stage/paired/diagnostic-01/candidate/events.jsonl" \
  --exports "$d150_stage/paired/warm-01/reference/complete.tif" \
            "$d150_stage/paired/warm-01/candidate/complete.tif"
```

The [adjacent-pair prototype](prototype-ff2c037/README.md) includes the
test-first results, full 150-frame CLI geometry trace, and comparison on the
same four fixed specimen regions. The prototype removed the false jump but
its full D150 output retained the soft detail observed in the sealed job.

The [local-motion follow-up](subpixel-diagnostic/README.md) includes the
independent native track, same-map interpolation controls and a second full
CPU prototype. It recovered 54 consecutive motions and removed the false
jump. The four fixed focus regions became softer, so the quality gap remains
open and the production experiment stays separate.

The [bounded-cubic sampling study](breathing-sampling/README.md) recovered
subpixel signed detail in an independent analytic fixture. Its exact paired
D150 RGB16 exports had byte-identical transforms and matching crop. The
four historical focus regions became slightly softer, so the independent
sampling change stays separate from the release.

The [nine-original anchor-direction probe](motion-admission/README.md)
reproduced the wrong direct jump and independently confirmed the genuine
adjacent motion. Positive inverse reverse-anchor fits matched both nearby
transitions more closely on held-out bilateral landmarks. Direction choice,
the long-range trajectory and fused quality remain open.

The [bounded witness design](witness-design/README.md) compares the same
directional histories in scale-6 proxy coordinates. It identifies the
invalid one-frame absolute switch, the false jump's narrow support, and
what can be validated with existing CubeCL moments. A batched witness,
reverse-estimation demand and fused output quality still need measurement.

The [passive CPU pilot](witness-pilot/README.md) verified that the actual
scale-6 luma retains evidence for the genuine step. It ranked the
inverse-reverse hypothesis first in eight of nine cells. The wrong direct
step lost wherever all models had comparable evidence, and the
replacement global pose remained unresolved. The pilot also records the
exact unbatched observation cost and authenticated input cleanup.
