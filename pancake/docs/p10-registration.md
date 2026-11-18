# Native-scale registration and crop checks

On 2026-11-18, the locked Pancake CLI `cb5e3a4` reproduced the original T50
failure using only the two exact frozen 6000×4000 RGB16 TIFFs
`focus_000.tif` and `focus_006.tif`. The first-reference similarity fit moved
the second by about 184.6 px horizontally and −186.3 px vertically on the
physical RTX 3090 Vulkan lane. Its 3620×5626 export lost 15.14% of the native
canvas. The T50 recipe changes focus region by region while keeping all source
coordinates static. The two TIFF byte hashes and exact command options are
in the replay receipts. [Original physical completion event](p10-registration-evidence/t50-pair-red.events.jsonl).

The bad translation largely followed a repeat in the reference itself. An
independent proxy calculation gave approximately 0.916 correlation for the
chosen cross-image fit and 0.921 for the same transform on the reference
alone. The acceptance check now requires a translation separated by at least
one scoring sample to beat that repeated-reference alternative by the same
minimum correlation advantage used against identity. The CubeCL moment
kernel and sampling grid are shared for both evaluations. Fine adjustments
below the sample spacing keep their existing confidence checks.

ChimpStackr source `ab7a92708269c01c6094729f6cdfaf1415677364` records aligned
crop in `src/algorithms/API.py::get_crop_bounds` by
rounding up the maximum displacement and adding one interpolation pixel to
each edge even for zero displacement. Its CLI applies that rule when alignment
and auto-crop are active. Pancake now keeps the same margin on a stationary
axis, keeps the full canvas when alignment is disabled, and retains the
completed canvas when a proposed crop cannot fit.
[Failing aligned-identity test before the change](p10-registration-evidence/identity-crop-red.log).

## Locked functional and regression evidence

The checked release used clean source `5e102447ad95c641eb773d9fdf94f2bc3757b81d`,
binary SHA-256 `3ac6abaecc1bbd5743efd2abc6879a43d4b17294514b7bc209a05227d613ccbb`
and Cargo lock SHA-256 `012cda6d161124eef8ecc3c5c6a4fed8db881e5f7606f4b9d7aee5f766f1a879`.
Rust 1.100.0 built it with `cargo build --locked --release -p pancake-cli`.
The Linux x86-64 host ran kernel 6.8.0-147-generic with AMD Ryzen 9 7950X3D CPU
and NVIDIA RTX 3090, driver 580.178.04 and PCI 0000:01:00.0. Display variables
were unset for native CLI execution.

| Check | Result | Evidence |
|---|---|---|
| Exact 2-frame T50 reproduction, Vulkan | Two exact identities, 3998×5998 RGB16 after the one-pixel margin | [Receipt](p10-registration-evidence/t50.receipt.json), [device event](p10-registration-evidence/t50.events.jsonl) |
| Nine frozen real E9 exposures, CPU | Nine exact identities, reference geometry of 337×510 RGB16 | [Receipt](p10-registration-evidence/e9-cpu.receipt.json), [event](p10-registration-evidence/e9-cpu.events.jsonl) |
| Nine frozen real E9 exposures, physical Vulkan | Nine exact identities, reference geometry of 337×510 RGB16 | [Receipt](p10-registration-evidence/e9-gpu.receipt.json), [device event](p10-registration-evidence/e9-gpu.events.jsonl) |
| P5 conformance on this exact release | All 64 passed, zero failed or unsupported. Both 4097×257 recovery cases retained the known 2 px motion | [Raw report](p10-registration-evidence/p5-report.json.gz), [JUnit](p10-registration-evidence/p5-junit.xml.gz), [provenance](p10-registration-evidence/p5-provenance.json), [commands and events](p10-registration-evidence/p5-processes.tar.gz) |

The separate focused `cargo test --locked --test cpu_job --test
cpu_registration_contract --test gpu_registration_contract` passed all six
tests. Locked Clippy for those three targets and the library passed using the
effective reviewed dependency policy. Runtime fingerprints and hashes refer to
the clean functional release. The functional receipts verify exact input
hashes before and after the jobs. Generated outputs were removed after decode
and hashing. Whole T50 and the frozen warm, cold, memory and equal-quality
protocol remain separate from these functional results.
[Evidence checksums](p10-registration-evidence/SHA256SUMS).

Replay the P5 selection from the repository root with the locked release
executable staged at `pancake/target/release/pancake-cli`:

```bash
case_arguments=()
while read -r case_id; do case_arguments+=(--case "$case_id"); done \
  < pancake/docs/p10-registration-evidence/p5-selection.txt
env -u DISPLAY -u WAYLAND_DISPLAY uv run --project pancake-conformance --frozen \
  pancake-conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --no-coverage --output artifacts/p10-registration/p5-replay "${case_arguments[@]}"
```

The integration based on local `bc3458a` retained its IO, runtime and worker
changes. The four revised production files were re-reviewed as OS-neutral
and the unchanged Cargo lock stayed in the source inventory. The platform
inventory guard, eight policy/classifier tests and workspace format check
passed. The integrated `cargo test --locked --lib --test cpu_job --test
cpu_registration_contract` passed 24 tests. The classifier retained
`cpu_job` and `cpu_registration_contract` for CPU assurance and
`gpu_registration_contract` for physical GPU assurance. The release
receipts above retain their original tested source revision.
