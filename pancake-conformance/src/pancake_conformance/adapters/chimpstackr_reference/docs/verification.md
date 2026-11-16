# Historical conformance reference

> Historical adapter record. Commands and paths describe the prior layout.
> See [current setup](../README.md) for this adapter.

This record predates the split into `pancake-conformance/` and
`pancake/`. Counts, hashes, runtime state, and artifact paths below
describe the archived commits, not the current project. The current catalog
contains 308 cases. Before the project moves, 252 harness tests passed
with two live GUI tests excluded; lint, frozen lock validation, and package
build passed. A copied project installed and listed all 308 cases without the
parent repository, ChimpStackr checkout, or Qt extra. No full native VM replay
was made after that earlier move.

Verified implementation commit: `08b05f2f6e1c9f3b67367c34d20bfdd49221faaf`.
The final replay completed all 295 selected cases: **294 passed, zero failed,
one unsupported**. Overall status is `partial`, exit code 0, because the Tart
guest has no physical GPU. The unsupported GUI case is not a passing reference
and its body does not execute. All 38 physical-device cases ran on the host.

| Suite | Passed | Unsupported |
| --- | ---: | ---: |
| CLI and services | 56 | 0 |
| Algorithms | 171 | 0 |
| Physical devices | 38 | 0 |
| Native interface | 29 | 1 |

The harness and Bokehforge tests also pass: **299 tests** with
`--gui-vm --gui-vm-persist`. Package build, lock validation and conformance Ruff
checks pass. The built wheel contains both console commands and the native
Swift transport. Bokehforge application/data code remains identical to main;
ChimpStackr source remains clean and unchanged at the pinned submodule commit.

## Coverage

| Measurement | Lines | Branch exits |
| --- | ---: | ---: |
| Raw Python source | 5,931 / 7,256 (81.74%) | 1,162 / 1,812 (64.13%) |
| Reviewed macOS source scope | 5,878 / 6,545 (89.81%) | 1,162 / 1,580 (73.54%) |

The scope removes 711 executable lines and 232 branch exits with exact ranges
and evidence. It does not count them as executed. There are still **667 missing
scoped lines and 418 missing scoped branch exits**. Recoverable failures, dynamic
UI paths and native JIT tracing limits remain gaps. This does not claim 100%.
See [coverage rules](coverage.md), [scope audit](coverage-scope-audit.md) and
[the pinned scope](../chimpstackr-coverage.json).

Host/guest raw data normalize to exactly **31 unique source files**. No guest
path remains in the merged database; measured contexts are only `[""]`, with
no compiler-only Numba coverage. Both raw and scoped missing inventories are
retained. A negative control with 100% line/branch thresholds correctly exits 1
and records the failed scoped gate in JSON and JUnit.

## Runtime and desktop isolation

The host uses Python 3.12.12; the guest uses its separately pinned Python
3.12.16. The locked PySide package is `6.12.0a1.dev1794566397`, loading Qt
6.12.1. Runtime versions are recorded for both execution environments.

All **33 application sessions** in the final GUI phase exited naturally with
code 0. Native file dialogs, exports and viewer gestures passed. During a
30.1-second guest GUI observation, 290 host foreground samples all remained on
Codex. The VM ran with `--no-graphics --no-clipboard --no-audio`; no host viewer
or VNC runtime was opened. The unchanged transport and separate guest desktop
keep native input inside the guest. The VM remains running because validation
explicitly used `--gui-vm-persist`.

## Frozen evidence

The reference contains 294 successful case contracts, one unsupported ID and
317 decoded output arrays. Its manifest checksum stayed unchanged throughout
the final replay. It originated at implementation commit `4b2c561`; replay at
`08b05f2` validates it against the merged dependency set and safe constructor
metadata hooks. The application source pin is identical in both runs.

| Pin | SHA256 or commit |
| --- | --- |
| ChimpStackr | `046266223945cc1cbf8eacd295c00ee08d42d095` |
| Complete target Python source | `c4bdcc78e95ccd3c62ec7c3375155a936ec026b42a9f8eeafe7ee48e88aba04a` |
| Final `uv.lock` | `912dde098b93749fd50b386dbc7ca9874f3d334833701e15af12bbef7d81dd6b` |
| Reference manifest | `7fd36d27bab634dc270cfa6a700a1b7c2d6470553a5502167da4872557131c62` |

Local generated evidence remains under `artifacts/` and is not committed:

- `conformance-vm-release-replay/`: final JSON/JUnit, provenance, guest artifacts and merged coverage.
- `reference-vm-0462662-expanded/`: immutable reference manifest and output arrays.
- `coverage-scope-negative-final/`: expected failing 100% gate control.
- `vm-setup/host-focus-expanded-full-gui.json`: read-only host focus observation.

Replay from `pancake-conformance/` after restoring the archived baseline under its
`artifacts/` directory and configuring the dedicated guest:

```sh
uv run --extra chimpstackr pancake-conformance run \
  --gui-vm --gui-vm-persist \
  --baseline artifacts/reference-vm-0462662-expanded \
  --output artifacts/my-replay
```

Archive the whole reference directory, suite commit, target commit, descriptor,
scope manifest, lockfile and passing replay provenance together before switching
implementations. Required one-time guest setup is documented in
[guest setup](gui-vm-setup.md).
