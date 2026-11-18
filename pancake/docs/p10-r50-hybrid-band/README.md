# R50 Hybrid band accumulation prototype

Candidate `3d2782e8e30a66cef1b5248d62ff6f8042c30736` removes the transient Hybrid RGB band. The existing weighted CubeCL kernel already derives the coefficient from the fine and coarse Gaussian levels for Exposure. Hybrid now uses that input route, and a separate selection kernel derives the coefficient only when a pixel gets a new strict focus winner. Both passes fit the previous limit of five storage tensors. The CPU result matched the old path bit for bit. Physical parity and application performance remain pending.

## Observed cost and scope

The exact one-copy R50 CPU run reports 42.072283 s at `8694b555666a1ddf4051e2839bbced4bcc625859`. Its separate GDB repeat measured 17.808 s of RAW decode, 7.944 s of thumbnails and 14.219 s of Hybrid frame fusion at 13.88 mean busy cores. That trace does not resolve individual fusion kernels. [One-copy stage receipt](../p10-r50-phase-287828a/owned-upload/README.md)

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

## Prepared replay

Use the shared `gpu_advanced_fusion` contract and the same 18 old and new f32 cases on explicitly selected physical Vulkan, then native CUDA with `--features cubecl/cuda` and the approved native libraries. The prepared driver uses ordinary application runtime qualification and records the observed backend, hardware fingerprint, PCI address and adapter information. It fails if the requested physical backend did not run. Compare each backend to its own old driver output. [Physical differential driver](compare-native-f32.rs.txt)

Build the locked release CLI from the exact candidate, hash it, and use the unchanged frozen adapter and P4 case selection. The 69 case IDs in this receipt were independently matched in order against the retained P4 archive. Confirm 69 passing outcomes, actual physical Vulkan execution for `algorithms.coverage.hdr_multibatch.gpu`, and verified CLI and clean-source provenance after the replay. The P6 physical Hybrid stack, aligned stack, slabs and 16-bit cases are additional direct product checks of the changed route. [Replay command](run-p4.sh.txt) · [Exact P4 case IDs](p4-case-ids.txt) · [Historical P4 evidence](../p4-conformance-evidence.md)

No physical replay or new R50 timings have been collected on this candidate. A paired R50 follow-up needs the same authenticated 50 originals, retained flags and output/transform comparison before assessing the stage and whole-job memory.
