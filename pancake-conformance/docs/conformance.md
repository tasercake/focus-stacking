# Focus-stacking conformance

The suite defines a reference contract for external application behavior.
Cases exercise CLI processes, component protocol processes, or native UI input.
They do not import application modules. Synthetic fixtures and independent
validators are shared across implementations. Source coverage is optional,
adapter-specific evidence, separate from conformance results.

## Target descriptor

`run --target PATH` is required. Paths are relative to the descriptor, except
`instrumentation.source`, which is relative to the target root. A minimal target:

```toml
schema_version = 1
name = "my-focus-stacker"
root = "/path/to/application"
cli = ["./bin/stacker"]

[stack]
input = ["--input", "{inputs}"]
output = ["--output", "{output}"]

[stack.options]
method = "--method"
device = { cpu = ["--cpu"], gpu = ["--gpu"], auto = [] }
```

Add mappings for every option exercised by the selected cases. Unsupported
options fail explicitly. `cli`, `gui`, and `probe` are argument arrays, with
`{python}` and `{target}` substitutions; no shell executes them. Optional
`--cli-command` and `--gui-command` JSON arrays override commands.

`probe` implements the [component protocol](component-protocol.md). `gui`
implements the [native UI contract](ui-protocol.md). `[env]` declares child
variables with `{case}`, `{home}`, `{target}`, and `{run}` substitutions.
`[state]` names case-contained mutable directories. `[services]` maps service
names to endpoint environment variables. `capabilities` declares target features.
No update or delivery mechanism is part of the portable catalog.

## Feature contracts and optional capabilities

The suite preserves user-visible features rather than reference internals.
Selected optional cases run only when the descriptor declares their required
capabilities. Missing features are reported as `unsupported`; these cases are
not passed and do not execute the target. Reports and baselines retain the
unsupported reason. Declare `native_gui` for GUI cases; diagnostic device cases
also require `backend_evidence` and the requested `cpu` or `gpu` capability.
VM runs exclude physical-GPU requirements even when host hardware supports them.

`CaseContext.stack` sends only requested options plus explicit `[stack.defaults]`.
There is no global CPU, kernel, pyramid, or scale setting. CLI syntax remains
in `[stack.options]`. If `cli_reports` is declared, `[stack.observations]` supplies
regular expressions for `progress` and `quality_report`; diagnostics may use
any readable format or output stream. Neither `[n/n]` syntax nor warning words
are universal requirements. Existing-output refusal and parent-directory
creation are valid policies when output and existing files stay correct.
Input-order tests validate usable output without demanding pixel identity after
reordering. Legacy case identifiers remain stable for selection compatibility;
their descriptions and assertions define the current behavior.

The [semantic UI contract](ui-protocol.md) maps actions, controls, choices, and
read-only observations to each implementation. It supports different labels,
shortcuts, dropdown/radio selection, and collection layouts. Cases verify actual
state changes and exported pixels; mappings cannot manufacture successful state.
Optional strict frozen-baseline comparisons remain available when pixel-level
regression identity is wanted. Baseline capture is not a requirement to use the
feature cases, and old snapshots should be reviewed after a contract revision.

## Adapter hooks and dependencies

An optional `adapter = "package.module"` selects an importable module. It may
export `environment(target, base, events_path)` to return a child environment
and `runtime_info()` to record runtime versions without creating a GUI. Unknown
adapters fail explicitly. Adapters supply launch commands and translate
observations; cases never branch on application identity.

An optional `[runtime] project = "path"` selects a separate locked uv project,
relative to the descriptor. That project installs the suite and target libraries.
Run the host CLI in this environment too. VM transport uses its environment for
both CLI and LaunchAgent execution. Without this field, the guest uses the
suite's environment. Target source, descriptor, and runtime must remain inside
the workspace for VM transport.

Optional `[instrumentation] source = "src"` enables Python coverage by default.
It requires a real source directory and the startup instrumentation described
in [coverage](coverage.md). Compiled targets can omit it. `--no-coverage` disables
collection; `--coverage` requires a declared source. `coverage_scope = "scope.json"`
selects a fingerprint-pinned exclusion manifest relative to the descriptor.

## Selection and reference capture

```sh
pancake-conformance list --json
pancake-conformance run --target target.toml --suite algorithms --suite devices
pancake-conformance run --target target.toml --case 'algorithms.precision16.*'
pancake-conformance run --target target.toml --record-baseline baselines/reviewed
pancake-conformance run --target replacement.toml --baseline baselines/reviewed
```

Baselines retain pixels, generated inputs, requests, and provenance. Capture
refuses overwrite. Compare the same selected cases and contract version.
Version 2 replaces the old defect characterizations with independent correctness
assertions. Keep version-1 directories immutable and capture a separate v2
baseline after its cases pass. A passing baseline comparison alone does not
establish image quality.

Reports retain each case's status, duration, evidence, and outputs. Failed or
interrupted runs remain incomplete. `--fail-fast` preserves completed evidence.
Unsupported capability cases are reported explicitly. A guest GUI comparison
remains pending until host CLI pixel verification completes.

## Execution and evidence

`--gui-vm` sends only interface cases to the configured guest. Host CLI,
algorithm, and physical-GPU execution remain on the host. There is no host GUI
fallback. Source fingerprints and repository pins bind guest results to host
inputs. Raw coverage arcs are normalized and combined before applying scopes.

Implementation-specific setup, coverage goals, exclusions, measured totals, and
historical verification records belong inside that implementation's adapter.
