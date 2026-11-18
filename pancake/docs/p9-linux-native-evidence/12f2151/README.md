# Integrated P9 Linux native release profiles

Both opt-in Linux x86-64 production CLI profiles compiled and linked at
clean revision `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` with Rust 1.100.0.
Cargo.lock SHA-256 was
`f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`.
Both graphs passed the repository dependency policy and offline
cargo-deny advisories, bans, and sources. The vendor-source guard passed
five checks.

| Production build | Defined native runtime symbols | Verified scope |
| --- | ---: | --- |
| `cubecl/cuda` | 281 | Release compile/link and four frozen cases on the same binary |
| `cubecl/hip` | 270 | Release compile/link and ELF inspection |

The build selects the core and CLI workspace packages together. On the
qualified machine, the archived scripts used a disposable target
directory, three compile jobs, and a registry-only build cache.
Run equivalent builds from the `pancake` directory with the locked graph.

```sh
CUDARC_CUDA_VERSION=12050 CARGO_TARGET_DIR=target/native-cuda \
  cargo build --locked --release -p pancake -p pancake-cli \
  --bin pancake-cli -j 3 --features cubecl/cuda
CARGO_TARGET_DIR=target/native-hip \
  cargo build --locked --release -p pancake -p pancake-cli \
  --bin pancake-cli -j 3 --features cubecl/hip
```

The frozen descriptor invoked the CUDA-linked binary with these results.

| Frozen case | Actual completion |
| --- | --- |
| `devices.cpu.weighted_average` | CPU on AMD Ryzen 9 7950X3D |
| `devices.cpu.exposure_fusion` | CPU on AMD Ryzen 9 7950X3D |
| `devices.gpu.weighted.zero_regions` | Native CUDA on NVIDIA RTX 3090 |
| `devices.gpu.exposure_constant_mix.9` | Native CUDA on NVIDIA RTX 3090 |

All four cases passed and published a nonempty export. Both CUDA events
report physical GPU, PCI `0000:01:00.0`, and `ptx_sm86`. The driver was
`580.178.04` with CUDA 12.5.40 NVRTC. CPU cases explicitly selected
CPU, with the runtime override and CUDA library search path unset.
Every case recorded one completed stack and no fallback. The independent
audit verified both application and suite revisions and all 90 frozen
contract files.

The [receipt](receipt.json) pins both binaries and their ELF build IDs,
the actual execution hardware, program and suite provenance, and the
export checksums. The [raw archive](raw-text-records.tar.gz) contains
the build and link logs, graph checks, exact commands, fixture records,
stdout, stderr, and completion events. The
[run-file manifest](run-file-manifest.json.gz) hashes all original run
files. The [historical native profile replay](../79db6fc/README.md)
preserves the earlier verification separately.
