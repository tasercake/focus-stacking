# Pancake

Pancake is a focus-stacking application project. All Pancake work lives here:

```text
pancake/
├── pancake-conformance/  # Standalone application conformance suite
└── pancake/              # Future focus-stacking application rewrite
```

[pancake-conformance](pancake-conformance/README.md) contains the existing harness,
including its Python package, CLI, tests, fixtures, target descriptors,
documentation, lockfile, and runtime artifacts. It is an independent uv project
and currently tests the ChimpStackr reference in `../submodules/ChimpStackr`.

[pancake](pancake/README.md) is reserved for the application rewrite. No application
implementation or build system has been added. The rewrite will use the
conformance harness through a thin adapter; that adapter is future work.

List conformance cases from the repository root:

```sh
uv run --project pancake/pancake-conformance --frozen pancake list
```

See the [suite README](pancake-conformance/README.md) for reference setup and tests.
