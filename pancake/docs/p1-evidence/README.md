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

## First locked release executable

On 2026-11-18, candidate `4b2f9f745f7a9cfe8da6adcb17a18f39c6f3d9cc`
built under Rust 1.100.0 with `cargo build --release --locked --package
pancake-cli --bin pancake-cli` from `pancake/`. The unchanged conformance
entry point ran `cli.help` plus every other P1 parser and path ID with
`DISPLAY`, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS` and
`XDG_SESSION_TYPE` unset. It passed all 20 selected IDs, with no failures or
unsupported results. Each failing CLI invocation reported the offending flag,
value or input count. The five image decoder cases were outside this run.

- [Complete selected-case report](cli-parser-release.json.gz)
- [Raw suite provenance](cli-parser-release-provenance.json)
- [Checked rejection diagnostics](cli-parser-diagnostics.txt)
- [Release help output](cli-parser-help.txt)
- [Executable, Cargo.lock and ELF linkage](cli-parser-linkage.txt)

`python3 -m unittest scripts/test_headless_dependencies.py` passed on the same
revision. It checked the normal and build dependency edges of both the CLI
and core for all Cargo target platforms and features. The compute graph
contains the low-level `wayland-sys` loader through wgpu. The release ELF
needs libc, libgcc_s, libstdc++ and libm. Its loader trace for `--help`
shows no X11, Wayland, GTK, EGL, GLX or Vulkan library loaded.

## Reviewed CLI and core replay

Candidate `98e945f27874c2c8b162ca124d33df23b0fb71a0` passed the same
20 selected IDs from a clean worktree using the same locked release build and
display-free invocation. All rejection diagnostics matched the expected flag,
value or input count. Executable SHA-256
`38fcf360bf6818583849f1268531b880c5c564a17ab42e6417689dd79da5327b`.
The CLI/core dependency graph test and
`python3 scripts/miri_host_policy.py . validate` passed. The latter validates
the pinned source inventory and tool policy. Canonical macOS Miri execution
remains pending.

Replay this stage from the workspace root after building the release binary.
Choose a fresh output directory for each run.

```sh
adapter=pancake-conformance/src/pancake_conformance/adapters/pancake
case_args=()
while IFS= read -r case_id; do
    case_args+=(--case "$case_id")
done < <(jq -r '.cases[] | select(.primary_milestone == "P1" and
    (.id | startswith("cli.coverage.reject.") | not)) | .id' "$adapter/case-roadmap.json")
env -u DISPLAY -u WAYLAND_DISPLAY -u DBUS_SESSION_BUS_ADDRESS -u XDG_SESSION_TYPE \
  uv run --project pancake-conformance --frozen pancake-conformance run \
  --target "$adapter/pancake.toml" "${case_args[@]}" --no-coverage \
  --output artifacts/pancake-conformance/p1-reviewed
```

[Complete selected-case report](cli-reviewed.json.gz),
[raw suite provenance](cli-reviewed-provenance.json) and
[executable, lock and linkage](cli-reviewed-linkage.txt).
