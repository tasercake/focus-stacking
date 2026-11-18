# Linux host integration evidence

The locked headless release at `cb5e3a4a35c2ce356c93fed0f784825a17787148`
completed all 341 host IDs with 0 failures and 0 unsupported cases. The 35
interface IDs are unrun for this revision. [Exact case accounting](cb5e3a4-accounting.json).

The accounting checked each complete raw report against its exact milestone
selection in `case-roadmap.json`, initially pinned in P0. All five reports
share the application revision, adapter and frozen suite digests. Each
case ID occurs once across the selected reports. The linked reports retain
native commands, verdicts and output checks. Linux CPU and physical NVIDIA
Vulkan results are distinguished in the source receipts.

## Release command and hardware

From `pancake/`, with Rust `1.100.0 (0ef1bc386 2026-11-09)` and the
repository release profile:

```sh
CARGO_BUILD_JOBS=4 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
  RUSTC_WRAPPER=/tmp/pancake-tools/bin/pancake-rust-cache \
  cargo +1.100.0 build --release --locked -p pancake-cli
```

The build succeeded in 46.88 seconds. CLI SHA-256
`818a2c3532141f5f96e75accc569121f064f2925bf31738956a94887a9f4cfc8`.
Cargo.lock SHA-256
`012cda6d161124eef8ecc3c5c6a4fed8db881e5f7606f4b9d7aee5f766f1a879`.
The conformance agents staged this binary in clean exact-revision worktrees
and ran the unmodified adapter with frozen Python dependencies and no coverage
instrumentation. The primary runtime host used Linux x86-64, kernel
`6.8.0-147-generic`, glibc 2.39 and an NVIDIA GeForce RTX 3090 at
`0000:01:00.0` with driver 580.178.04. Native CUDA qualification of
the runtime component is recorded separately. [Runtime receipts](../p6-runtime-evidence/README.md).

## Code and assurance checks

Scoped lifecycle tests first failed compilation because the control API was
absent. The pinned Clippy driver with the workspace lints subsequently ran six
lifecycle tests, including boundary acknowledgement, wake-on-cancel,
rejecting early publication and freezing completed progress. Separate native
job regressions ran real CPU decode, numerical kernels and export. They cover
sixteen-bit identity output, existing export retention on cancellation and
malformed sources, and worker reuse with distinct result generations.

| Check | Revision | Observed outcome |
|---|---|---|
| Locked Linux CPU scope, `cargo test --locked --workspace --lib` plus all integration targets selected by `scripts/assurance_targets.py … cpu` | `cb5e3a4` | 58 tests passed in this run. [Log](cb5e3a4-native-cpu.log.gz) |
| `bash scripts/check.sh fast` | `aea0a1d` | 40 checker tests, reviewed source inventory, formatting, whole-workspace Clippy and rustdoc pass. [Log](aea0a1d-fast.log.gz) |
| `bash scripts/check.sh deps` | `aea0a1d` | Policy and vendor checks plus advisory, ban, source and unused-dependency checks pass. [Log](aea0a1d-deps.log.gz) |

The tested Rust source delta between these checkpoints consists of declaration
ordering in `src/lib.rs` and a Rustdoc literal in the pyramid source. The
grayscale test documentation correction and updated Miri fingerprints are
tracked separately. The receipts keep the original release hash and revision.
The interface, canonical native Apple execution, exhaustive owned-source
assurance, retained platform builds and performance acceptance have their
own gates.
