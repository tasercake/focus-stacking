# Optional source coverage

Conformance and source coverage are separate evidence. Portable scenarios do
not import application code. A target may declare a Python source directory:

```toml
[instrumentation]
source = "src"
```

The path is relative to the target root. Collection is enabled by default only
when this field is present. Use `--no-coverage` to disable it. Explicit
`--coverage` without a declared source fails. Native or other-language targets
need their own collector; Python coverage does not measure compiled kernels.

`CoverageSession` configures branch, multiprocessing, and thread collection.
Its child environment enables an opt-in startup hook before application imports.
Every Python file below the declared source stays in the raw denominator,
including files never imported. Suite configuration resets default exclusion
and partial-branch patterns. Target logic is never invoked merely to raise
coverage. Adapter-specific observation and native-worker hooks stay in adapters.

Each run writes `coverage/coverage.json`, `coverage.xml`, `html/index.html`,
`summary.json`, and the exact `coverage.ini`. Missing lines and branch exits
remain visible. No execution data is an error unless all selected cases are
explicitly unsupported. SIGKILL can lose final counters.

## Reviewed scopes

Optional `coverage_scope = "scope.json"` in the descriptor selects an exclusion
ledger pinned to the complete source fingerprint. Each exclusion records exact
ranges, reason, category, and evidence. Source drift fails validation. Excluded
code is never marked executed; excluding executed bodies or branch exits is
rejected. Adapter-specific scopes and their audits live under adapters.

`coverage/scope-profile.json` retains the input ledger; `scoped.json` retains
applied exclusions and remaining gaps. Raw measurements remain unchanged.
`--min-line-coverage` and `--min-branch-coverage` use the configured scope;
`--raw-coverage` selects raw totals. Thresholds require collection.

## Guest data

Host and guest source inventories, content fingerprints, and repository pins
must match before data import. Guest paths are normalized into host paths.
Raw branch arcs are united first; percentages are never averaged. Source
inventory is rechecked before reports are finalized. The same declared source
path drives collection, guest provenance, validation, and scoped reporting.

Coverage goals, implementation-specific tracing limits, measured totals, and
platform exclusions belong to the owning adapter. They are not portable
conformance requirements.
