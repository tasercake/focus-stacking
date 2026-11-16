# Pancake-conformance

A standalone reference conformance suite for focus-stacking software. The suite
owns observable contracts, synthetic fixtures, independent image validators,
immutable baselines, and reports. Targets can use any language or UI framework.
No application is selected by default. The contract preserves features and
observable outcomes, with configurable CLI and semantic UI mappings. Backend
strategy, internal state, and application delivery mechanisms are not required.

Application integration belongs in [adapters](src/pancake_conformance/adapters/):
launch hooks, dependency projects and locks, target descriptors, source coverage
scopes, adapter tests, and implementation-specific verification records. The
core project has no application dependency. The future
[Pancake application](../pancake/README.md) is a separate project.

## Run

From this directory:

```sh
uv sync --locked
uv run --locked pancake-conformance list
uv run --locked pancake-conformance run --target /absolute/path/to/target.toml
```

Start with [targets/example.toml](targets/example.toml). Configure its source
root, commands, and argument mappings for your implementation. Adapter runtime
projects provide their own setup instructions. Core installation does not
install an application's libraries.

## Check the suite

```sh
uv run --locked pytest
uv run --locked ruff check src tests
```

Live native smoke tests require both `pytest --target PATH` and `--gui-vm`;
otherwise they skip. `--gui-vm` [bootstraps a missing dedicated guest](docs/gui-vm-bootstrap.md)
automatically on Apple Silicon macOS. Add `--gui-vm-persist` to keep it running.
Existing custom guests use the [manual setup guide](docs/gui-vm-setup.md). CLI, algorithm, and physical-device cases
stay on the host; interface cases run in the guest. Adapter tests live beneath
adapters and are selected explicitly with their runtime environment.

See [conformance](docs/conformance.md), [numerical contracts](docs/algorithm-contract.md),
[component protocol](docs/component-protocol.md), [UI protocol](docs/ui-protocol.md),
[diagnostics](docs/diagnostics.md), and [coverage](docs/coverage.md).
