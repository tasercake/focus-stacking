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
reference index and the matching candidate index. The observed device name
and NVIDIA UUID memory attribution must agree. The candidate backend receipt
uses `runtime` and `device` on the completed numerical job, as well as the
public `actual_backend` field. Reference execution uses OpenCL on that GPU.

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

Collect monotonic native dispatch and independently observed first-presented
correct frame timestamps in the isolated GUI lane. The endpoint needs native
presentation evidence tied to the changed frame, such as a captured presented
frame with a presentation timestamp and confirmed image and viewport state.
Capture all required viewer actions while idle and during real processing.
Keep the native input and presentation trace, target build, renderer,
workload and independent pixel/state evidence alongside the sample JSON.

For lifecycle measurements record native pause and cancel dispatch, worker
acknowledgement at a safe boundary, and settled state separately. Confirm that
the worker stops submitting new work at acknowledgement. Use the unchanged
64-frame lifecycle case and selected real jobs. Record the fixture/job
identity on the event trace. The reduction consumes these arrays.

- `viewer` entries with `condition` (`idle` or `loaded`), `action` (`source`,
  `result`, `pan`, `zoom`, or `comparison`), monotonic `dispatched_ns`, and
  monotonic `presented_ns`.
- `lifecycle` entries with `operation` (`pause` or `cancel`), monotonic
  `dispatched_ns`, `acknowledged_ns`, and `settled_ns`.

```sh
"$ref_python" "$runner" latency /path/to/verified-native-events.json
```

Qualification depends on the independently verified origin and endpoints of
the events. The reduction applies the frozen numerical gates.

## Preparation evidence

- Before implementation, `python -m unittest discover -s qualification/p10-performance -v`
  failed to import the absent protocol.
- Eight focused tests and Ruff passed using the frozen reference environment.
  The measurement test invokes a real local child process and verifies that
  the timed boundary reaches its output publication.
- The pinned ChimpStackr checkout at
  `ab7a92708269c01c6094729f6cdfaf1415677364` installed on Linux with
  `uv sync --frozen`. Its CLI help ran and locked PyOpenCL enumerated the RTX
  3090 on NVIDIA driver 580.178.04. NVML returned positive attributed bytes
  for running local GPU clients.
- A reference-only real E9 preflight used all nine original hash-matching PNGs,
  explicit CPU, kernel 6, levels 8, scale 6, first-reference Euclidean
  alignment, auto-crop and TIFF16. Exit 0 and completed CPU diagnostics
  accompanied a genuine 337 × 510 × 3 uint16 output. The TIFF SHA-256 was
  `babe55824c0b24200981aab0f1e13ee59590d94781a2d6017d0216d367b617cd`.
  Its decoded pixel SHA-256 was
  `529d4566b7bfe3fc0c742ae1ba90e4bd090592b89b7283a4d94f342f88aa8230`.
  The source hashes were reverified and the temporary output was removed.

The matched candidate benchmark, native latency collection, and P10
qualification remain pending.
