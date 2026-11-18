# P1 command-line integration evidence

## Initial contract run

Status on 2026-11-18 at `34dd609dda395171284bf2704b4f6b10dfcea040`.
The unchanged `cli.help` case reached the mapped target command and failed
during launch because `./target/release/pancake-cli` was absent. Suite exit 1,
one completed case, zero passes, one failure. The report records a 1.362 ms case.

Run from the repository root with no candidate binary present.

```sh
uv run --project pancake-conformance --frozen pancake-conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --case cli.help --no-coverage \
  --output artifacts/pancake-conformance/p1-red/report
```

[Raw report](cli-help-initial.json) and [provenance](cli-help-initial-provenance.json)
retain the original launch error, worktree, case ID, descriptor and frozen Python
lock. The starting Cargo.lock SHA-256 is
`7c7c64dcbf4255efec0705b472765dd001b733999b122f67c78f36f79349ba7b`.
The host is Ubuntu 24.04.5 LTS, Linux 6.8.0-147-generic x86-64, AMD Ryzen 9
7950X3D and NVIDIA GeForce RTX 3090 (driver 580.178.04). The suite ran with uv
0.6.4 and CPython 3.12.12. The launch failure preceded any CPU or GPU compute.

## Frozen contract check

`uv run --project pancake-conformance --frozen pancake-conformance list --json`
returned all 376 IDs. The audit matched the live catalog's order, descriptions
and required capabilities to the adopted snapshot and milestone roadmap.
All 90 tracked core contract files matched individually and as one digest.
[Catalog and file hashes](contract-audit.json).

`env -u DISPLAY -u WAYLAND_DISPLAY -u DBUS_SESSION_BUS_ADDRESS uv run --project
pancake-conformance --frozen pytest -q pancake-conformance/tests` ran 309
passing conformance self-tests. Two live GUI smoke tests require an explicit
target and native GUI lane. These counts describe the harness.
[Raw self-test output](conformance-self-tests.txt).

## P1 replay selection

Select every roadmap record with `primary_milestone == "P1"`. The selection
contains 20 help, argument and path IDs and five image preflight IDs. The image
cases require diagnostics from checking real malformed PNG, DNG and NumPy
inputs, an unsupported input format and oversize PNG headers. A diagnostic from
an unavailable pipeline would satisfy their generic rejection assertion, so
the P1 evidence must verify the offending inputs and actual error reasons.
The later successful glob and path-order cases exercise a completed stack.
