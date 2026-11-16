# Contract v2 validation — 2026-11-16

Application source: `ab7a927` in `submodules/ChimpStackr`.
All six behavior families are corrected. No Rust scaffold file was changed.
The existing independent adapter, portable UI/CLI and VM-bootstrap work was
preserved and integrated before final verification.

| Check | Passed | Skipped / unsupported |
| --- | ---: | --- |
| Application headless, CLI and physical GPU tests | 362 | 0 |
| Application GUI tests in macOS guest, Qt offscreen | 40 | 3 require OpenCL |
| Those three data-only GPU preview tests on physical host, without GUI | 3 | 0 |
| Suite and adapter self-tests | 324 | 2 explicit-target native smoke wrappers |
| Canonical reference conformance | 375 | 1 physical-GPU GUI case unsupported in VM |
| Additional original checker / nearby non-repeating controls on physical GPU | 8 | 0 |

The 405 distinct application checks passed. The three guest OpenCL skips were
covered by their data-only host tests; they did not create host windows. Native
conformance ran exclusively in a dedicated guest. The unsupported
`interface.compute.gpu` case is not a pass and has no golden output. All requested
CPU/GPU corruption, precision, identity, geometry and crop cases passed.

Reference GPU: Apple M4 Pro. The original 65×99 checker and nearby controls
passed all four methods on both CPU and GPU, with zero measured transform drift.
The original GPU-index normalization checks also passed before their retirement
from the portable catalog; application normalization code was unchanged.

The first complete host run passed 354 cases. Concurrent main changes replaced
some reference-specific policies with portable contracts. Final host replay
passed all 341 current cases. Native replay exposed inherited routing/readiness
defects; only failed or directly affected cases were replayed. Every final case
has an actual passing or unsupported verdict in the [machine-readable record](contract-v2-validation.json).
Earlier failed and interrupted reports remain retained as historical evidence;
they were not relabeled successful. The final native lifecycle case completed
real pause/resume/cancel and a clean restart on the original 64-image workload.

## Frozen reference

[Version-2 baseline](../baselines/contract-v2-2026-11-16/manifest.json):
375 passed case records, 346 decoded outputs, and one explicit unsupported case.
Capture occurred only after all independent oracles passed. Input hashes were
rechecked, including restored missing-source fixtures and GUI inputs. All
baseline entries were then read back and compared to their validated exports.
No image processing was repeated merely to capture references. Existing baseline
and historical evidence directories were not rewritten. The immutable manifest
SHA256 is `dacb538f5e141efb069f167dc9af0328a80b83a10c6f7922df2dce9ddf136ddc`.

The [complete v1/v2 case map](../../../../../docs/case-contract-v1-v2.csv) covers
316 old cases and 376 current cases. Eighteen reference delivery, cache or device
policy cases were retired by the independent feature-contract migration; this
correction does not change those application policies.

## Evidence and reproduction

Raw logs and reports are retained under repository `artifacts/contract-v2/`.
Key runs: `final-host`, `final-interface-custom-vm`, `interface-repair`,
`interface-repair-2`, `lifecycle-final`, `app-gui-vm`, and
`gpu-repeated-controls`. `baseline-audit.json` records the serialization audit;
`scaffold-preservation.json` contains SHA256s for all 34 scaffold files.
The original execution paths in provenance refer to the isolated worktree;
artifact paths are relative to the repository after delivery.

The default managed VM was in use by another run. Verification used the free
existing `chimpstackr-conformance` guest via the retained
`reference-vm-override.toml`, with the same application source and runtime lock.
No host keyboard, pointer, or GUI window was used. Host and guest execution,
source provenance, diagnostics and pixel comparisons remain separate evidence.

From repository root, with a free configured VM:

```sh
uv run --locked --project pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference \
  pancake-conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference/chimpstackr.toml \
  --suite cli --suite algorithms --suite devices --suite interface \
  --gui-vm --no-coverage \
  --baseline pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference/baselines/contract-v2-2026-11-16
```

## Limits

A macOS guest cannot certify physical-GPU GUI execution. A portable, repeatable
real GPU-runtime-failure fixture was unavailable; no corrupt frame or injected
failure is presented as GPU fallback evidence. Conservative identity fallback
can leave genuinely unidentifiable motion uncompensated. Synthetic fixtures and
this Darwin arm64 runtime do not certify every photograph, camera RAW format,
platform or interpreter version. Full source coverage was not recomputed; the
v2 coverage profile intentionally uses the full raw denominator with no inherited
line exclusions. One existing pytest fixture deprecation warning remains.
