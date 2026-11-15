# Focus stacking conformance

External conformance tests for a focus stacking application. The reference target
is the ChimpStackr submodule at commit
`046266223945cc1cbf8eacd295c00ee08d42d095`. The harness is a separate uv project;
its tests do not import the target application, depend on its implementation
language, or inspect its UI framework's objects.

The current supported host is macOS. Numerical tests use real command-line
processes. Interface tests use macOS Accessibility and physical keyboard/pointer
input against real Cocoa windows and native file dialogs. Required hardware or
permissions missing from the host cause failures, not silently skipped tests.

## Run

From this repository root:

```sh
git submodule update --init submodules/ChimpStackr
uv sync --extra chimpstackr
uv run --extra chimpstackr stack-conformance list
uv run --extra chimpstackr stack-conformance run --target targets/chimpstackr.toml
```

Native UI tests require Apple's Swift compiler (`xcrun swiftc`), an unlocked
desktop session, Accessibility permission inherited by the launching terminal
or app, Automation access to System Events for native keyboard shortcuts, and
Screen Recording permission for screenshots. They control the
foreground app: leave keyboard and pointer idle during the interface suite.
The first native test compiles a small Swift AX/CGEvent transport into a temporary
cache. No Appium server, browser, or third-party automation service is required.

Use the same single entry point for selection, reports, and reference capture:

```sh
uv run --extra chimpstackr stack-conformance run --suite algorithms --suite devices
uv run --extra chimpstackr stack-conformance run --suite interface
uv run --extra chimpstackr stack-conformance run --case 'algorithms.precision16.*'
uv run --extra chimpstackr stack-conformance list --json
```

`--suite` and `--case` can be repeated. `--case` accepts shell-style patterns;
quote them so the shell does not expand them. An empty selection is an error.
Every selected case runs, including after another case fails. Exit codes are
0 for success, 1 for conformance/coverage failure, and 2 for configuration or
environment errors. Run output directories must be new or empty.

## Separation of concerns

| Layer | Contract | Implementation coupling |
| --- | --- | --- |
| Algorithm cases | Explicit settings, generated inputs, exported pixels | None |
| CLI cases | Arguments, errors, exit codes, progress, files | Public command-line interface only |
| Device cases | Completed backend evidence and CPU/GPU image equivalence | Versioned JSON diagnostics, not target functions |
| Interface cases | Semantic accessibility IDs, native input, visible state, exports | OS accessibility contract only |
| Target descriptor | Executables, argument mapping, environment, capabilities | Target-specific configuration |
| Reference adapter | Python launch, coverage, identifiers, read-only observations | ChimpStackr-specific; replaceable |

The large numerical matrix runs through the CLI. Native GUI cases cover complete
workflows and selected numerical/export equivalence checks. They do not repeat
the whole numerical matrix through clicks. No case calls an application stack,
alignment, export, or GUI business method directly.

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
[algorithm contracts](docs/algorithm-contract.md) and
[device diagnostics](docs/diagnostics.md) for detailed limits.

## Freeze a reference and switch targets

```sh
uv run --extra chimpstackr stack-conformance run \
  --target targets/chimpstackr.toml \
  --record-baseline artifacts/reference-0462662

uv run --extra chimpstackr stack-conformance run \
  --target targets/replacement.toml \
  --baseline artifacts/reference-0462662
```

A baseline contains decoded output arrays, checksums, shapes, dtypes, explicit
pixel-error limits and provenance. It refuses overwrite. A failed recording run
does not publish a completed manifest. Baseline comparisons require the same
output inventory for every selected case. Copy the entire baseline directory
when archiving a reference. Freeze the suite commit, `uv.lock`, target commit,
target descriptor and baseline together. Review compatibility exceptions before
accepting intentional improvements in a port.

Default baseline limits for genuine 16-bit outputs are mean error 8 and peak
error 128 in 16-bit code values, so reducing data to 8 bits fails comparison.
Eight-bit, float and exposure-fusion compatibility outputs use normalized mean
error 0.5/255 and peak error 3/255. Exposure fusion retains its documented 8-bit
precision and one-level repeat variation. Each frozen output stores its actual
limits; changing them requires an explicit baseline review.

Copy `targets/chimpstackr.toml` for another implementation. Set `root`, `cli`
and `gui` to its executables, remove `adapter = "chimpstackr-python"`, update
the declarative argument mapping and target-specific environment. Shells are
never used to execute commands. A compiled replacement needs no Python target
dependency; install the harness with `uv sync` and run it without the
`chimpstackr` extra. Preserve the public CLI and semantic UI contracts, or put
small translations at the target boundary. See
[UI protocol](docs/ui-protocol.md) for IDs and native operations.

Strict device tests require completed backend diagnostics written as JSON lines
to `CONFORMANCE_EVENTS_PATH`. Another target can emit that contract from a
small observation hook in any language. Merely accepting `--gpu` or printing a
GPU selection message does not satisfy those tests.

## Reports and coverage

Every run writes `report.json`, `junit.xml` and `provenance.json`. Per-case
directories retain commands, stdout/stderr, input hashes, output images,
observed execution metadata and native UI action traces. GUI failures retain
accessibility trees and screenshots when capture permission is available.

Reference coverage is enabled by default. `--no-coverage` disables it.
`--coverage` requires a compatible target-specific collector. Python coverage
reports include **all 31 application source files**, with line and branch
coverage reported separately. Never-imported files remain in the denominator;
the application's own coverage omissions are not used.

```sh
uv run --extra chimpstackr stack-conformance run \
  --min-line-coverage 100 --min-branch-coverage 100
```

That command enforces the stated target and currently fails: raw 100% is not
achievable in a macOS source run while Windows/Linux, frozen-app installers,
hardware/IO failures and unused internal paths remain present. The suite does
not alter platform identity, execute private unit tests, exclude source files,
or fabricate execution to claim 100%. Python tracing also does not measure
embedded OpenCL C, Lightroom Lua or compiled dependencies. Full missing-line
and branch inventories remain available. See [coverage scope](docs/coverage.md).

## Verify the harness

```sh
uv run --extra chimpstackr pytest
uv run --extra chimpstackr ruff check src/stack_conformance tests
```

Harness tests exercise negative controls: wrong pixels, missing outputs,
invalid configuration, process timeout, missing coverage evidence and silent
CPU fallback. These are separate from the external application conformance
catalog. Platform and packaged-app support must be extended explicitly before
claiming Windows, Linux, installer, updater or Lightroom-host conformance.
