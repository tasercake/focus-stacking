# Exact Linux functional scale preflight

On 2026-11-18, the release CLI at
`cb5e3a4a35c2ce356c93fed0f784825a17787148` processed one frozen Hybrid
profile for each scale workload below. The locked binary SHA-256 was
`818a2c3532141f5f96e75accc569121f064f2925bf31738956a94887a9f4cfc8`.
The Linux x86-64 host used an AMD Ryzen 9 7950X3D and physical RTX 3090.
The T50 process completed on Vulkan with the NVIDIA 580.178.04 ICD, PCI
`0000:01:00.0`. Every sample used the frozen input bytes and settings,
independently decoded TIFF16, and checked every input hash again.
The elapsed-time and resource-comparison campaign remains pending.

| Profile | Actual RGB16 output height × width | Registration and quality |
|---|---:|---|
| D150 Hybrid CPU | 1524 × 2126 | All 150 native JPEGs were consumed. All 150 transforms were finite, 62 identity, and max translation norm was 93.46 px. Representative registered comparison against the reference remains open. |
| R50 Hybrid CPU | 3392 × 5088 | All 50 Canon CR3 inputs were consumed. All transforms were identity. Pinned LibRaw visible geometry is 3412 × 5118, revealing a 20 × 30 extent difference. Canon crop and renderer parity remain open. |
| T50 Hybrid physical Vulkan | 3620 × 5626 | All 50 native generated TIFFs were consumed. One stationary frame produced a false 262.28 px translation norm. Output lost 15.14% of the correct 4000 × 6000 stationary canvas. Geometry blocks equal-quality comparison. |

The T50 exception was exactly `focus_006.tif`, with the following actual
reference-to-source matrix. Every other transform was identity.

```text
[ 0.99995726347   0.00029137847  184.614578247 ]
[-0.00029137847   0.99995726347 -186.298477173 ]
```

The independently decoded generated sharp truth and the candidate shared
46 sampled central depth-strip regions once mapped by the reported
symmetric crop assumption. Median absolute error was 832.96 of 65535.
Median vertical second-difference variance ratio was 0.869 and the
minimum was 0.0228. These descriptive values establish actual output
inspection. Matching per-method quality and complete release gates remain open.

The per-workload receipts retain exact commands, hashes, software versions,
physical/CPU identities, geometry and output statistics.

- D150 CPU [receipt](d150-cpu-receipt.json.gz), [app progress](d150-cpu-stdout.txt.gz),
  [diagnostics](d150-cpu-events.jsonl.gz).
- R50 CPU [receipt](r50-cpu-receipt.json.gz), [app progress](r50-cpu-stdout.txt.gz),
  [diagnostics](r50-cpu-events.jsonl.gz).
- T50 Vulkan [receipt](t50-vulkan-receipt.json.gz), [app progress](t50-vulkan-stdout.txt.gz),
  [diagnostics](t50-vulkan-events.jsonl.gz).

The [T50 materialization](t50-materialization.json.gz) reverified all
50 focus inputs and both independent truth images under the full-set
15 GiB reserve. The [ownership cleanup](t50-cleanup.json) removed all 52
TIFFs after the diagnostic. All three output TIFFs were also deleted.
The original real inputs remain in the task-owned corpus stage for the
future controlled campaign. The [functional command](scale-preflight.py.txt)
and [minimal two-frame reproducer](two-frame.py.txt) retain the acquisition
and independent checks.
