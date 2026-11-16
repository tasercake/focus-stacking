# ChimpStackr reference adapter

This adapter tests the pinned `submodules/ChimpStackr` source through portable
conformance cases and optional Python source coverage. Behavior contract v2 corrects the pinned source and updates its submodule pin. ChimpStackr module names, Qt hooks, dependencies, and
coverage exclusions belong here, outside the core suite contract.

## Setup and run

`--gui-vm` [bootstraps a dedicated guest automatically](docs/gui-vm-bootstrap.md).
The default managed guest is `pancake-conformance`; custom guest names remain
configurable in the descriptor.

From the `pancake-conformance` project directory:

```sh
git -C .. submodule update --init submodules/ChimpStackr
uv sync --locked --project src/pancake_conformance/adapters/chimpstackr_reference
uv run --locked --project src/pancake_conformance/adapters/chimpstackr_reference \
  pancake-conformance run \
  --target src/pancake_conformance/adapters/chimpstackr_reference/chimpstackr.toml \
  --gui-vm --gui-vm-persist
```

The isolated runtime installs ChimpStackr, the suite, and the pinned official Qt
snapshot. It has its own lock. The target descriptor declares runtime project,
source coverage directory, coverage scope, observations, isolated preferences,
service endpoints, and VM settings. CLI, algorithms, and physical-device cases
run on the host. Native interface cases require the configured macOS guest.

## Check the adapter

```sh
uv run --locked --project src/pancake_conformance/adapters/chimpstackr_reference \
  pytest tests src/pancake_conformance/adapters/tests
```

Native smoke tests require an explicit target. Add
`--target src/pancake_conformance/adapters/chimpstackr_reference/chimpstackr.toml
--gui-vm --gui-vm-persist` to pytest after provisioning the guest. Adapter-only
checks run without a GUI.

Current [adapter-isolation verification](docs/adapter-boundary.md) records checks
for this layout, including their limits.

## Hook boundary

`../chimpstackr.py` translates the generic environment hook and records actual
Qt runtime versions. `../chimpstackr_ui.py` starts the original entry point,
isolates QSettings, adds native accessibility metadata, exposes read-only viewer
state, and attaches tracing at native worker entry points. Original callbacks,
arguments, results, and exceptions remain intact. `../chimpstackr_probe.py` and
`../chimpstackr_services.py` implement the portable component wire protocol by
calling original service code.

`chimpstackr-coverage-v2.json` uses the full raw source denominator with no exclusions.
The historical `chimpstackr-coverage.json` retains the old reviewed scope.
Raw reports keep all source files and missing branches. The goal is high source
coverage through this adapter, separate from the portable contract for new
implementations.

[Historical evidence](docs/verification.md), [scope audit](docs/coverage-scope-audit.md),
[coverage goals](docs/goal.md), and other records in `docs/` predate adapter
isolation. Their commands and paths describe those historical runs. Use the
commands above for the current layout; no new full native replay is implied.

See [contract v2](docs/contract-v2.md) for source paths, contract migration and validation.
