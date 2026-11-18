# T50 TIFF row-worker diagnostic

Eligible DEFLATE RGB16 TIFFs of at least 1,048,576 pixels can decode in up to four row bands. The caller handles one band. A process-wide lease allows up to three extra scoped workers, with a smaller count when the host offers fewer CPUs or useful tile rows. Every lane reads from the original opened file using a separate logical cursor. Only seek and compressed input reads share a lock. Each decoder verifies its directory against the original band plan. Decoded tile scratch is bounded at 24 MiB per parallel import, in addition to the shared working raster.

The first matched Linux CPU diagnostic used candidate `3529ea4` and baseline `287828a` in the same optimized probe on four physical Ryzen 9 7950X3D cores. It authenticated the three generated T50 inputs before and after use and compared all 648 million candidate working samples bit for bit. Other processes ran on the host outside the selected cores.

| Decode-only metric | Serial | Row workers |
| --- | ---: | ---: |
| Median of nine authentic T50 frame decodes | 0.471289 s | 0.140305 s |
| Frame 024 peak process RSS | 285,440 KiB | 287,664 KiB |
| One-core frame 024 median of three decodes | 0.521138 s | 0.520237 s |

The four-core candidate reached 3.36× serial throughput. Linux observed three extra TIFF worker threads. There were zero extra threads on one core, and another 216 million candidate samples matched the baseline. The end-to-end T50 comparison and frozen P10 qualification are pending. [Receipt](receipt.json) · [Paired samples](alternating.tsv) · [One-core samples](one-core-parity.tsv) · [Live workers](threads-rows.json) · [Source archive](probe-source.tar.gz)

The test-first witness failed when the seek was omitted inside the shared input lock, returning the wrong tile bytes. The follow-up production revision `1a88701` retains this test on an in-memory cursor and exercises the real filesystem TIFF path in the native integration lane. The independently encoded 1025×1027 fixture preserves every normalized code, partial edge pixels and its ICC profile. A one-byte compressed length in the last tile row reports the source path and tile 288. The native fixture is little-endian contiguous RGB16 with 64×64 tiles, horizontal predictor and the row-major sample code sequence `index % 65536`. [Exact pure red log](cursor-pure-red.log.gz) · [Pure tests](miri-boundary-unit.log.gz) · [Native regressions](miri-boundary-integration.log.gz) · [Strict Clippy](clippy-miri-boundary.log.gz)

The source archive captures the exact two TIFF decoders and build lock used in the decode-only diagnostic. The reproduction script records the materialization receipt hash and selected affinity. [Probe commands](matched.sh.txt) · [Hardware and background processes](match-environment.txt) · [Input hashes](input-sha256.txt)
