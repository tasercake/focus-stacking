# Exact combined 8694b55 T50 Hybrid diagnostic

One authorized pair ran the pinned ChimpStackr OpenCL reference first and the exact combined `8694b555666a1ddf4051e2839bbced4bcc625859` Debian CLI second. Both ran real Hybrid jobs on the same physical RTX 3090, PCI `0000:01:00.0`, driver `580.178.04`. The observed completed-job times were **26.301 s reference** and **22.172 s Pancake**, ratio **0.843**. This is one diagnostic pair outside the frozen timing schedule. [Verified summary](verified-summary.json)

The Debian SHA-256 was `7dbc969e1813bc62aa4df206bb77982e3f7705298f753e12b7a493ae89ce3784`; the rootlessly extracted CLI was `e5fa8d2cb31a55071c999a83e35b4c3d31d6c569717b7baca328c16ea7ed4b6f`. The reference used clean `ab7a92708269c01c6094729f6cdfaf1415677364` and the frozen offline environment. Its interpreter digest and 46 package entries matched the earlier diagnostic after normalizing editable checkout paths. OpenCL index 0 matched physical UUID `GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac`; Pancake reported explicit `wgpu-vulkan` on the same PCI address. Both ran the identical 50-source order and frozen Hybrid flags, including initial-frame similarity, kernel 6, eight levels, scale 6, no slabs, auto crop and RGB16 TIFF. The reference reported GPU fusion and warping with CPU alignment estimation after three `GPU alignment help failed (Singular matrix); using the CPU` warnings. There was no whole-job CPU fallback. [Previous alignment behavior](../t50-12f2151-preflight/pair-001/README.md#observed-pipeline-differences)

All 52 shared generated files, 2,775,174,405 bytes under sealed materialization SHA-256 `317f4b0c9be5837cd7082227bf700ee232e7e995471ee44be8488cbf3511603c`, were reauthenticated after truth reads. Independent TIFF decode confirmed genuine 5998×3998 RGB16, low-bit variation, 50 exact finite identity transforms, symmetric one-pixel crop and all 50 known focal-plane regions in each result. Both byte streams and decoded hash streams matched their corresponding prior `12f2151` outputs exactly. [Previous exact output identities](../t50-12f2151-preflight/pair-001/summary.json)

| Observation | ChimpStackr OpenCL | Pancake Vulkan |
| --- | ---: | ---: |
| Retained before deletion, TIFF bytes | 78,347,120 | 143,881,378 |
| Mean absolute error versus generated sharp truth, u16 | 979.595 | 843.328 |
| Vertical-second-difference variance ratio in 50 truth regions | 1.1663986–1.1664015 | 0.8667194–0.8918330 |
| Observed process-tree RSS peak, bytes | 6,701,006,848 | 987,627,520 |
| Max RSS observation gap | 26.475 ms | 9.677 ms |
| Observed attributable GPU memory peak, bytes | 4,315,938,816 | 2,518,323,200 |
| Max GPU observation gap | 27.563 ms | 78.153 ms |

Whole-output paired RGB16 MAE was 1792.133 codes, RMS 2207.626 and maximum 19611. Candidate truth MAE was lower and its measured local detail was attenuated. Equal quality remains unresolved. The independent raw-trace reduction reproduced both per-metric cadences and peaks. The reference RSS trace and both GPU traces exceeded the 20 ms cap, so neither paired memory ratio qualifies. The 34 scheduled timing jobs remain separate.

The outer diagnostic performed both unchanged frozen-runner sample calls before publishing an actual subprocess-terminal receipt and waiting at a task-local handoff. The handoff followed both child waits and timers and only delayed optional paired TIFF/truth reading and final original and binary rehashes. The archive includes the exact overlay diff, build and package evidence, raw stdout/stderr, events and gzip counters, phase receipt, argv and derived controlled execution settings. Ambient launch environment values are excluded. [Raw evidence](raw-sanitized-8694b55.tar.gz) · [Checksums](SHA256SUMS)

The two output TIFFs were rehashed and removed, totaling 222,228,498 bytes. The shared stage remains with its owner for the other reader. [Cleanup receipt](output-cleanup.json)
