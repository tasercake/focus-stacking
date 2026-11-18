# E9 coefficient table registration qualification

This replay covers the exact shared-table candidate
`a919045e8004e138df9fcc05650d9e87e50e0e36` and the unchanged stock source
`75c3213a8e4c1d91298c4ba954102fd295eaa114`. The locked candidate release
CLI SHA-256 is
`95923ea36d753a348352b7eba91a1d14e08322617d16c5239f7b357eb6682671`.
The native build contains linked CubeCL CUDA, CubeCL wgpu and Vulkan HAL
symbols. The frozen target descriptor ran that exact CLI.

The roadmap maps 64 case IDs to P5. The host lane completed 63 with native
CPU events and no fallbacks. The hardware lane covers the one mapped
`algorithms.recovery.cascade.gpu` case and requires actual Vulkan execution.
The audit checks the complete frozen 90-file contract and both lanes.
The conformance environment uses the tracked lock offline and CPython 3.12.12.

The independent comparison links each source with the same CUDA-enabled
profile, lock and Rust 1.100.0. Both comparison test programs include the same
synthetic fixture and output logic derived from the prior native CPU probe.
They differ at the two private calls that receive the candidate table handle.
Each test exercises identity, signed-shift, and flat ambiguity at FFT sides
64 and 128. It verifies real window, FFT, and cross-phase dispatch
counts, estimates, scored affine hypotheses and all inverse-of-forward f32
surface channels. Comparison is within each named physical backend, on one
RTX 3090 at PCI `0000:01:00.0`. The published evidence retains backend
provenance, case outputs as hashes, and the raw f32 comparisons.

## Results

All 64 mapped P5 cases passed. The release CLI emitted 63 native CPU
completion events and one physical `wgpu-vulkan` completion at
`0000:01:00.0`. Each event had a null fallback reason. The runner captured
candidate `a919045` for both the target and the frozen suite with clean
status. It verified all 90 contract entries and the combined SHA-256
`2d17fb4f570dcfae47e355b63e18650c325c586f47620c565b568f4fdcce20b2`.
Both case lanes and both comparison builds used the same Cargo lock SHA-256
`f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`.
[P5 audit with per-lane provenance](p5-audit.json)

The four comparison runs used NVIDIA driver 580.178.04 and the same
physical RTX 3090. Stock and candidate shared the Vulkan fingerprint
`spirv_4318_8708` and the CUDA fingerprint `ptx_sm86`. Each backend matched
all 122,880 f32 channels across six inverse-of-forward surfaces, with
zero maximum absolute difference and identical scores and decisions.
Each fixture submitted two window, six FFT, and one cross-phase launch.
[Physical parity audit and per-fixture digests](physical-audit.json)

| Test executable | Source | SHA-256 |
| --- | --- | --- |
| Stock | `75c3213` | `31d25181cbefbe220c12b47d8198cc078cebe0b625d09928e8e3f90fab815a0c` |
| Coefficient table | `a919045` | `6efaf56c0add1a6fdd1652c4cdde25cf5c52cea6f7d747de4b42a9b16d3f0432` |

P5 and parity scope exercise native Linux CPU, Vulkan, and CUDA. The
separate four-pair real E9 timing remains a diagnostic. This replay adds
no performance samples or Apple hardware execution.
[Commands, inputs, provenance and raw outputs](raw-records.tar.gz)
[Archive checksum](raw-records.sha256)
