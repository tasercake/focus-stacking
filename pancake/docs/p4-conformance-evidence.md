# P4 application conformance evidence

All 69 case IDs assigned to P4 by the version-2 adapter roadmap were selected
individually from the 376-case frozen catalog. The unchanged runner exercised
the real locked release CLI through the adapter with coverage disabled.
Generated case input names and hashes,
argv, subprocess diagnostics and completion events are retained.

| Source | Release executable SHA-256 | Selected / passed / failed / unsupported |
| --- | --- | --- |
| `18c17b6f1dd2ff2a15ccea985fe430ac1eb7a666` | `8c96ad652487f8628e53b44dfa014ff65b3da84da3acfa98ab0e56d26d09201a` | 69 / 69 / 0 / 0 |
| `cb5e3a4a35c2ce356c93fed0f784825a17787148` | `818a2c3532141f5f96e75accc569121f064f2925bf31738956a94887a9f4cfc8` | 69 / 69 / 0 / 0 |

Both candidates were built with
`cargo +1.100.0 build --release --locked -p pancake-cli`. Each executable
was verified before and after its run against the supplied digest. The target
and suite stayed on the same clean commit for each run. Execution used Linux
x86-64 6.8.0-147-generic, AMD Ryzen 9 7950X3D, and a physical NVIDIA GeForce
RTX 3090 at PCI `0000:01:00.0` with driver 580.178.04. Display variables
and any backend override were unset. The nine-frame GPU exposure completion
event reports `wgpu-vulkan`, `physical_gpu: true`, and no fallback.

- [Raw report and execution receipts for `18c17b6`](p4-conformance-evidence/18c17b6.tar.gz)
  SHA-256 `db9523d403ac2cd224af30f6301da6627c7cb7f244a8df919e7c148e9579cab0`.
- [Raw report and execution receipts for `cb5e3a4`](p4-conformance-evidence/cb5e3a4.tar.gz)
  SHA-256 `1b64e5c7d87d565375ec33bc73040b01a6fe84a3b8ad13d5ae36a062764f1d69`.

The archives contain complete JSON and JUnit reports, runner provenance, exact
selection and commands, per-case and per-process diagnostics, and output digests.

A separate complete-job test generated nine distinct one-pixel RGB16 TIFFs.
The expected final image is the equal mean of four-, four-, and one-frame batch
means, rounded to one u16 code. The earlier CLI completed on CPU with maximum
error 6,337 codes. The hardened CLI returned the exact expected u16 samples on
both CPU and physical RTX 3090 Vulkan. Source hashes were preserved. The
supplemental result has no frozen catalog ID.

- [One-pixel exposure oracle](p4-conformance-evidence/tiny_exposure.py)
- [Initial CPU result](p4-conformance-evidence/18c17b6-tiny-exposure.json)
- [Hardened CPU and physical GPU results](p4-conformance-evidence/cb5e3a4-tiny-exposure.json)

The 69-case evidence applies to each documented release revision. Application-wide
assurance, final integrated revision, further hardware lanes, and native-scale
performance have their own verification.
