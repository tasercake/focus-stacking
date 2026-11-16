# Pancake Rust adapter

Status: declarative integration contract for an unimplemented application.
No Pancake executable exists yet. No conformance pass is claimed.

`pancake.toml` is the entire initial adapter. It maps direct commands, flags,
diagnostics, isolated state, and full target capabilities. No Python wrapper,
business hook, application import, algorithm, codec, or probe is needed.

Capabilities express the required target, not completed scaffold features.
They keep unfinished requirements in the failing denominator. Slint native UI
mappings will be added after observing actual accessibility controls.

Expected binaries: `pancake/target/release/pancake-cli` and
`pancake/target/release/pancake-gui`. Build once before cases. Add a tested thin
launcher only if platform executable/package behavior requires it; never build
inside each invocation or synthesize application output.

`case-roadmap.json` snapshots all 376 contract-v2 IDs, required capabilities, and
primary milestones. It is planning data, not a passing result or test oracle.

The application will support `CONFORMANCE_EVENTS_PATH` for truthful diagnostics
and `CONFORMANCE_UI_SETTINGS_DIR` for isolated profiles. `PANCAKE_*` settings in
the descriptor are planned public configuration, not existing scaffold APIs.

Native coverage uses Pancake LLVM tooling. There is no Python instrumentation
or coverage exclusion ledger.

Initial red smoke, from workspace root:

```sh
uv run --project pancake-conformance --frozen pancake-conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --case cli.help --no-coverage \
  --output artifacts/pancake-conformance/adapter-initial-REPLACE_WITH_UNIQUE_RUN_ID
```

Until P1 creates the executable, this must fail with a missing-binary diagnostic.
Do not add a mock executable to turn it green.

See [implementation plan](../../../../../pancake/docs/implementation-plan.md)
for phases, runtime qualification, acceptance, and the physical-GPU GUI lane.
