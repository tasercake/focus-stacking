# D150 Hybrid CPU on the exact Linux release

The locked `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` release CLI was
extracted independently from its Debian package and matched the sealed
SHA-256 `32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055`.
The reference used ChimpStackr `ab7a92708269c01c6094729f6cdfaf1415677364`
and its frozen environment. The Figshare ZIP matched its recorded 53,459,291
bytes and SHA-256. All 150 selected original JPEGs matched the frozen ordered
manifest, decoded independently as 2304×1728 RGB8, and retained their hashes
after the campaign. [Build and harness provenance](build.json)
[Package verification](sealed-package-verification.json)
[Source acquisition](acquisition.json.gz) [Decoded originals](preflight.json.gz)

The coordinated benchmark window ran 13:41:43–14:22:06 SGT on
2026-11-18. Both targets used the Ryzen 9 7950X3D CPU, logical IDs 0–15
(one per physical core), the same 16-thread settings and inherited 32 GiB
per-process address-space limit. The complete frozen profile used breathing
alignment, first-frame reference, slabs 40/overlap 4, kernel 6, eight pyramid
levels, scale 6, auto-crop and RGB16.
[Start conditions](window-start.txt) [End conditions](window-end.txt)

## Frozen numeric results

All 34 primary launches completed successfully in the prescribed alternating
order. Each target completed two warmups, ten warm measurements and five
fresh-cache cold measurements. Both additional diagnostic jobs confirmed CPU
execution and reproduced their target's ten warm decoded-pixel hashes.
[Summary](summary.json) [36 samples](samples.csv)

| Metric | Pancake | ChimpStackr | Ratio | Gate |
| --- | ---: | ---: | ---: | --- |
| Warm median, limit 0.50 | 43.356797 s | 88.299508 s | 0.491020 | Pass |
| Cold median, limit 1.00 | 42.756521 s | 95.643264 s | 0.447042 | Pass |
| Process-tree peak RSS, limit 0.50 | Pending | Pending | Unavailable | Pending |

The 20 ms RSS sample-gap rule was exceeded in 9 of 17 Pancake jobs and all
17 reference jobs. Maximum gaps were 23.834 and 33.925 ms respectively.
Observed process-tree RSS lower bounds were 839,249,920 B and
3,412,643,840 B. The separate kernel child-process high-water values were
839,614,464 B and 3,413,954,560 B. Neither substitutes for the required
complete process-tree observation. The runner concluded `pending`.
[Exact raw timing and resource receipts](raw-paired-runs.tar.gz)
[Archive checksum](raw-paired-runs.sha256)

## Geometry and image quality

Both targets exported genuine RGB16. Pancake's 2130×1530 crop retained
84.0% of the reference's 2288×1696 exported area. In common first-frame
coordinates, the distinct rectangles were `[87,99,2217,1629]` and
`[8,16,2296,1712]` as left, top, right, bottom. The reference rectangle comes
from its observed diagnostic crop event. Pancake's origin follows from its
symmetric crop and the independently decoded extent. The raw diagnostic
receipts retain 150 source and sequential matrices per target.

The warm-pair comparison examined the common canvas without resampling.
RGB MAE was 3,220.34 u16 codes, about 12.53 u8 codes, and RMS was 4,805.35
u16 codes. In four matched texture-bearing specimen regions, Pancake's
90th-percentile absolute luma Laplacian was 0.686–0.706 times the reference's.
Visual inspection showed softer detail and doubled edges in the candidate
around the same anatomical structures. Different crop and registration
outcomes remain under investigation. This profile's speed gates passed.
Its RSS and equal-quality acceptance remain open.
[Crop and focus-region metrics](focus-comparison.json)

## Reproduction and temporary data

Use a clean `12f2151` checkout, its exact package-extracted CLI at
`pancake/target/release/pancake-cli`, the pinned reference checkout and
`uv sync --frozen` in its adapter runtime. The paired runner came from
`fbf01d1`, whose only change against this sealed harness was retaining both
requested first-warm review exports after completed gate misses. Existing
timing, sample order, resources and thresholds were used as implemented in
the frozen harness. Artifact paths and digests are in the build attestation.
[Exact cleanup-only difference](review-retention.diff.gz)

```sh
proof="$PWD/qualification/p10-performance/evidence/integrated-d150-12f2151"
scratch="$PWD/artifacts/d150"
ref=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
mkdir -p "$scratch"
python3 "$proof/acquire_d150.py.txt"
# Set sealed_checkout to the exact staged checkout. Prepare build.json with its
# executable path and verify all other hashes against the retained attestation.
(
  cd "$sealed_checkout"
  PYTHONPATH="$PWD/qualification/p10-performance" "$ref/.venv/bin/python" \
    "$proof/preflight_d150.py.txt" "$scratch"
)
bash "$proof/run-paired.sh.txt" "$sealed_checkout" "$scratch"
"$sealed_checkout/$ref/.venv/bin/python" "$proof/compare_d150.py.txt" "$scratch/paired"
```

The timing and analysis commands, custody records and logs are retained.
The acquisition ZIP, derived previews, runtime caches and isolated staged
package copy were cleaned. The 150 originals and exact first-warm TIFF pair
were transferred with verified hashes into the registration follow-up's
temporary lease. That task owns cleanup after the bounded corrected run.
[Lease and witness hashes](staging-transfer.json) [Local cleanup](cleanup.json)
