# Pancake completed-job performance campaign

The [frozen specification](../../pancake/docs/performance-targets.json)
defines the input sets, methods, settings, sample counts, and thresholds.
This runner measures the Linux x86-64 CPU and NVIDIA Vulkan/CUDA lanes against
the pinned ChimpStackr CLI. It verifies the selected input bytes against the
P0 manifest before and after each profile. It runs 17 jobs per target for each
profile, including two warmups, ten warm samples, and five cold samples.
Thirteen profiles yield 442 paired jobs on each lane. The two separately
instrumented backend checks per profile add 26 more jobs.

## Prepare and run a profile

Prepare the candidate from the complete, clean release source and verify the
real corpora before scheduling measurements. Unrelated workspace
edits do not affect source verification. The reference interpreter uses the
frozen adapter lock.

```sh
git submodule update --init submodules/ChimpStackr
ref_project=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
uv sync --frozen --project "$ref_project"
ref_python="$ref_project/.venv/bin/python"
runner=qualification/p10-performance/p10.py
"$ref_python" "$runner" matrix --runtime cpu
"$ref_python" "$runner" prepare-candidate \
  --receipt artifacts/pancake-performance/release-build.json
"$ref_python" "$runner" run \
  --runtime cpu --profile E9.exposure_fusion.cpu \
  --input-root /path/to/real-corpus-staging-root \
  --build-receipt artifacts/pancake-performance/release-build.json \
  --output artifacts/pancake-performance/e9-cpu-001 \
  --threads "$(nproc)" --timeout 1800
```

Use the actual release features in `prepare-candidate --features …` when
features differ from the Cargo defaults. For GPU, use `--runtime wgpu-vulkan`
or `--runtime cuda`, select the corresponding `.gpu` profile, and provide
`--gpu-uuid GPU-…`. On a host with multiple OpenCL devices, provide the pinned
reference index and the matching candidate index. Native CUDA uses index 0 after restricting
visibility to the selected UUID. The reference preflight obtains the physical
UUID of its actual OpenCL index and checks it against NVML. The candidate
completion event supplies `runtime`, `device`, and `device_pci_address` as well
as the public `actual_backend` field. Each GPU sample must show attributable
memory on the matched card and completion without a reported CPU fallback.

For T50 pass the directory containing the exact `focus_000.tif` through
`focus_049.tif` files. Real R50/D150/E9 paths resolve under the staging root
in the frozen manifests. Keep native source names and dimensions. Regenerate
or reacquire the original bytes using the [T50 recipe](../t50-generated/README.md)
and the [real-corpus provenance](../../pancake/docs/p0-performance-baseline.md).

The common affinity mask and worker limit apply to both targets. To constrain
both applications, run the entire command under the same `taskset` mask and
give `--threads` the number of allowed CPUs. Keep other audits, builds, and
GPU jobs idle while measuring. The common Git-directory lock serializes this
runner across worktrees. Independent applications require separate scheduling.
The report captures CPU frequency policy, available CPU temperatures, GPU
power and thermal state, and tool and driver identities.

## Read the receipts

Each sample launches the actual CLI from a fresh process. Monotonic elapsed
time covers process creation through wait for full process exit.
TIFF decoding, export validation, and pixel comparison occur after that timer.
Warm runs share scoped caches. Cold runs use separate empty cache
directories. Cache inventories expose how much the tools persisted.
Instrumentation runs separately after primary samples. Their wall durations
are excluded from the benchmark statistics.

Resource samples collect RSS across the child session and attribute NVIDIA
memory to its process IDs using both NVML compute and graphics lists.
These counters are sampled at a 10 ms nominal interval.
A gap above 20 ms or an unavailable metric leaves a memory gate pending.
Transient peaks can escape polling, and RSS can count a shared page in multiple
processes. The GPU measurement excludes unrelated clients. The maximum sampled
tree RSS and GPU residency are reported separately.
The macOS physical-footprint lane requires equivalent measurements on Apple
hardware.

The report retains every attempted job, flags, exit code, geometry, output
SHA-256, decoded pixel SHA-256, pairwise pixel metrics, and backend diagnostics.
Raw stdout, stderr and gzip resource traces remain beside it. Captured failures
end the profile with the original receipts intact. If an external condition
invalidates a run, preserve its directory and explain the condition before
starting another run.

The runner deletes its case-owned cache and intermediate images. Use
`--keep-review-images` to retain the first warm pair long enough to measure
representative real focus regions. Record the image hashes, corresponding
regions in both coordinate systems, and per-region measurements, then remove
the retained pair. Cropped shapes can differ and need an independently
registered region comparison before a quality decision. Keep the full,
matching conformance ledger alongside the timing result. Completed-job timing,
memory gates, and decoded TIFF checks leave quality and release status pending
until those independent checks finish.

## Native latency

`linux_latency.py` launches the installed release GUI and the unchanged native
AT-SPI driver on a private Xvfb and Openbox desktop. It initializes Xvfb’s
shared XWD framebuffer, sends native XTest pointer events, and observes the
actual visible screen pixels after each event. There is no per-event screenshot
command, app callback, or app-side time measurement. The first independently
observed correct patches give a conservative upper bound on virtual-screen
presentation time. The receipt records the largest observation gap.
Physical monitor refresh and scanout are outside this virtual-display receipt.

Prepare a GUI build receipt and an ordered scenario whose PNG witnesses were
checked independently against the real source and expected viewport geometry.
Use visible patches that distinguish the requested state, pan center, zoom,
selection, or comparison position. Keep patches clear of the native cursor.
The pre-action patches must be on screen and the post-action patches must
differ visibly at dispatch. The observer writes the actual matched patches
after the timer and records their hashes and maximum channel errors.

```sh
"$ref_python" "$runner" prepare-candidate --component gui \
  --receipt artifacts/pancake-performance/gui-release-build.json
"$ref_python" qualification/p10-performance/linux_latency.py \
  --scenario /path/to/reviewed-viewer-scenario.json --workload T50 \
  --input-root /path/to/materialized-T50 \
  --build-receipt artifacts/pancake-performance/gui-release-build.json \
  --output artifacts/pancake-performance/viewer-001
```

The native scenario uses schema 1 and an ordered `steps` array. This shape
illustrates a single source-selection step. The listed witness images and
coordinates must come from independent review of the actual scenario.

```json
{
  "schema_version": 1,
  "worker_status": {"control": "stack.status", "field": "title"},
  "steps": [
    {
      "kind": "viewer",
      "condition": "idle",
      "action": "source",
      "input": {"kind": "click", "at": {"control": "frame.1"}},
      "before": [{"point": [700, 450], "png": "witness/source-0.png"}],
      "after": [{"point": [700, 450], "png": "witness/source-1.png"}]
    }
  ]
}
```

- Pointer inputs support `click`, `scroll_up`, `scroll_down`, and `drag`. An
  anchor uses native `control` and optional interior `fraction`, or an absolute
  private-screen `point`. A drag has a required `to` anchor. Its terminal
  motion and release form the timed native input. Non-timed `setup` steps
  accept `inputs` and an optional lower-case `worker_phase` to wait for.
- Viewer cases use the exact generated 24 MP T50 source. Use `idle` and
  `loaded` conditions and `source`, `result`, `pan`, `zoom`, and `comparison`
  actions. Loaded cases require a worker-confirmed Running decode,
  registration or fusion stage around the pixel interval. Setup steps use real controls to start
  actual jobs and restore preconditions. Retain at least 200 samples per
  condition, including all required actions.
- `lifecycle` steps accept `operation` (`pause` or `cancel`) and `input`.
  The collector records actual Running before dispatch, worker-confirmed
  Paused or Cancelling, and reusable Idle after cancellation. A fleeting
  Cancelling transition may be observed through the retained native
  acknowledgement marker for the same worker generation. Idle by itself
  supplies no acknowledgement evidence. The timestamps bound external
  observation. Corroborate the observed state with the production
  worker’s safe-boundary and resource-drain semantics and the native
  [lifecycle case](../../pancake-conformance/src/pancake_conformance/cases/interface.py).
- Use `--workload lifecycle` for the unmodified 64-path fixture. It intentionally
  shares source bytes across distinct hardlinks. The other inputs require
  distinct frozen content. Also capture selected R50/D150/E9 cases and keep
  every observation from each trial. Target setup and stage selection happen
  through real native controls and the GUI launch inputs.

Reduce full captures on the same GUI build.

```sh
"$ref_python" "$runner" latency \
  artifacts/pancake-performance/viewer-001/native-latency.json \
  artifacts/pancake-performance/lifecycle-001/native-latency.json \
  artifacts/pancake-performance/real-lifecycle-001/native-latency.json
```

The reducer rejects mixed build/frozen-target provenance, incomplete captures,
and duplicate samples. It applies the frozen counts and thresholds. Keep the
native action trace, independent witness files, actual presented patches,
and input and build receipts together. Partial captures retain their original
observations and contribute no passing latency evidence.

## Preparation evidence

- Before implementation, `python -m unittest discover -s qualification/p10-performance -v`
  failed to import the absent protocol.
- Fifteen focused tests and Ruff passed using the frozen reference environment.
  The measurement test invokes a real local child process and verifies that
  the timed boundary reaches its output publication.
- The pinned ChimpStackr checkout at
  `ab7a92708269c01c6094729f6cdfaf1415677364` installed on Linux with
  `uv sync --frozen`. Its CLI help ran and locked PyOpenCL enumerated the RTX
  3090 on NVIDIA driver 580.178.04. NVML returned positive attributed bytes
  for running local GPU clients. ChimpStackr OpenCL index 0, Vulkan
  `vulkaninfo --summary` with the NVIDIA ICD, native CUDA UUID lookup, and
  NVML identify the same card, UUID `GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac`
  at PCI `0000:01:00.0`. These are out-of-timer identity probes.
- A reference-only real E9 preflight used all nine original hash-matching PNGs,
  explicit CPU, kernel 6, levels 8, scale 6, first-reference Euclidean
  alignment, auto-crop and TIFF16. Exit 0 and completed CPU diagnostics
  accompanied a genuine 337 × 510 × 3 uint16 output. The TIFF SHA-256 was
  `babe55824c0b24200981aab0f1e13ee59590d94781a2d6017d0216d367b617cd`.
  Its decoded pixel SHA-256 was
  `529d4566b7bfe3fc0c742ae1ba90e4bd090592b89b7283a4d94f342f88aa8230`.
  The source hashes were reverified and the temporary output was removed.
- A candidate-only E9 functional diagnostic used the same frozen profile and
  inputs on the AMD Ryzen 9 7950X3D. Exact application revision `18c17b6`
  completed on the CubeCL CPU runtime and exported genuine 339 × 512 RGB16.
  Reference diagnostics report a one-pixel crop on each edge. Registered
  overlap quality remains to be evaluated. No elapsed benchmark measurement
  was made. [Diagnostic receipt](evidence/e9-candidate-functional.json)
- A separate native observer smoke test used `smoke_x11.py` and a small
  Xlib window. It changed visible screen RGB on receipt of actual XTest
  input and the captured patch matched its independently known color with
  zero error. This fixture validates the acquisition path before measuring
  Pancake’s GUI.

The matched candidate benchmark, native latency collection, and P10
qualification remain pending.
