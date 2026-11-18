# Camera-recommended Canon CR3 reference

The corrected R50 reference develops each original CR3 with the existing
locked RawPy/LibRaw runtime. It takes the crop from validated camera capture
metadata, applies camera white balance and the recorded saturation level, and
encodes the developed output as sRGB RGB16. The crop is taken in sensor
coordinates before applying orientation. This respects the camera's authored
image rectangle and uses the application’s established color space. LibRaw's
wider compatibility-table rectangle and historical default transfer remain
documented in the original comparisons. [Prior geometry evidence](../p2-cr3-resume/README.md)

The same two frozen real Canon CR3 files gave 5088×3392 in both Rawler and the
corrected independent RawPy path. The older RawPy path gave 5118×3412. Across
the common sensor rectangle, normalized RGB mean absolute error was 0.075572
and 0.075289 with the historical reference. With the corrected reference,
full matching-size RGB error was 0.004115 and 0.004095, with signed channel
bias below 0.000170 in magnitude. The largest individual channel errors
remained 0.7884 and 0.8053. RawPy keeps its independent demosaic and calibration
implementation. This comparison establishes matching crop and color policy.
Numerical image quality for complete stacks remains a separate check.
[Full per-frame data](capture-comparison.json)

Changing only the EXIF Orientation of a scratch copy of frame 000 produced
an exact 90° clockwise rotation of the decoded RGB16. The source frame
and frame 049 matched their frozen hashes before and after every job.
Metadata checks reject rectangles outside the decoded sensor, unsupported
orientation, and missing or incompatible calibration. The current profile
requires shared channel black and white levels. It fails explicitly when
the metadata cannot support that calculation.

The real ChimpStackr Hybrid CPU job read two frozen CR3 sources, used the R50
reference settings and exported a 5086×3390 TIFF. The existing observer
recorded CPU stacking completion, crop and actual publication. Independent
TIFF validation verified native RGB16 with codes beyond eight-bit promotion.
The truncated CR3 replay reported the path and preserved its existing
destination. The observer reported completion status false and recorded no
export. [Functional receipt](functional-receipt.json)
[Completion events](complete-events.jsonl) [Malformed-input events](corrupt-events.jsonl)

The benchmark driver selects this launcher only for R50 and fingerprints it
before and after a campaign. It derives the output bounds from the oriented
camera rectangle of the first source. Full source decode happens inside the
reference CLI process on every run. ChimpStackr's method, reference, alignment,
crop-after-stack and export use the existing pinned CLI. The production
Rawler path, other reference workloads, 376 frozen case definitions,
performance thresholds, source bytes, lock and reference descriptor retain
their identities. The two-frame job is functional evidence. A full R50
performance campaign and quality review remain pending.

## Reproduce

Start at `43e884791c70839371e3266f5b9d68bbb4611f31`. Initialize the pinned
ChimpStackr submodule and sync the existing reference lock. Download only
manifest rows 0 and 49, verify byte counts and SHA-256, and put the
originals at `artifacts/cr3-reference/sources/frame_000.CR3` and
`artifacts/cr3-reference/sources/frame_049.CR3`. For the comparison, copy the
standalone Rawler probe and manifest from the prior geometry evidence as
described there, using `artifacts/cr3-reference/probe` as its build root.
The analytical comparison consumes the default develop path.

```sh
scratch=artifacts/cr3-reference
proof=pancake/docs/p2-cr3-reference-evidence
ref=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
git submodule update --init submodules/ChimpStackr
uv sync --frozen --project "$ref"
export PYTHONPATH="$PWD/qualification/p10-performance"
exiftool -o "$scratch/sources/portrait.CR3" '-IFD0:Orientation#=6' \
  "$scratch/sources/frame_000.CR3"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 "$ref/.venv/bin/python" \
  "$proof/compare-capture.py.txt"
"$ref/.venv/bin/python" "$proof/replay.py.txt"
"$ref/.venv/bin/python" -m pytest -q qualification/p10-performance \
  pancake-conformance/src/pancake_conformance/adapters/pancake/test_cr3_reference.py
```

The adapter and runner tests initially failed because the reference policy
and launcher did not exist. The final focused test run passed 55 tests and
three subtests, and Ruff passed. Scratch original CR3s, orientation copy,
output rasters and diagnostic build were removed after verification.
[Cleanup receipt](cleanup.json)
