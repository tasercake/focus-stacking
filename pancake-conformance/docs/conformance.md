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
`[fixtures] native_update_asset = "MyApp-macOS.dmg"` declares the release filename
used by the service policy fixture; its default is `FocusStacker-macOS.dmg`.

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
