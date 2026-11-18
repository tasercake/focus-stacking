# P4 application conformance evidence

All 69 case IDs assigned to P4 by the version-2 adapter roadmap were selected
individually from the 376-case frozen catalog. The unchanged runner exercised
the real locked release CLI through the adapter. No executable override or
coverage instrumentation was used. Generated case input names and hashes,
argv, subprocess diagnostics and completion events are retained.

| Source | Release executable SHA-256 | Selected / passed / failed / unsupported |
| --- | --- | --- |
| `18c17b6f1dd2ff2a15ccea985fe430ac1eb7a666` | `8c96ad652487f8628e53b44dfa014ff65b3da84da3acfa98ab0e56d26d09201a` | 69 / 69 / 0 / 0 |

The initial candidate was built with
`cargo +1.100.0 build --release --locked -p pancake-cli`. Its executable
was verified before and after the run against the supplied digest. The target
and suite were on the same clean commit throughout. Execution used Linux
x86-64 6.8.0-147-generic, AMD Ryzen 9 7950X3D, and a physical NVIDIA GeForce
RTX 3090 at PCI `0000:01:00.0` with driver 580.178.04. Display variables
and any backend override were unset. The nine-frame GPU exposure completion
event reports `wgpu-vulkan`, `physical_gpu: true`, and no fallback.

The [raw archive](p4-conformance-evidence/18c17b6.tar.gz) contains the complete
JSON and JUnit reports, runner provenance, exact selection and command,
per-case and per-process receipts, and output SHA-256 index. Archive SHA-256
`db9523d403ac2cd224af30f6301da6627c7cb7f244a8df919e7c148e9579cab0`.

This first candidate preceded the one-pixel exposure batch regression fix and
device buffer preflight in `da04c99`. Its 69-case result belongs only to its
own exact revision. Integrated-snapshot regression, application-wide assurance,
the remaining required lanes and native-scale performance remain separate.
