# Pancake

Pancake is the future focus-stacking application rewrite. The application source
is reserved in [pancake/](pancake/README.md). No implementation or build system
has been added.

The independent [pancake-conformance](../pancake-conformance/README.md) project
lives at the repository root. It owns the Python package, CLI, tests, fixtures,
target descriptors, documentation, lockfile, and runtime artifacts. A thin
adapter will connect the rewrite to that suite; the adapter is future work.

List conformance cases from the repository root:

```sh
uv run --project pancake-conformance --frozen pancake-conformance list
```
