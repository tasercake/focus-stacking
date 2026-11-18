# Exact stock and typed RAW R50 CPU diagnostic

One serial stock/candidate pair ran on the Ryzen 9 7950X3D in a
dedicated CPU window on 2026-11-19 SGT. The common affinity selected
15 different physical cores at logical CPUs 0–14, with one core
outside the RAW worker pool. Both processes used fresh app caches and
the same pre-read input file cache, with a 32 GiB child address-space
cap. The runner measured spawn through actual exit including final TIFF
export and retained Linux `wait4` direct-child peak RSS. Both completed
50 ordered frame steps and genuine CPU execution with no fallback.
[Quiet window census](quiet-lease.txt.gz) [Exact command](command)
[Terminal status](full-after.txt) [Stock raw run](stock/process.json.gz)
[Candidate raw run](candidate/process.json.gz)

| Arm | Wall time | Direct-child RSS peak |
| --- | ---: | ---: |
| Stock `e81079d` | 35.642573 s | 2,236,637,184 B |
| Typed RAW `c80d59a` | 34.944663 s | 2,255,990,784 B |

The typed RAW arm took 0.697910 s less in this pair, a 1.96% reduction,
and used 19,353,600 B more direct-child peak RSS. The two executions
shared the frozen Hybrid CPU profile, with first-anchor similarity,
kernel 6, eight pyramid levels, alignment scale 6, no slabs, auto
crop and RGB16 TIFF. This one observation estimates the isolated
change on one host. The frozen warm/cold program, sampled
process-tree memory and independent specimen-quality judgment
remain separate. [Summary and boundaries](result.json)
[Complete raw report](report.json.gz)
[Immutable ELF receipts](../canon-positive/binaries.json)

The corpus was exactly 50 unmodified, filename-ordered, pinned Canon
CR3 originals. The existing two verified frames were moved into their
manifest positions without duplication. The other 48 original
objects contributed 424,416,224 B for 442,098,996 B total. All lengths
and hashes were verified both before and after this pair, and both
stock and candidate ELF digests remained unchanged. The capture and
CC BY 4.0 rights are bound to the frozen acquisition record.
[Full source and ordered input receipts](full-acquisition.json)

Both exports match byte for byte at 5086×3390 genuine RGB16. The
independently decoded sample digest
`9316387ed669f3e5cde04a009d2e7b12114ab3411e54448fee1447c07a689492`
matches the prior real R50 result. Every source-ordered alignment
and sequential 2×3 transform matches the earlier f32 bit digest
`510dcebedcee928da7a9bf16f8e23b046a2b1d4b8582ed4643c6b3e12554711b`.
Stock and candidate reproduce prior camera-corrected geometry. The
independent RawPy/LibRaw reference and outstanding color/detail
findings retain their existing interpretation.
[Stock completion and maps](stock/events.jsonl.gz)
[Candidate completion and maps](candidate/events.jsonl.gz)
[Independent reference review](../../p10-r50-integrated-quality/README.md)

The [extension script](extend-r50.py.txt) builds on the
[authenticated two-file stage](../canon-positive/README.md). The
[bound two-arm runner](full-r50-pair.py.txt) uses the
[existing process observer](../../p10-r50-component-comparison/diagnose.py.txt)
and the [archived f32 reducer](verify_three.py.txt) with the
[frozen Python environment](cpu-python-sync.log). In task-owned
scratch, copy the scripts without the trailing `.txt` suffix and
copy the process observer as `diagnose.py`. Replay requires the pinned
inputs, both exact ELF hashes and a host quiet window. All original
files and all four CPU/Vulkan output TIFFs were rehashed and removed
after preserving the independent verification receipts. Both verified
ELFs remain locally available. [Initial witness hold](retention.json)
[Final media cleanup](cleanup.json)
