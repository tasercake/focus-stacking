# Staged passive bilateral witness pilot

Diagnostic-only source is staged on `3cd43b5756bc7e6036a46a6be2824e45a094401e`.
The test calls the existing CubeCL `correlation_moments` kernel on two
fixed sampling lattices per region. It fits exposure gain and offset on
one lattice, validates on the other, and exchanges query and source for
the second direction. It checks a known signed translation in a continuous
two-axis texture with a photometric gain change, an aperture with two
indistinguishable horizontal maps, and motion confined to one column of
witness regions. The geometry oracle and test coordinates are confined to
the diagnostic. [Witness design](../witness-design/README.md).

The original short window ended before a fresh build could complete. In
the later authorized window, exact `8410863` production source and lock
matched `3cd43b5` and compiled on CPUs 2 and 3 with Rust 1.100.0. The real
CubeCL CPU synthetic test passed all three controls. Cargo recorded a
1m07s build and 0.06s test duration. The source and sampled geometry are
synthetic. Those durations supply no D150 performance evidence. [Synthetic test log](synthetic-8410863.log.gz).

## Minimal synthetic replay

Replay in an isolated worktree with its original application files clean.
The overlay is temporary and uses the private normal sampling kernel,
keeping all diagnostic symbols out of the released product. The synthetic
frame and translations guarantee interpolation support for all sampled
tiles. The fixed-layout helper and rounding screen are smoke-test machinery.
They require general common-overlap handling, independent uncertainty
calibration and bounded batching before use for production or cost analysis.

```bash
repo=$(pwd)
proof=$repo/pancake/docs/d150-geometry-audit/witness-pilot
kernel=$repo/pancake/src/registration/kernels.rs
overlay=$repo/pancake/src/registration/witness_pilot.rs
scratch=$repo/artifacts/d150-witness-pilot
git diff --exit-code -- "$kernel"
test ! -e "$overlay"
mkdir -p "$scratch"
cp "$kernel" "$scratch/clean-kernels.rs"
(
  set -e -o pipefail
  trap 'cp "$scratch/clean-kernels.rs" "$kernel"; if [ -f "$overlay" ]; then unlink "$overlay"; fi' EXIT
  cp "$proof/witness_pilot.rs.txt" "$overlay"
  printf '\n#[cfg(test)]\n#[path = "witness_pilot.rs"]\nmod witness_pilot;\n' >> "$kernel"
  cd "$repo/pancake"
  CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
    taskset -c 2,3 cargo test --locked --lib witness_bilateral_motion_and_ambiguity -- --nocapture \
    2>&1 | tee "$scratch/synthetic.log"
)
```

## Real-luma observation

The optional test module takes the authenticated nine-original receipt and
the archived directional candidates. It decodes each interval sequentially
and calls the product's scale-6 luma prefilter at 384×288. A common native
pixel-center transform projects all candidates into that sampled extent.
All three maps and their inverses must have complete support for each
scored tile. Within each cell, the strongest proposal must beat both rivals
in both cross-fits and directions. Positive gain, an informative contrast
denominator and the small floating-point screen are scoped pilot checks.
The test records every cell and the two-axis spread of candidate support.
The per-record device launches measure this diagnostic only and give no
grouped-kernel, full-estimation or whole-job performance claim.
[Native independent comparisons](../motion-admission/README.md).

After the synthetic test, the optional replay requires these additional
paths and module in the same temporary overlay. Use the verified acquisition
output and a fresh result path. Both test filters can run in this overlay.

```bash
motion=$repo/pancake/docs/d150-geometry-audit/motion-admission
stage=$scratch/subset
taskset -c 2,3 python3 "$motion/acquire-probe.py.txt" --audit "$motion/audit.json" --output "$stage"
real=$repo/pancake/src/registration/real_pilot.rs
test ! -e "$real"
(
  set -e -o pipefail
  trap 'cp "$scratch/clean-kernels.rs" "$kernel"; for path in "$overlay" "$real"; do if [ -f "$path" ]; then unlink "$path"; fi; done' EXIT
  cp "$proof/witness_pilot.rs.txt" "$overlay"
  cp "$proof/real_pilot.rs.txt" "$real"
  printf '\n#[path = "real_pilot.rs"]\nmod real_pilot;\n' >> "$overlay"
  printf '\n#[cfg(test)]\n#[path = "witness_pilot.rs"]\nmod witness_pilot;\n' >> "$kernel"
  cd "$repo/pancake"
  PANCAKE_WITNESS_ACQUISITION="$stage/acquisition.json" \
    PANCAKE_WITNESS_DIRECTIONS="$motion/direction-replay.json" \
    PANCAKE_WITNESS_OUTPUT="$scratch/real.json" \
    CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
    RAYON_NUM_THREADS=2 taskset -c 2,3 cargo test --locked --lib witness_ -- --nocapture \
    2>&1 | tee "$scratch/real.log"
)
```
