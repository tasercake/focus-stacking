# Pancake Linux device replay

On 2026-11-18, the unchanged contract-v2 device suite finished with **72 of 72
passed**, zero failures, and zero unsupported cases. The run used the staged
release executable at clean revision `cb5e3a4a35c2ce356c93fed0f784825a17787148`
and verified its SHA-256 before and after copying it to the descriptor's CLI
path. The [receipt](receipt.json) records the command, environment, Cargo and
uv locks, suite and descriptor, binary, hardware, and exact 72 IDs.

Every one of the 90 adopted frozen contract files matched. Across 100 CLI
invocations, 33 jobs completed on the Ryzen 9 7950X3D CPU and 36 completed via
wgpu Vulkan on the physical RTX 3090 at `0000:01:00.0` (driver `580.178.04`).
The GPU total includes all five Auto jobs. Each successful job recorded one
completion event and produced a validated export. The 31 corrupt-input jobs
identified the offending file and recorded no completion or fallback event.
All 30 cases with pre-existing exports preserved their original file hashes.

The [raw archive](raw-text-records.tar.gz) contains the suite report, JUnit
file, provenance, command arguments, fixture manifests, stdout, stderr, event
streams, and the independent receipt audit. The
[file manifest](run-file-manifest.json.gz) records all generated inputs and
exports by path, byte count, and SHA-256. Generated image files and the test
environment are disposable.

Native CUDA on this application revision, Apple execution, the other host
suites, isolated GUI, packaging, and performance require their own runs.
