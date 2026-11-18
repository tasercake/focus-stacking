# Frozen P10 evidence inventory

The [frozen target manifest](../../../pancake/docs/performance-targets.json)
defines 13 workload/method combinations, each measured with explicit CPU or
GPU selection. That gives 26 logical profiles. Vulkan and CUDA are separately
attributed NVIDIA implementations of the same GPU profile IDs. The frozen
comparison permits native CUDA against reference OpenCL on the same card.
The inspected target SHA-256 is `58bb68533311c48696a3a844d80eef2f37a3c1f39649305948c838b7002663dc`.

**One of 26 logical profiles has met every completed-job gate.** The
corrected-reference E9 CPU campaign at exact `c1e2cac` passed its numeric
and independent representative-image quality gates. Its 34 primary jobs
and two backend diagnostics add to five historical full-count schedules
at `12f2151` with 170 primary jobs and ten backend diagnostics. Three of
the historical schedules used an ineligible E9 reference combiner. The
corrected native CUDA/OpenCL E9 campaign adds 34 primary jobs and two
backend diagnostics. It missed the warm target and device cadence.
Three CPU profiles and one GPU profile have eligible full schedules.
Ten CPU and twelve GPU profiles lack a full eligible schedule.
[Qualified E9 CPU campaign](integrated-e9-corrected-cpu-c1e2cac/README.md)

## Profile coverage

**Qualified** means the exact profile passed its numeric and representative
quality gates. **Full count** means two warmups, ten warm and five cold
completed jobs per application. It records schedule coverage and leaves
any numeric, telemetry or quality issue open. **Ineligible** identifies the
historical E9 reference algorithm mismatch. **Open schedule** indicates
the full matched schedule is absent.

| Workload | Frozen method ID | Explicit CPU | Explicit GPU |
|---|---|---|---|
| T50 | `laplacian` | Open schedule | Open schedule |
| T50 | `hybrid` | Open schedule | Open schedule |
| T50 | `weighted_average` | Open schedule | Open schedule |
| T50 | `depth_map` | Open schedule | Open schedule |
| R50 | `laplacian` | Open schedule | Open schedule |
| R50 | `hybrid` | Full count at `12f2151` | Open schedule |
| R50 | `weighted_average` | Open schedule | Open schedule |
| R50 | `depth_map` | Open schedule | Open schedule |
| D150 | `laplacian` | Open schedule | Open schedule |
| D150 | `hybrid` | Full count at `12f2151` | Open schedule |
| D150 | `weighted_average` | Open schedule | Open schedule |
| D150 | `depth_map` | Open schedule | Open schedule |
| E9 | `exposure_fusion` | Qualified at `c1e2cac` | Corrected CUDA/OpenCL full count at `c1e2cac`. Warm failed and device cadence remains open. |

The profile IDs are `<workload>.<method>.cpu` and
`<workload>.<method>.gpu`. The input receipts pin 50 native generated RGB16
TIFF frames for T50, 50 real Canon CR3 focus frames for R50, 150 real JPEG
focus frames for D150 and nine real bracketed-exposure PNGs for E9.
[R50 RAW manifest](../../../pancake-conformance/src/pancake_conformance/adapters/pancake/performance-raw-corpus.json) ·
[D150 and E9 manifest](../../../pancake-conformance/src/pancake_conformance/adapters/pancake/performance-corpus.json) ·
[Generated T50 source recipe](../../t50-generated/README.md)

## Retained completed-job results

Ratios are Pancake/reference. Warm and each memory ratio must be at most
0.50. Cold must be at most 1.00. The `12f2151` E9 entries retain numeric
observations from the ineligible legacy reference combiner. The
`c1e2cac` CPU profile used the corrected equal final batch mean.
[E9 recipe and comparator audit](e9-reference-eligibility.md)

| Profile and exact Linux implementation | Warm ratio | Cold ratio | Process-tree RSS | Attributable GPU memory | Output quality |
|---|---:|---:|---|---|---|
| [R50 Hybrid CPU, packaged `12f2151`](integrated-r50-12f2151/README.md) | 2.325331, fail | 2.037556, fail | Pending cadence | — | Geometry matched with corrected reference RAW ingest. Color and selected-region detail remain open. |
| [D150 Hybrid CPU, packaged `12f2151`](integrated-d150-12f2151/README.md) | 0.491020, pass | 0.447042, pass | Pending cadence | — | Crop, doubled edges and detail remain open. |
| [E9 exposure fusion CPU, packaged `12f2151`](integrated-e9-12f2151/README.md) | 0.46036 | 0.06282 | 0.31883 | — | Ineligible comparator. RGB16 and common dimensions verified. |
| [E9 exposure fusion Vulkan/OpenCL, packaged `12f2151`](integrated-e9-12f2151/README.md) | 0.70500 | 0.09522 | 0.71987 | Pending cadence | Ineligible comparator. |
| [E9 exposure fusion CUDA/OpenCL, native `12f2151`](integrated-e9-cuda-12f2151/README.md) | 0.56340 | 0.08442 | 0.42523 | Pending cadence | Ineligible comparator. |
| [E9 exposure fusion CPU, packaged `c1e2cac`](integrated-e9-corrected-cpu-c1e2cac/README.md) | 0.425874, pass | 0.057144, pass | 0.318864, pass | — | Independent review passed with residual exposure differences and 364 additional floor and 731 additional ceiling samples. |
| [E9 exposure fusion CUDA/OpenCL, native `c1e2cac`](integrated-e9-corrected-cuda-c1e2cac/README.md) | 0.521168, fail | 0.078821, pass | 0.426292, pass | Pending cadence | Same sampled representative detail with residual exposure and endpoint differences. |

The native CUDA E9 sampled lower bound was 295,698,432 B. Half the
cadence-valid historical reference peak of 320,864,256 B is 160,432,128 B. The strict
candidate peak and ratio remain unavailable. Earlier repeated E9 campaigns
and backend/phase experiments cover the same logical IDs and add no profile
coverage. The [R50 packaged pair and phase diagnosis](../../../pancake/docs/p10-r50-phase-287828a/README.md)
and the [earlier physical T50 pair](t50-12f2151-preflight/pair-001/README.md)
are single matched diagnostics. The later exact `8694b55` Vulkan T50 Hybrid
pair took 22.171825 s versus 26.301475 s for OpenCL (ratio 0.842988).
The reference aligned on CPU and warped and fused on the RTX 3090. The
complete RGB16 exports repeated each target's earlier hashes. Paired RSS
and GPU coverage remain pending. Single observations supply no warm or cold
median. [Sealed T50 Hybrid diagnostic](t50-hybrid-pair-8694b55/README.md)

## Native latency and matching release

The exact `8694b55` packaged viewer measured 200 idle and 200 loaded
events on the RTX 3090 with all 1,120 presented RGB patches validated.
Idle P95 passed at 23.811137 ms. Loaded P95 failed at 59.597912 ms
against 33 ms, with 33 of 200 events beyond the limit. Packaged
`287828a` had passed idle at 21.713 ms and missed under load at 33.818 ms.
The scoped `6489af6` candidate passed both at 20.793 and 23.827 ms.
[Exact `8694b55` viewer](../../../pancake/docs/p10-viewer-package-evidence/8694b55/README.md) ·
[Earlier packaged viewer](../../../pancake/docs/p10-viewer-package-evidence/287828a/README.md) ·
[Scoped viewer candidate](../../../pancake/docs/p10-viewer-command-evidence/README.md)

The exact `c1e2cac` stock package measured 52.322024 ms loaded P95 in
an ordered A/B test. The separate bounded-poll prototype measured
66.942485 ms. Both arms missed 33 ms and the prototype stayed outside
the product. [Stock and bounded-poll pair](../../../pancake/docs/p10-shared-poll-evidence/c1e2cac/README.md)

The packaged `d6359e1` lifecycle campaign passed all 120 acknowledgements.
The actual 64-path fixture and real D150 each contributed 30 pauses and
30 cancellations under load. Maximum pause and cancellation times were
150.773 ms and 151.283 ms against 250 ms. This audit found no later
same-release combined viewer and lifecycle pass.
[Exact lifecycle and settled-state evidence](native-lifecycle-d6359e1/README.md)

The sealed `c1e2cac` Linux package passed 341 host, 34 isolated GUI and one
physical RTX 3090 GUI case, all 376 case IDs. This is the product package
used by the corrected E9 CPU campaign. The native CUDA/HIP build and
scoped CUDA execution receipts are separate. The confirmed `c1e2cac`
ledger and the newer suite source retain distinct provenance.
[Linux package and exact ledger](../../../pancake/docs/p9-linux-package-evidence/c1e2cac/summary.json) ·
[Native Linux profiles](../../../pancake/docs/p9-linux-native-evidence/c1e2cac/README.md) ·
[Current implementation and assurance scope](../../../pancake/docs/implementation-plan.md#active-delivery-checkpoint)

## Holds and unavailable evidence

- **Engineering and scheduling.** Complete the missing full matched profiles
  with the approved inputs and consistent output quality. Resolve the
  measured R50 speed misses and D150/R50 quality gaps. E9 GPU needs a
  passing warm comparison and cadence-valid device memory observation
  with the corrected reference. Final release also needs matching full
  native latency, package, conformance and assurance evidence.
- **Host memory observation.** The full D150 and R50 CPU campaigns had
  process-tree sampling gaps above 20 ms. A dedicated collector core did
  not cure R50. Synthetic native procfs and private-namespace probes have
  narrower scope. An aggregate RSS result still needs complete timely
  process-tree observations or an equivalent verified high-water counter.
  [RSS cadence and containment evidence](resource-sampling/collector-cadence-followup.md) ·
  [Private procfs comparison](resource-sampling/rss-pid-namespace.md)
- **Device memory observation.** The installed NVIDIA process lists miss
  the 20 ms window on prior physical jobs. The local `ff9f5eb` overlap
  diagnostic found no complete Vulkan bypass and an inconclusive CUDA
  control. The recorded capability inquiry found accounting disabled.
  Per-PID maxima would require supported enabled mode and complete process
  ownership provenance. A trustworthy attributable source remains required.
  [NVIDIA per-call evidence](resource-sampling/collector-cadence-followup.md) ·
  [Accounting capability and lifetime requirements](resource-sampling/nvml-accounting.md)
- **Apple execution.** No final matching physical Apple CPU, wgpu Metal,
  native Metal, native GUI, or Apple footprint receipt is available here.
  These remain unverified along with exact Apple packaging. Retained builds
  are tracked separately. The historical `d6359e1` Windows build/link
  remains scoped to that revision. AMD/Intel GPU and Windows execution
  remain best effort. [Release matrix and Apple package prerequisites](../../../pancake/docs/p9-release-preparation.md#apple-and-retained-builds)

This inventory records existing evidence and leaves all frozen thresholds,
inputs and lane requirements unchanged.
