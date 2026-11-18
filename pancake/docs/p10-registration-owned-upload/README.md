# Registration upload staging and T50

The registration helper grows one aligned owned CubeCL byte buffer before
submitting it through `Client::create`. The source must still pass the
existing typed frame and byte-budget checks. The narrowed change retains the
contiguous f32 tensor, the same client, and the existing synchronization
boundaries. [Independent source and receipt review](../../../qualification/p10-performance/evidence/registration-owned-upload-review.md).

The locked headless release comparison ran the exact baseline
`287828aac07ffad2252785b73a52a59fc07b3409` and candidate
`07816a24a62f96bc3d3252e95fcfd2b4b5950269` on a physical NVIDIA RTX 3090,
driver `580.178.04`, PCI `0000:01:00.0`. Both builds used Rust 1.100.0
and Cargo.lock SHA-256
`f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`.

| Whole-job sample | Baseline | Owned buffer |
| --- | ---: | ---: |
| Wall through export and process exit | 50.533 s | 37.223 s |
| Reaped process user CPU | 26.793 s | 25.067 s |
| Reaped process system CPU | 24.133 s | 12.326 s |
| Process-tree peak RSS | 1,547,694,080 B | 969,015,296 B |
| Maximum RSS observation gap | 11.311 ms | 10.604 ms |
| Observed attributable VRAM | 2,518,323,200 B | 2,518,323,200 B |
| Maximum VRAM observation gap | 70.550 ms | 76.053 ms |

The elapsed ratio was 0.736616, a 26.34% reduction in this pair. The
stock release ran first and each arm used a fresh compute cache, 32
logical CPUs, and a 28 GiB no-swap scope. An unrelated build remained
stopped throughout both observations. The timer covered full process
creation through exit with Linux `wait4`. Individual device wait
durations remain unmeasured in these uninstrumented builds. The VRAM
observation cadence exceeded 20 ms, leaving the frozen VRAM peak open.
This was one same-application diagnostic pair. Frozen P10 speed and
quality comparison require matched ChimpStackr measurements.

Both jobs used the same 50 authenticated 6000 × 4000 RGB16 T50 sources and
frozen Hybrid settings. Both reported `wgpu-vulkan` on the RTX 3090 with zero
fallbacks, the same progress, and 50 exact identity transforms. The
3998 × 5998 RGB16 TIFFs matched the historical encoded digest
`6160722086e2153b4dd3d8e3810dd22e156669fcafaa15fc72a3e88968b39302`
and decoded-pixel digest
`f54746784bcc278da2df734e9f034053a3b54105ddb2a30046baf6dab07a80a3`.
All 52 shared files, including both truth images, rehashed after the pair.
Both temporary exports were removed.

## Native allocation and registration checks

The test probe passed a 6,000 × 4,000 interleaved f32 RGB frame through the
public registration warp. It read the lower-right 3 × 2 region and compared
all 18 samples by their f32 bit patterns. The original and candidate both
matched.

GDB recorded successful full-frame allocation calls and retained their
backtraces. Both builds made one caller allocation to initialize the
frame. The stock registration call made three separate 288,002,048-byte
mappings. Two were in CubeCL's `Client::create_from_slice`, and the third
was the aligned-copy allocation reached from that call. The candidate
made one such mapping in the aligned byte buffer's growth path. Every
counted registration allocation included `pancake::registration::kernels::warp`
in its backtrace. The initial strace output is retained, with stack
unwinding truncation. GDB supplied the complete registration attribution.

At `287828a` the requirement for one staging allocation failed. The same
test passed at `07816a2`, as did all 63 host P5 registration cases on the
exact locked CLI. The case traces record 63 native CPU completions with zero
fallbacks. The reviewed production-source inventory and Rust format check
passed.

## Registration and device case replay

A separate exact-source run passed all 72 P6 device cases and the last P5
physical cascade case. Together with the host replay this covers all 64 P5
and all 72 P6 IDs, with 136 distinct passes. The targeted device replay
matched the same `07816a2` source, frozen suite, and executable hash used by
the T50 candidate. It verified all 90 frozen contract files.

The device replay exercised 101 CLI calls. It observed 33 native CPU jobs
and 37 physical RTX 3090 Vulkan jobs, including the five Auto requests.
The 31 corrupt-input calls identified the offending source. Thirty
preserved the previous export bytes. The [device receipt](device-regression.json)
lists every selected case and its provenance. The [raw logs](device-regression-raw.tar.gz)
and [generated file hashes](device-file-manifest.json.gz) retain the run.

## Reproduce the scoped diagnostics

The exact locked build command, full-frame Linux allocation probe source,
GDB command and assertions, 63-case selection, and bounded GPU launch are
in the [raw archive](raw-records.tar.gz). The [receipt](receipt.json)
records both executable hashes and source revisions, call stacks, CPU
provenance, physical GPU and settings, resource traces, and archived
hashes. The independent review is preserved on this branch and in the
archive. The shared generator and its owner retain the data custody and
cleanup record.
