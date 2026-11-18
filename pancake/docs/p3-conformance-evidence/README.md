# P3 release CLI conformance

Hardened release candidate `cb5e3a4a35c2ce356c93fed0f784825a17787148`
also passed all **27 P3 roadmap cases** in a clean headless checkout on
2026-11-18. The suite selected and completed exactly those 27 IDs on
Linux x86_64, with 31 completed CPU stack calls on the AMD Ryzen
9 7950X3D and zero failures, skips, unsupported cases, or unrun IDs.
The release binary and Rust dependency lock matched their recorded
SHA-256 values. This rerun covers the primary P3 cohort.
[Receipt](cb5e3a4/receipt.json) · [Raw report](cb5e3a4/report.json.gz) ·
[Provenance](cb5e3a4/provenance.json)

## Initial release candidate

On 2026-11-18, release candidate
`18c17b6f1dd2ff2a15ccea985fe430ac1eb7a666` completed all 27 primary P3
cases, 13 related P6 device cases, and the 25 previously passing P1
cases. Every report was complete with zero failures, skips, unsupported
cases, or unrun case IDs. [Raw run receipt](18c17b6/receipt.json)

| Selection | Selected | Passed | Completed stack calls |
|---|---:|---:|---|
| Weighted-average and depth-map P3 milestones | 27 | 27 | 31 CPU |
| Related weighted-average and depth-map P6 device cases | 13 | 13 | 10 CPU, 11 physical RTX 3090 Vulkan |
| Previously passing P1 CLI cases | 25 | 25 | Input validation and help |

The primary case IDs were selected from the unchanged case roadmap after
matching every ID, suite, and description against the live 376-case catalog.
The device run added weighted-average and depth-map execution, slab,
alignment, precision, and zero-weight cases. Each GPU completion reported
the physical RTX 3090 and PCI address `0000:01:00.0`. Both automatic
requests selected the same Vulkan device. The P1 regression selected
the 25 passing IDs from the retained P1 conformance report.
[Primary IDs](18c17b6/primary/case-ids.txt)
[Device IDs](18c17b6/devices/case-ids.txt)
[P1 IDs](18c17b6/p1-regression/case-ids.txt)

Host hardware was an AMD Ryzen 9 7950X3D and an NVIDIA RTX 3090
running driver 580.178.04 on Linux x86_64, kernel 6.8.0-147-generic.
The suite ran on Python 3.12.12 and used the checked-out frozen
contract-v2 source and Python dependency lock. The original release
binary was built by the job integration branch and copied into a clean
checkout of its exact revision after SHA-256 verification. The descriptor
and its defaults were unchanged. [Primary provenance](18c17b6/primary/provenance.json)
[Device provenance](18c17b6/devices/provenance.json)

Run each selection from a clean checkout of the tested revision with the
corresponding release binary in `pancake/target/release/pancake-cli`.
Set `receipt` to the selected case-ID file and `run_dir` to a new run
directory under `artifacts/`.

```bash
# From pancake/, prepare the actual release candidate.
cargo +1.100.0 build --release --locked -p pancake-cli

# From the repository root with the frozen conformance Python environment.
unset PANCAKE_RUNTIME DISPLAY WAYLAND_DISPLAY
export PYTHONPATH="$PWD/pancake-conformance/src" PYTHONNOUSERSITE=1
args=()
while IFS= read -r id; do args+=(--case "$id"); done < "$receipt"
"$VIRTUAL_ENV/bin/python" -m pancake_conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --no-coverage --output "$run_dir" "${args[@]}"
```

Each run directory below contains the raw report, JUnit XML, process exit
status, target/suite provenance and compressed per-call arguments, events
and fixture manifests. Reports retain oracle metrics and source-image
hashes. Generated image payloads and the copied release binary are
disposable.

This verifies the listed conformance behavior at the exact recorded
candidate. The final integrated revision requires fresh matching
provenance and its own full assurance and runtime matrix. The separate
[P3 kernel receipt](../p3-kernel-evidence/README.md) includes native
CUDA component execution. Product-level native CUDA and Apple execution
were outside these three runs.
