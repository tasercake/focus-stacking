# Pancake

Pancake is an isolated project for a new focus-stacking application. Its first
component is a standalone, language- and framework-independent conformance suite.
The stacking application is not implemented yet.

The suite owns its Python package, CLI, synthetic fixtures, tests, target
descriptors, documentation, dependency lockfile, and runtime artifacts. It does
not depend on Bokehforge or downloaded datasets. The thin ChimpStackr reference
adapter uses the existing `../submodules/ChimpStackr` checkout; upstream source
and submodule pins remain unchanged.

## Run the suite

From the repository root:

```sh
uv sync --project pancake --frozen
uv run --project pancake --frozen pancake list
```

For the ChimpStackr reference:

```sh
git submodule update --init submodules/ChimpStackr
cd pancake
uv sync --frozen --extra chimpstackr
uv run --frozen --extra chimpstackr pancake run --gui-vm --gui-vm-persist
```

Configure the [dedicated macOS guest](docs/gui-vm-setup.md) before running native
interface tests. CLI, algorithm, and physical-device cases stay on the host.
Guest transport preserves the `pancake/` and `submodules/ChimpStackr/` sibling
layout without copying other projects or host environments.

From this directory, check the harness without native GUI workflows:

```sh
uv run --frozen --extra chimpstackr pytest \
  --deselect=tests/test_interface_cases.py::test_native_method_and_alignment_controls \
  --deselect=tests/test_interface_cases.py::test_native_export_round_trip
uv run --frozen ruff check src tests
```

For the complete harness, use `uv run --frozen --extra chimpstackr pytest
--gui-vm --gui-vm-persist`. A different target needs no ChimpStackr extra: supply
its descriptor with `pancake run --target targets/replacement.toml`.

See the [conformance guide](docs/conformance.md) for contracts, case selection,
reference capture, reports, and coverage. The [verification record](docs/verification.md)
describes the reference runs made before the project move; it is historical
evidence, not a new Pancake verification result.
