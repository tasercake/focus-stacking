# R50 Hybrid band accumulation prototype

Candidate `3d2782e8e30a66cef1b5248d62ff6f8042c30736` removes the transient Hybrid RGB band. The existing weighted CubeCL kernel already derives the coefficient from the fine and coarse Gaussian levels for Exposure. Hybrid now uses that input route, and a separate selection kernel derives the coefficient only when a pixel gets a new strict focus winner. Both passes fit the previous limit of five storage tensors. The CPU and physical Vulkan results matched the old path bit for bit. Exact locked candidate `903836c` passed every P4 case. Later exact-source receipts cover the isolated [native CUDA parity](native-cuda/README.md) and [completed R50 diagnostic](../p10-r50-component-comparison/README.md).

## Observed cost and scope

The exact one-copy R50 CPU run reports 42.072283 s at `07816a2`, paired with the packaged `287828a` control. Its separate GDB repeat measured 17.808 s of RAW decode, 7.944 s of thumbnails and 14.219 s of Hybrid frame fusion at 13.88 mean busy cores. That trace does not resolve individual fusion kernels. [One-copy stage receipt](../p10-r50-phase-287828a/owned-upload/README.md)

On the actual 5088×3392 input canvas with eight pyramid reductions, source-level launches go from 45 to 37 per frame. The finest band temporary was 207,101,952 bytes; all eight non-top band areas total 23,011,030 pixels per frame. Old temporary traffic was one RGB write, one unconditional weighted read, and one conditional winner read. At fraction `p` of pixels replacing winners, the removed temporary traffic is `24+12p` bytes per pixel. Recomputing a winning coefficient can read up to `60p` additional shallow RGB input and coarse sample bytes per pixel. This gives the nominal difference `24−48p` before caching and extra arithmetic, and removes one large allocation regardless of `p`. Actual traffic, RSS, and elapsed time need a paired run. [Exact R50 recipe and native canvas](../../../qualification/p10-performance/evidence/integrated-r50-12f2151/README.md)

The first-frame path does not read any uninitialized score. Later frames use the original strict `>` comparison, and an exact tie preserves the earlier source. The shared `expanded` code preserves the existing bilinear stencil and signed f32 subtraction. The uppermost level reads the source without expansion. Both kernels guard tail lanes. Per-frame synchronization still covers the same four persistent outputs. Budget checks, registration, cancellation points and Exposure and Laplacian kernel routes remain in place. [Dispatch and selection](../../src/fusion/advanced/levels.rs#L60) · [Frame completion](../../src/fusion/advanced/mod.rs#L160) · [Job checkpoints](../../src/job/stream.rs#L216)

The first experiment at `80da401` used one seven-tensor kernel and was kept isolated after review found an imported-WGPU limit it could exceed. The reported storage-buffer count did not include the separate bind-group index limit. The split candidate uses the existing maximum of five data bindings and needs no new capability rule. Because WGPU shader, Metal and native CUDA compilers may contract and round computations differently after the global f32 intermediate is removed, unchanged arithmetic source does not by itself establish physical parity.

## Test-first CPU witness

Base `b820da05d3982a7912cb7c7c9d8aa926ece14a9c` and test-only revision `08668346bbdb2132f7ef234e6f83cdd6176de550` issued 50 launches for two actual four-reduction Hybrid frames, exceeding the 42-launch bound. The exact candidate passed the bound and all 22 focused CPU tests. The coverage includes independent 0.3/0.7 expected amplitudes for equal positive weights, exact zero-weight ties, zero and multiple reductions, odd tails, narrow grids, existing sharpness and precision checks, and cancellation preserving an existing export. Scoped Clippy compiled both advanced test entrypoints. Reviewed Miri source inventory and formatting passed. [Red](cpu-red.txt) · [Green](cpu-green.txt) · [Clippy](clippy.txt)

The out-of-tree driver separately linked against both locked libraries. It generated deterministic chromatic RGB, complementary equal-contrast patterns and different flat colors for 18 cases across six shapes and depths 0, 1, 4 and 8. The output streams matched all 235,962 f32 channels, 943,848 bytes per output. Both SHA-256 digests are `19d204268113dcb8178898d06aa523f6a9fae38233b180539a74bec252e38422`. The old and new driver binary digests are `0d19fe0f530caf98e8df026abbd688c24ad37538f9583191b41f2a16109e289f` and `095da79a8bf8e77b59819e83ee0c1e03cd1bb9139c8ca4f56aa49e67adb8c2a7`. [CPU differential driver](compare-f32.rs.txt)

These runs used Linux 6.8.0-147-generic x86-64, Ryzen 9 7950X3D, Rust/Cargo 1.100.0, CPUs 12–13 and crate lock SHA-256 `f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`.

```bash
export CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0
unset RUSTC_WRAPPER
taskset -c 12,13 cargo +1.100.0 test --offline --locked \
  --test cpu_advanced_fusion --test cpu_job --test cpu_stack_plan
CLIPPY_CONF_DIR="$PWD/target/dependency-policy/clippy" taskset -c 12,13 \
  cargo +1.100.0 clippy --offline --locked --lib --test cpu_advanced_fusion \
  --test gpu_advanced_fusion --test cpu_job --test cpu_stack_plan -- -D warnings
python3 scripts/miri_host_policy.py . validate
```

For the differential, build each lock and source revision separately and link the retained driver with `rustc +1.100.0 --edition=2024`, `-L dependency=DIR` and explicit `--extern pancake=LIB --extern cubecl=LIB`. With Cargo’s build-directory layout, populate `DIR` with links to the build’s `target/debug/build/*/*/out/` rlibs and proc macros. Run each executable with its output path and compare the two files using `cmp`.

## Exact physical Vulkan and P4 closure

The locked `903836ca831ba1e92b7d4f006836320dd8cbe402` release CLI has SHA-256 `c4cf0e5f9ed65e4fd3b91835b27b28d1ff12e518d9dee57fb70f3cb3ed0fc6f6`. It was built using `taskset -c 12,13 cargo +1.100.0 build --offline --locked --release -p pancake-cli` with two Cargo jobs, incremental compilation off and no compiler wrapper. The ELF build ID is `d9527bde1bfac3c8645b623bcf5336704ae0a8e8`. The dependency lock digest is the same as the focused CPU run.

On the physical NVIDIA RTX 3090 at PCI `0000:01:00.0`, driver `580.178.04`, the same 18 raw f32 cases for clean stock `b820da05` and candidate `903836c` each finished on explicitly selected Vulkan. All 235,962 channels matched bit for bit. Both output digests were `697aec036d9827b6c2bd46d8330f06950db2026574009e9042420b7e0530b212`. The shared GPU contract also passed. [Physical differential driver](compare-native-f32.rs.txt)

The exact frozen P4 replay ran from 20:05:30 to 20:06:11 SGT on 2026-11-18. All 69 mapped cases passed with zero failures or unsupported cases, and the candidate ELF rehashed unchanged before and after execution. Target and suite provenance both identify clean `903836c`. The physical HDR case completed with `wgpu-vulkan`, `physical_gpu: true` and no fallback on the same RTX 3090. The run supplies functional evidence. [Verification receipt](physical-and-p4-receipt.json) · [Replay command](run-p4.sh.txt) · [Exact case IDs](p4-case-ids.txt)

The verified read-only ELF, complete raw archive and separate checksums are retained under `artifacts/pancake-performance/binaries/hybrid-band-903836c/` in the repository's artifact store. Archive SHA-256 is `e4f163c873cc9e5ef7f21284b5080d818a34390b696b13a50d32c02d14fa149f`.

## Prepared R50 comparison

The common control is the preserved exact `07816a2` owned-registration-upload release. Its production paths and lock are byte-identical to `b820da05`. Compare it separately with the exact Hybrid ELF above and the exact `f034185` luma lattice ELF. All three use the same lock. The Hybrid executable delta is `pancake/src/fusion/advanced/levels.rs`. The luma delta is limited to the registration estimator and kernels, including their tests. The comparison uses the same 50 authenticated Canon CR3s, first-anchor similarity, kernel 6, eight reductions, scale 6, no slabs, auto crop and RGB16 TIFF. [Frozen R50 profile](../performance-targets.json) · [Historical one-copy diagnostic](../p10-r50-phase-287828a/owned-upload/README.md)

The corpus owner can copy `r50-three-arm.py.txt` to its task scratch as `r50-three-arm.py` and extract `diagnose.py` from the pinned ancestor before taking the agreed CPU quiet slot. The existing measured-process helper records public frame progress, exit status, elapsed time and direct-child high-water RSS. All three arms run in fixed order with per-arm fresh application caches and common Linux affinity 0–14. SHA-256 validation uses the immutable manifest before and after the three runs. Output decoding checks expected 5086×3390 genuine RGB16, exact prior pixel hash, and the bit digests of all 50 alignment and 50 sequential matrices in input order. Every arm must report actual CPU completion without fallback. Output verification follows the timed launches. Command environment expects the frozen Python environment and an explicit quiet lease receipt.

```bash
repo=/home/krishna/Documents/focus-stacking
git -C "$repo" show 8694b55:pancake/docs/p10-r50-phase-287828a/diagnose.py.txt > "$scratch/diagnose.py"
export PYTHONPATH="$repo/qualification/p10-performance:$repo/pancake-conformance/src"
prlimit --as=34359738368 -- taskset -c 0-14 "$frozen_python" "$scratch/r50-three-arm.py" \
  --inputs "$authenticated_originals" --output "$new_report_directory" --lease "$quiet_receipt" \
  --baseline "$repo/artifacts/pancake-performance/binaries/registration-owned-07816a2/pancake-cli" \
  --hybrid "$repo/artifacts/pancake-performance/binaries/hybrid-band-903836c/pancake-cli" \
  --luma "$verified_luma_elf"
```

The prepared recipe was checked statically. No originals were acquired and no R50 run or CUDA run was made in this task. A single observation per arm is a component diagnostic outside the frozen warm and memory gates. [Three-arm recipe](r50-three-arm.py.txt)
