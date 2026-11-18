# Physical lifecycle latency on the d6359e1 Debian release

The exact packaged Pancake GUI passed all 120 frozen native pause and cancel
requests on the physical RTX 3090. Every acknowledgement met 250 ms. The two
workloads each supplied 30 pauses and 30 cancellations. Each timed request
started during observed numerical processing. [Exact verification](summary.json).

| Workload | Operation | Samples | P50 (ms) | P95 (ms) | Max (ms) |
|---|---|---:|---:|---:|---:|
| Original 64-path fixture | Pause | 30 | 139.580 | 141.270 | 141.325 |
| Original 64-path fixture | Cancel | 30 | 70.446 | 141.503 | 142.509 |
| Real D150 | Pause | 30 | 146.991 | 149.750 | 150.773 |
| Real D150 | Cancel | 30 | 147.253 | 149.915 | 151.283 |
| Combined | Pause | 60 | 143.568 | 149.033 | 150.773 |
| Combined | Cancel | 60 | 139.935 | 149.233 | 151.283 |

Every pause reached worker-confirmed Paused. Two fixture cancellations exposed
Cancelling before reusable Idle, which arrived at 139.871 ms and 139.039 ms.
The remaining 58 cancellations exposed acknowledgement and settled Idle
through the same generation's durable worker marker. The reducer preserves
acknowledgement and settled time separately. Both collectors exited 0.
The unchanged combined latency reducer exited 1 because the viewer
conditions had zero observations. Lifecycle operations and native lifecycle
workload coverage both passed. [Frozen reduction](frozen-reduction.json).

## Package and execution identity

- The unmodified GUI was extracted from the sealed Linux `.deb` at
  `d6359e129737f1a9077fb4abc2a8f783fa1f7b38`. The archive SHA-256 was
  `e6b4d83e8100d04d1692fc8d2f0e276e249fa5a1d79e6e8f623801632c860758`.
  The GUI SHA-256 was
  `eea214ed6c57477480b0f5897a12ae8b9c05a9595730dbfcedabfd15650f6f50`.
  The package and P9 physical receipts agreed on bytes, source, Cargo lock,
  and descriptor. The collector independently checked the exact executable
  against its owned checkout and release receipt. [Build receipt](build-receipt.json).
- The original lifecycle collector and reducer modules were restored from
  `024516fa5c42716ac6e061fa122375a2ebc6a6f3`. Their bytes match the historical
  receipt. The target hash, scenario steps, numerical phases, GPU UUID,
  and fixture implementation were identical. The scenarios rebound only the
  executable commit and SHA-256. Both ordered input lists matched the earlier
  capture, and the collectors verified unchanged source bytes at exit.
  [Historical campaign](../native-lifecycle-measured/README.md) and
  [replay plan and acquisition receipt](replay-plan.tar.gz).
- The serial quiet window was 2026-11-18 17:03:04–17:04:37 SGT on AMD Ryzen 9
  7950X3D and NVIDIA RTX 3090, driver 580.178.04, PCI `0000:01:00.0`, UUID
  `GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac`. Both private sessions used
  1440 × 1000 Xvfb and the automatic shared wgpu renderer. At visible launch,
  the GUI had 91,922,432 bytes of same-device GPU residency for the fixture and
  87,728,128 bytes for D150. Each final job completed on the matched Vulkan
  device. [Raw observations and host snapshots](raw-native-lifecycle.tar.gz).

The original downloaded D150 ZIP and all 150 selected source JPEGs were
rehash-verified before authenticated removal. Both private profiles, caches,
and the generated fixture were removed by the collector. The archive retains
all native input timestamps and acknowledgements, worker terminal events,
selected input receipts and shutdown evidence. [Cleanup](cleanup.json),
[launch command](run-lifecycle.sh.txt), and [receipt checksums](SHA256SUMS).
