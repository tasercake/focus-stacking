# Preregistered 11-source D150 anchor and skip-edge diagnostic

This plan pins the investigation from `af964f5dab976a276e1b91cf4db0b2d63e8063c1`. It tests whether the independent optical witness sees a link to the First anchor and whether the existing shared matcher can produce supported alternatives across the late ambiguous interval. It gives no full D150, production geometry, quality, or performance result. No image or archive was acquired, no diagnostic adapter was written, and no executable was built or run. [Anchor evidence](../anchored-recovery-review/README.md) · [Exact manifest and evaluation plan](plan.json).

## Inputs and allowed comparisons

| Fixed cohort | Frozen zero-based indices | Original captures |
| --- | --- | --- |
| First-anchor neighborhood | 0, 1, 2 | 0516, 0517, 0518 |
| Genuine-step control | 63, 64, 65, 66 | 0579, 0580, 0581, 0582 |
| Late ambiguous interval | 137, 138, 139, 140 | 0653, 0654, 0655, 0656 |

The exact named JPEGs, sizes and bit digests appear in `plan.json`. Fresh edges are `0→1`, `0→2`, `1→2`, `137→139`, `137→140`, and `138→140`. Replay the three old adjacent edges in each of the two four-source controls against their fixed prior candidates. `64→65` is the genuine-motion control and `138→139` is the false-jump control. Keep the other edges in the report even if they abstain. The arm needs at most 12 fresh directed product estimates and never scans new edges in response to a result. [Prior six-edge results](../witness-batching/real-summary.json).

Estimate the fresh directions on the shared CPU path with Breathing, scale six, 384×288 proxy, 5% maximum scale step and ordinary precision. Each edge has at most three proposed maps in the native `before→after` coordinate system. Use the positive forward estimate, the inverse of the positive reverse estimate, and an identity comparator. Reject a measured proposal with nonfinite or singular coefficients or an isotropic scale outside the existing forward interval after inversion. A zero-confidence result leaves the slot unavailable. Collapse exact duplicate maps and keep the slot provenance. The old controls use the same archived direct and inverse-reverse proposals plus identity. Both separate optical fits from the existing bilateral tool are useful controls. They cannot become selected product proposals in this trial. Record every proposal status, matrix, confidence, measurement and disagreement.

## Prespecified independent native screen

Use OpenCV 4.14.0, one thread, and disable OpenCL. Retain the existing image authentication, prefilter and fixed 9×9 grid spread over 16–84% of each native axis. The existing reciprocal tracker uses its 25×25 window, two pyramid levels, maximum round-trip drift of 0.35 native pixels and maximum forward LK error of 12. The independent local fit excludes candidate training centers within 39 native pixels of the held-out grid. The hold-out searches start at fixed positions in each direction without using a predicted map. This avoids fitting to their measured locations. Product proposals still use the existing full proxy. [Native correspondence and training tool](../local-track.py.txt) · [Existing bilateral measurement](../motion-admission/bilateral.py.txt).

Each direction must retain at least four valid witnesses in three or more noncollinear macrocells. A macrocell is one of the 3×3 consecutive groups of three fixed witness-grid rows and columns. Require directional median residual at most 2.0 native pixels and strictly more than 1.0 native pixel advantage over every other actual proposal, including identity. Repeat the same bounds separately after omitting each occupied macrocell in that direction and require at least three witnesses after each omission. The two-pixel envelope is a conservative diagnostic screen at twice the existing one-pixel known-transform tolerance. The one-pixel advantage uses that same geometric scale to avoid promoting a small observed difference. They are empirical screens for this trial. Round-trip consistency supplies no calibrated absolute localization bound, and the synthetic bilateral tool’s 0.20 px allowance has no role here. [Known-transform tolerance](../../../../pancake-conformance/docs/algorithm-contract.md).

An edge abstains if the data are insufficient, the directions disagree, a leave-one-cell-out check changes the result, or the candidates tie. Identity alone supplies no proof of stationary motion. Label an edge `native_supported_proposal` only after the entire screen passes. Record absolute forward and inverse medians and per-point errors even when a comparative check abstains. The packed witness can record corroboration or contradiction when its independent proxy cells support a uniquely ranked proposal. It uses at most nine cells, two lattices, three proposals and 54 queries per direction. Keep common valid overlap, the existing cross-fit comparison and two-axis footprint, and the `1 / 65,536` floor. Native and proxy disagreement stays unresolved. A clean local result needs its own verified link to a trusted pose. In particular, `1→2` alone never connects either node to First.

The control comparison must recover a supported nonidentity alternative at `64→65` and reject the historical direct jump at `138→139`. Report a control miss as inconclusive for the proposed recovery. Preserve its observations and the original bounds for review.

## Owned stage and later commands

The prior owner removed the authenticated archive and all nine originals. The new `D03` download is exactly 53,459,291 bytes before extraction and the 11 verified originals total 3,582,818 bytes. ZIP and originals can temporarily coexist at 57,042,109 bytes. Use the exact ordered entries and SHA-256 values in `plan.json`. The frozen manifest, source revision, rights, archive SHA and download limit are recorded there. The retained manifest authenticates an intended stage. It does not establish that a staged file currently exists. [Previous cleanup](../witness-batching/real-cleanup.json).

The existing acquisition helper accepts exactly nine entries. A later reviewed copy can require exactly the eleven listed plan rows while reusing its bounded byte-and-hash download and extraction. The original helper stays pinned. The old product probe accepts nine files and computes 28 directed fits in two windows. Its later adapter should read the registered graph and call the same decode, thumbnail and estimate functions on only the 12 fresh directions. The prior bilateral CLI also hard-codes nine records, 28 fits and six adjacent edges. A later adapter should call `bilateral()` on the 12 listed pairs, then apply the fixed native screen. The packed overlay consumes a fixed three-map batch and six archived intervals. Reuse its record kernel and serial-versus-packed bit checks. A later test-only adapter needs to take the new edge plan, skip its old repeat-timing loop and handle unavailable candidates by explicit abstention. Do not pad missing slots with a fabricated map or change the original archived tool. [Existing bounded acquisition](../motion-admission/acquire-probe.py.txt) · [Existing product probe](../motion-admission/probe.rs.txt) · [Pinned overlay](../witness-batching/real-overlay.patch.gz).

After independent adapter review and a separate execution grant, the proposed exact invocation is below from the owned checkout. Adapter files named here are proposed case-owned copies. They do not exist at this revision. Build any later native probe as a locked debug example in a separate target before running it, without release or GPU targets. The CPU list requires the scheduler's grant.

```bash
plan="$PWD/pancake/docs/d150-geometry-audit/anchor-skip-prereg/plan.json"
scratch="$PWD/artifacts/d150-anchor-skip-011/run-001"
acquisition="$scratch/materialized/acquisition.json"
timeout --signal=TERM --kill-after=5s 180s python3 "$scratch/acquire-probe-011.py" \
  --audit "$plan" --output "$scratch/materialized"
timeout --signal=TERM --kill-after=5s 150s taskset --cpu-list 20,21 \
  "$scratch/bin/d150-anchor-skip-probe" --plan "$plan" --acquisition "$acquisition" \
  --output "$scratch/product-proposals.json"
timeout --signal=TERM --kill-after=5s 150s taskset --cpu-list 20,21 \
  "$reference_python" "$scratch/bilateral-011.py" --plan "$plan" --acquisition "$acquisition" \
  --trace "$scratch/product-proposals.json" --output "$scratch/native-holdouts.json"
```

The single packed corroboration replay follows native screening under a separate test-only command. Its adapter is unimplemented. Before any prospective repeat, seal the exact binaries, commands, environment, exit codes, stage hashes and all abstentions. The previous six-edge CPU development diagnostic completed in 8.92 seconds including proxy preparation and 42 repeated parity samples. Allow a cold two-job debug build of roughly 2–5 minutes and plan 15–90 seconds for the expanded CPU observations, with the stated watchdogs. Transfer time depends on the authorized source connection. These are scheduling estimates. The named owner checks every reader is terminal, rehashes the 11 originals, removes the owned ZIP and originals, and retains only input receipts, bounded output records and reproducible diagnostic source. No original file enters Git.
