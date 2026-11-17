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

`case-roadmap.json` snapshots all 376 contract-v2 IDs, required capabilities,
primary integration milestones, and P0 feasibility gates. All 17 P0 gates must
pass before P1 starts. Case-to-gate links identify feasibility responsibility;
they do not claim every full case has already run or passed. This is planning
data, not a passing result or test oracle.

P0.01 snapshot review is resolved by explicit adoption of the current committed
contract. [Drift review](drift-review.md) covers 16 modified and four added core files;
[reviewed snapshot](contract-current.json) pins all 90. Historical fingerprints
and all 376 case records remain intact. Numeric engineering targets are fixed;
real D150/E9 inputs and diagnostic CPU jobs are pinned separately; T50/R50, matched baseline protocol and complete support-matrix qualification remain pending.

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

Until real P0 qualification or P1 integration supplies the mapped executable,
this must fail with a missing-binary diagnostic. Do not add a mock executable
to turn it green.

See [implementation plan](../../../../../pancake/docs/implementation-plan.md)
for all P0 blocker gates, later regression phases, runtime qualification,
acceptance, and the physical-GPU GUI lane that must be proven during P0.
