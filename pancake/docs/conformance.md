# Pancake conformance

External conformance tests for a focus stacking application. The reference target
is the ChimpStackr submodule at commit
`046266223945cc1cbf8eacd295c00ee08d42d095`. The harness is a separate uv project;
its tests do not import the target application, depend on its implementation
language, or inspect its UI framework's objects.

The current supported host is macOS. Numerical tests use real command-line
processes. Interface tests use macOS Accessibility and physical keyboard/pointer
input against real Cocoa windows and native file dialogs. Required hardware or
permissions missing from the host cause failures, not silently skipped tests.

The reference extra uses an official, immutable Qt for Python CI build that
bundles Qt 6.12.1's native Accessibility ownership fix
([QTBUG-149612](https://qt-project.atlassian.net/browse/QTBUG-149612)). Exact
wheel URLs and hashes are locked. The PySide package label is
`6.12.0a1.dev1794566397`; loaded Qt is **6.12.1**, recorded in run provenance.
This harness runtime remains within ChimpStackr's declared dependency range;
application source stays unchanged. Native controls must expose valid
accessibility data; invalid trees and abnormal application exits fail tests.

## Run

From this repository root:

```sh
git submodule update --init submodules/ChimpStackr
cd pancake
uv sync --extra chimpstackr
uv run --extra chimpstackr pancake list
uv run --extra chimpstackr pancake run --target targets/chimpstackr.toml --gui-vm
```

Configure the dedicated Tart macOS VM once using [guest setup](gui-vm-setup.md).
`--gui-vm` runs interface cases inside that guest. CLI, algorithm, and physical
device cases stay on the host. The VM has no host window, clipboard, or audio
by default; its input events do not use the host desktop. Missing VM, SSH,
guest desktop, permissions, or runtime fail clearly without host GUI fallback.
`--gui-vm-visible` opts into a window when starting the VM; it does not change
an already-running VM's display mode. `--gui-vm-persist` leaves the dedicated
VM running for later tests. Both require `--gui-vm` and default off.
An already-running configured VM is reused; the default stops it after tests.

GUI exports are fetched before CLI parity checks run on the host. Guest input
and export hashes are checked first. Those cases remain pending until the host
comparison succeeds; a guest native phase alone cannot produce a passing final
verdict. Direct target CLI execution is rejected inside the guest.

Without `--gui-vm`, interface tests retain direct host desktop behavior.
Native UI tests require Apple's Swift compiler (`xcrun swiftc`), an unlocked
desktop session, Accessibility permission inherited by the launching terminal
or app, Automation access to System Events for native keyboard shortcuts, and
Screen Recording permission for screenshots. They control the
foreground app: leave keyboard and pointer idle during the interface suite.
The first native test compiles a small Swift AX/CGEvent transport into a temporary
cache. No Appium server, browser, or third-party automation service is required.

Use the same single entry point for selection, reports, and reference capture:

```sh
uv run --extra chimpstackr pancake run --suite algorithms --suite devices --gui-vm
uv run --extra chimpstackr pancake run --suite interface --gui-vm --gui-vm-persist
uv run --extra chimpstackr pancake run --case 'algorithms.precision16.*' --gui-vm
uv run --extra chimpstackr pancake list --json
```

`--suite` and `--case` can be repeated. `--case` accepts shell-style patterns;
quote them so the shell does not expand them. An empty selection is an error.
Explicit suites execute in the supplied order. To reserve a short uninterrupted
desktop window, put `--suite interface` first, followed by `--suite cli --suite
algorithms --suite devices`; the remaining headless work can continue after the
desktop is released. Unknown suite names fail instead of silently dropping tests.
Every selected case runs, including after another case fails. Exit codes are
0 for success, 1 for conformance/coverage failure, and 2 for configuration or
environment errors. Run output directories must be new or empty.
`--fail-fast` stops after the first failure. Interrupted and fail-fast runs report
selected/completed counts and an explicit incomplete state; partial execution
cannot produce a successful frozen baseline or a passed overall report.

## Separation of concerns

| Layer | Contract | Implementation coupling |
| --- | --- | --- |
| Algorithm cases | Explicit settings, generated inputs, exported pixels | None |
| Service cases | Versioned JSON requests, local HTTP fixtures, checksums and errors | Neutral process hook; reference adapter maps original functions |
| CLI cases | Arguments, errors, exit codes, progress, files | Public command-line interface only |
| Device cases | Completed backend evidence and CPU/GPU image equivalence | Versioned JSON diagnostics, not target functions |
| Interface cases | Semantic accessibility IDs, native input, visible state, exports | OS accessibility contract only |
| Target descriptor | Executables, argument mapping, environment, capabilities | Target-specific configuration |
| Reference adapter | Python launch, coverage, identifiers, read-only observations | ChimpStackr-specific; replaceable |

The large numerical matrix runs through the CLI. Native GUI cases cover complete
workflows and selected numerical/export equivalence checks. They do not repeat
the whole numerical matrix through clicks. No case calls an application stack,
alignment, export, or GUI business method directly. Reachable update-service
logic also has a language-neutral JSON hook, so network policy, cancellation and
checksum failures do not require repeated native interactions. The reference
adapter calls the original service implementation. Unused math helpers are
outside the application coverage goal; the suite does not add callers for them.

The ChimpStackr GUI bootstrap starts the original `src.run.main`, selects normal
user preferences in an isolated INI profile, and attaches semantic accessibility
identifiers. It also exposes an existing image canvas and its read-only viewport
state through accessibility. The reference profiler observes completed work and
does not replace algorithm functions. **No ChimpStackr source files are changed.**

Each case has isolated settings, device cache, temporary files, inputs and
outputs. A run shares only the Numba compiler cache; this avoids recompiling
unchanged machine code for every subprocess. Initial source-target preferences
select CPU processing and disable automatic update checks. Tests do not install
updates, change the installed app, or modify the user's Lightroom plugin.

Current catalog contains 295 cases:

| Suite | Cases | Execution with `--gui-vm` |
| --- | ---: | --- |
| CLI and services | 56 | Host subprocesses |
| Algorithms | 171 | Host subprocesses |
| Physical devices | 38 | Host CPU and actual GPU |
| Interface | 30 | 29 guest cases; one physical GPU case unsupported |

## Generated fixtures and numerical checks

Fixtures are generated on demand from fixed seeds using NumPy/SciPy, Pillow,
tifffile and OpenEXR. No photo dataset is downloaded or committed. Fixtures
include complementary focus planes, flat color, odd dimensions, real 16-bit
ramps, known shifts/rotations/scale/shear, focus breathing, exposure brackets,
deep slabs, Unicode paths and image-format/orientation cases. Reports record
fixture generator version, metadata and input hashes.

Independent decoders validate channel order, dimensions, dtype, finite values,
range and genuine 16-bit precision. Numerical checks include focus recovery in
each sharp region, color/geometry error, crop behavior, deterministic repetition,
cross-format exports and actual CPU/GPU agreement. Output files are compared as
decoded pixels, not encoded file hashes. Error budgets use the same numeric
units in each test and explicitly document known hardware/algorithm variation.

Compatibility and quality checks are distinct. Current reference behavior
includes these known limitations: weighted-average returns black for spatially
constant inputs, and exposure fusion uses an internal 8-bit path even for
16-bit inputs. EXIF orientations 5 and 7 are interchanged, and some small-texture
alignment requests have excessive crop or ambiguous breathing estimates.
Explicit compatibility cases preserve these observations; they
do not certify them as correct image processing. See
[algorithm contracts](algorithm-contract.md) and
[device diagnostics](diagnostics.md) for detailed limits.

## Freeze a reference and switch targets

```sh
uv run --extra chimpstackr pancake run \
  --target targets/chimpstackr.toml --gui-vm \
  --record-baseline artifacts/reference-0462662

uv run --extra chimpstackr pancake run \
  --target targets/replacement.toml --gui-vm \
  --baseline artifacts/reference-0462662
```

A baseline contains decoded output arrays, checksums, shapes, dtypes, explicit
pixel-error limits and provenance. It refuses overwrite. A failed recording run
does not publish a completed manifest. Baseline comparisons require the same
output inventory for every selected case. Copy the entire baseline directory
when archiving a reference. Freeze the suite commit, `uv.lock`, target commit,
target descriptor and baseline together. Review compatibility exceptions before
accepting intentional improvements in a port.

VM capability limits remain explicit. The physical GPU GUI case is reported as
`unsupported`, with a reason and a JUnit skipped entry; it is never counted as
passed or executed for coverage. A run with all supported cases passing and
unsupported cases has status `partial` and exit code 0. A recorded baseline
stores unsupported IDs separately from successful references. If a later target
can execute those cases, new references are required before comparison can pass.

Default baseline limits for genuine 16-bit outputs are mean error 8 and peak
error 128 in 16-bit code values, so reducing data to 8 bits fails comparison.
Eight-bit, float and exposure-fusion compatibility outputs use normalized mean
error 0.5/255 and peak error 3/255. Exposure fusion retains its documented 8-bit
precision and one-level repeat variation. Each frozen output stores its actual
limits; changing them requires an explicit baseline review.

Copy `targets/chimpstackr.toml` for another implementation. Set `root`, `cli`,
`gui` and `probe` to its executables, remove `adapter = "chimpstackr-python"`
and the reference-only `coverage_scope`, update
the declarative argument mapping and target-specific environment. Shells are
never used to execute commands. A compiled replacement needs no Python target
dependency; install the harness with `uv sync` and run it without the
`chimpstackr` extra. Preserve the public CLI and semantic UI contracts, or put
small translations at the target boundary. See
[UI protocol](ui-protocol.md) for IDs and native operations.
The `state` table names case-owned mutable paths; `services` maps canonical
service names to target endpoint environment hooks. Neither belongs inside
portable cases. See [component protocol](component-protocol.md).

Strict device tests require completed backend diagnostics written as JSON lines
to `CONFORMANCE_EVENTS_PATH`. Another target can emit that contract from a
small observation hook in any language. Merely accepting `--gpu` or printing a
GPU selection message does not satisfy those tests.

## Reports and coverage

Every run writes `report.json`, `junit.xml` and `provenance.json`. Per-case
directories retain commands, stdout/stderr, input hashes, output images,
observed execution metadata and native UI action traces. GUI failures retain
accessibility trees and screenshots when capture permission is available.
Each case's `notes.artifact_directory` locates its files; registered output paths
are relative to that directory. VM runs retain raw guest reports and coverage,
host parity logs, transport metadata, and the final merged report separately.

Reference coverage is enabled by default. `--no-coverage` disables it.
`--coverage` requires a compatible target-specific collector. Python coverage
reports include **all 31 application source files**, with line and branch
coverage reported separately. Never-imported files remain in the raw denominator;
the application's own coverage omissions are not used. A separate, source-pinned
scope excludes reviewed dead, unused and unreachable regions. Every exclusion
has exact ranges and evidence. Raw and scoped results remain visible together.
Coverage thresholds use the configured scope; `--raw-coverage` selects raw totals.

```sh
uv run --extra chimpstackr pancake run \
  --gui-vm --min-line-coverage 100 --min-branch-coverage 100
```

That command enforces 100% of the reviewed macOS application scope. It still
fails while retained recovery paths and native tracing gaps remain uncovered.
Confirmed unused helpers and foreign-platform/packaged-only bodies are excluded
from that goal, per the [revised scope](goal.md). The suite does not alter
platform identity or fabricate execution. Python tracing also does not measure
embedded OpenCL C, Lightroom Lua or compiled dependencies. Full missing-line
and branch inventories remain available. See [coverage scope](coverage.md).

## Verify the harness

```sh
uv run --extra chimpstackr pytest --gui-vm --gui-vm-persist
uv run --extra chimpstackr ruff check src/pancake tests
```

These checks cover the Pancake project. Bokehforge has its own environment and
test suite in `../bokehforge`.

Harness tests exercise negative controls: wrong pixels, missing outputs,
invalid configuration, process timeout, missing coverage evidence and silent
CPU fallback. These are separate from the external application conformance
catalog. Platform and packaged-app support must be extended explicitly before
claiming Windows, Linux, installer, updater or Lightroom-host conformance.
