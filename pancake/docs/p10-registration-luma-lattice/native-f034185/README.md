# Exact native Vulkan and P5 qualification

The exact candidate was
`f034185843cb20bfb61c31655f999e2f26e1c939`. The locked Rust 1.100.0
release CLI is SHA-256
`5cd03069846177a3f94fcd304f3d01d3d03ab007a99246dd6b10c1ccc5f205b5`.
The release GPU integration executable is SHA-256
`727c32e1ff4db38508037a022779dd714377ee8cd854bfbe8b856fb5fa2e5c6f`.
Both built on Linux with one job pinned to CPU 2.
[Exact hashes](lattice-release-sha256.txt)
[Source and tree](lattice-release-identity.txt)
[CLI build](lattice-release-build.log.gz)
[Integration binary build](lattice-release-gpu-suite.jsonl.gz)

An independent review confirmed the sampler source is byte-identical
to `7e29d6e`. The native thumbnail tests now run through public
`thumbnail()` and check bits with a read-only luminance accessor.
The library harness retains pure layout and budget checks. The Miri
inventory validator caught the missing reviewed paths before the
targeted hash refresh. After the update, the validator and all six
policy regressions passed. The complete supplemental Linux Miri run
on `nightly-2026-11-15` passed all 21 library tests with strict
provenance and symbolic alignment. The separate CPU native check
passed all 36 library, job and registration tests, with focused
strict Clippy on the CPU and GPU integration targets.
[Miri inventory red](miri-ledger-red.log.gz)
[Miri inventory validation](miri-ledger-green.log.gz)
[Policy tests](miri-policy-regression.log.gz)
[Actual supplemental Miri](supplemental-miri-full.log.gz)
[Native CPU cases](native-miri-split-final.log.gz)
[Focused lint](miri-split-clippy.log.gz) [Unit-test lint](miri-split-unit-clippy.log.gz)

## Physical completion

The RTX 3090 was the sole physical adapter visible through the
recorded NVIDIA Vulkan ICD. The release test registered its verified
device and completed the old and new paths on that same backend.
The test verifies the actual direct launch and the two lattice
launches along with complete bitwise f32 parity for the reduced
thumbnail, single-pixel axes and fractional custom sizes. It also
tests independent clamped color and known registration geometry.
[Driver and PCI identity](vulkan-p5-nvidia.txt)
[Vulkan adapter enumeration](vulkan-p5-vulkaninfo.txt)
[Native gate command](vulkan-p5-native.command)
[Completed native test](vulkan-p5-native.log.gz)

All 64 P5 case IDs passed through the release CLI, with no failed,
unsupported or unrun cases. The audit checked all 90 frozen contract
files and each case command and completion record. It found 63 native
CPU calls and one physical `wgpu-vulkan` call for
`algorithms.recovery.cascade.gpu`, on the RTX 3090 at PCI
`0000:01:00.0` with a null fallback reason. The physical work ended
20:06:56 SGT and the host lane ended 20:07:22 SGT on 2026-11-18.
This record covers registration behavior and same-backend Vulkan
parity. Full-workload performance and CUDA remain separate lanes.
[Audited case accounting and provenance](p5-audit.json)
[Exact commands, results and events](raw-p5-cases.tar.gz)
[Archive checksum](raw-p5-cases.sha256)
[Physical terminal](vulkan-p5-physical-terminal.txt)
[Host terminal](vulkan-p5-terminal.txt)

Reproduce with a clean `f034185` checkout and the frozen
`pancake-conformance` environment. Both release executables must
match the retained build receipt. Use the [lane script](run-vulkan-p5.sh.txt)
during an exclusive physical lease and retain the [case audit](audit-p5.py.txt).
The generated fixtures, exported images and private runtime directory
were removed after retaining paths and hashes.
[Generated file manifest](generated-file-manifest.json.gz) [Cleanup](cleanup.json)
