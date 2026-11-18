# P6 headless host assurance

Independent checks ran on clean source
`5f4bdbdd09e332b1bee068a9fdfacf88d3f05294` on 2026-11-18.
The candidate preserves Pancake application sources, lockfile, descriptor,
frozen suite and workflows from `cb5e3a4a35c2ce356c93fed0f784825a17787148`.
Its headless build lock SHA-256 is
`012cda6d161124eef8ecc3c5c6a4fed8db881e5f7606f4b9d7aee5f766f1a879`.
The reviewed inventory covers all owned production Rust and workspace
manifests. Canonical Miri remains on Darwin.

The [P1 receipt](../p1-assurance-evidence/README.md) identifies the unchanged
host and pinned tools. The workdir was `pancake/`. The native tests used
`VK_DRIVER_FILES=/usr/share/vulkan/icd.d/nvidia_icd.json`, scoped XDG cache
and runtime directories, and no desktop display variables. The hardware path
was the physical NVIDIA RTX 3090 with driver 580.178.04. Test inputs included
owned test-fixture files for numerics, registration, asynchronous jobs and
export. Linux Miri used the pinned nightly, strict provenance and symbolic
alignment checks and selected `--lib`.

| Command | Result |
|---|---|
| `bash scripts/check.sh fast` | Exit 1 at rustfmt's module sort. Earlier policy and 40 infrastructure tests passed. [Log](fast.log.gz) |
| `cargo nextest run --locked --workspace --all-targets --all-features --cargo-profile dev --profile ci --no-tests=pass --run-ignored all` | Exit 0. 68 tests passed without skips, including all eight physical-GPU integration tests. [Log](native-dev.log.gz) |
| `bash scripts/check.sh deps` | Exit 0. Dependency review, advisories, bans, sources and unused dependency checks passed. [Log](deps.log.gz) |
| `bash scripts/check.sh coverage-cpu` | Exit 1 with 3,179/3,947 lines, 300/453 functions and 3,221/4,296 regions. Instrumented tests passed. [Log](coverage-cpu.log.gz) [LLVM report](coverage-cpu.json.gz) |
| `CLIPPY_CONF_DIR="$PWD/target/dependency-policy/clippy" cargo clippy --locked --workspace --all-targets --all-features -- -D warnings` | Exit 101 on a documentation code span in the grayscale export integration test. [Log](clippy.log.gz) |
| `cargo doc --locked --workspace --all-features --no-deps --document-private-items` | Exit 101 on a binomial weights comment parsed as an intra-doc link. [Log](rustdoc.log.gz) |
| `MIRIFLAGS="-Zmiri-strict-provenance -Zmiri-symbolic-alignment-check" cargo +nightly-2026-11-15 miri test --locked --workspace --all-features --lib -- --include-ignored` | Exit 0. 15 pure-host tests passed under supplementary Linux Miri, including synchronization and allocation-bound contracts. [Log](linux-miri.log.gz) |

The stable coverage run has no branch instrumentation. The uncovered lines
are in CLI main (6), fusion (61), image I/O (183), job (269), registration (62)
and runtime (187). Shared configuration and P0 kernel summaries were full.
The later `a0e5c32` and `aea0a1d` commits repair the formatting and documentation
findings. This receipt retains those failures at the exact earlier source.
Full coverage, mutation, sanitizer and required platform checks remain
separate from the observed conformance results.
