# Shared frozen T50 stage for the 8694b55 release

The materializer used a clean checkout of
`8694b555666a1ddf4051e2839bbced4bcc625859`. Its generator and scalar oracle
match the prior qualified T50 materializer. The frozen receipt and
performance targets retain their original hashes.

All 50 ordered 6000×4000 RGB16 focus TIFFs and the two independent truth TIFFs
were generated. All 52 encoded file hashes and both independent decoded hash
sets matched the freeze, totaling 2,775,174,405 bytes. The materialization
receipt has SHA-256
`317f4b0c9be5837cd7082227bf700ee232e7e995471ee44be8488cbf3511603c`.
The two truth files remain separate from benchmark source arguments.

The generator finished between 20:22:52 and 20:26:37 SGT on 2026-11-18.
It ran on CPU14, nice +12, idle I/O priority, one decode worker and numeric
thread limits of one. Runtime was 224.730 seconds, peak RSS was 83,692 KiB,
and generator reserve was 15 GiB. Available disk space was 120,291,086,336 B
before, and 127,636,058,112 B after the generation window. Concurrent
ordinary work includes the authorized cleanup of R50 scratch. Available host
memory was 46,441,680 KiB at entry and 44,957,144 KiB at exit. The shared lock
covered the complete generation. No application or GPU benchmark ran here.

The [stage receipt](shared-stage.json) identifies the read-only corpus for
the packaged 400-event viewer and matched full-product diagnostic. Each
borrower verifies the same input manifest and releases its reads
before the owner authenticates cleanup. [Preflight](prepared-stage.json) ·
[Complete encoded and decoded records](materialization.json.gz) ·
[Exact command, resource logs and ownership](raw-stage.tar.gz)
