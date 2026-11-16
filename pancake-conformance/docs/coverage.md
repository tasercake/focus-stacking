# Reference-target coverage

Coverage is optional instrumentation. Portable cases do not import ChimpStackr,
Qt or the coverage collector. The reference adapter inserts an opt-in
`sitecustomize.py` directory into the target process's `PYTHONPATH` and sets
`COVERAGE_PROCESS_START`. Coverage starts before application imports. Child
processes inherit that environment; multiprocessing and Python threads are
included. Separate process data files are combined after cases finish.

The collector measures every Python file beneath the configured target `src/`
directory, including files never imported. It uses its own configuration rather
than ChimpStackr's configuration, which omits GUI modules. No source file,
exception block or platform branch is excluded by suite configuration. Default
coverage exclusion and partial-branch regular expressions are reset, so target
`pragma: no cover` and `pragma: no branch` comments do not shrink the report. Target business logic is never invoked by
the collector to improve a coverage number.

Reports contain separate line and branch coverage ratios:

- `coverage.json`: executed/missing lines and executed/missing branch exits per file.
- `coverage.xml`: Cobertura format for CI.
- `html/index.html`: annotated source browser.
- `summary.json`: independent line/branch percentages and complete gap inventory.
- `coverage.ini`: exact measurement configuration used for the run.

`CoverageSession(source_root, output_dir).environment(env)` returns a child
environment without modifying its argument. `finalize()` combines child data
and writes reports. It fails explicitly when target execution produced no
coverage data. Use a fresh output directory for each run. Graceful target exit
or SIGTERM saves counters; SIGKILL cannot guarantee final counters.

At pinned ChimpStackr commit `046266223945cc1cbf8eacd295c00ee08d42d095`, the raw
Python denominator is **31 files, 7,256 executable lines and 1,812 branch exits**.
These values are observations from coverage.py on CPython 3.12, not a selected
"testable" subset. A later source/interpreter change can change the denominator.

## Reviewed application scope

The revised coverage goal is 100% of used, reachable code for this macOS source
target. Raw measurements remain unchanged. `targets/chimpstackr/chimpstackr-coverage.json`
defines the separate `macos-source-application` scope, pinned to the complete
source SHA256. Every exclusion names exact ranges, category, reason and evidence.
See [scope audit](coverage-scope-audit.md) and [goal](goal.md).

`coverage/scoped.json` retains the applied exclusion ledger, counts and remaining
missing statements/branch exits. `coverage/scope-profile.json` freezes the exact
input manifest before execution. Excluded code is never marked as executed.
Covered unused definitions may leave the scoped denominator because importing
a function does not make its body used. Excluding an executed function body or
an executed branch exit is rejected. Source drift also fails the scope check.

Thresholds use this configured scope. `--raw-coverage` uses raw totals instead.
Host and guest **raw arcs are united first**; one common scope is applied after
path normalization. Percentages are never added or averaged. A later target
must remove or replace this reference-specific manifest.

Unused application helpers and impossible foreign-platform/source-packaging
paths are outside the goal. Their exclusion does not imply they can safely be
deleted from a public Python library or a future packaged/Windows/Linux build.
Recoverable errors, device fallback and missing tests remain inside the goal.
Native JIT bodies remain measured gaps, separately listed as tracing limits;
they are not classified as dead code.

## Raw coverage limits

The suite does not replace platform checks, run source unit tests or mark
unreachable code as covered. Current source has
mutually exclusive platform and packaging paths that cannot all execute in a
normal source-launched macOS app:

| Source surface | Required environment or condition |
| --- | --- |
| `run.py` | Windows AppUserModelID, Linux desktop-file icons, frozen macOS icon path |
| `lightroom.py` | Windows registry/process enumeration and executable discovery; packaged application connection |
| `updater.py` | Windows ZIP/PowerShell installation, Linux AppImage replacement, frozen macOS DMG self-replacement |
| `compute.py`, OpenCL pipeline | No-device, exhausted-memory, driver/kernel faults, calibration/cache errors |
| Image IO and GUI lifecycle | Unsupported RAW codecs, IO faults, exceptional dialogs and rare event sequences |

Triggering real self-update replacement is also a separate packaged integration
scenario, not a reason to modify the user's installed app during this run.
Missing line and branch lists remain visible in reports. Adding Windows/Linux
and isolated packaged-app/fault environments can close parts of the gap.

The source-profile manifest also excludes Lightroom install/repair/remove and
update installation UI callbacks. `application_path()` returns `None` for a
source launch; `_check_application()` raises before plugin destination checks,
and the Lightroom card disables its action/hides Manage. `UpdateDialog` cannot
download or install because source `can_install()` is false. Their available
status and release-page paths remain in scope. Packaged testing must restore
these callbacks and underlying functions.

The denominator covers **Python executable code**. Embedded OpenCL C kernels,
compiled dependencies and Lightroom Lua plugin execution need their own
language/runtime collectors; this adapter does not claim to measure them.
Numba's native machine code also runs outside ordinary Python tracing. Its
Python source remains in the denominator. The collector disables Numba's
compile-time coverage notifications: compiled lines do not prove runtime line
or branch execution. JIT execution settings stay unchanged. See Numba's
[compiled-code coverage documentation](https://numba.readthedocs.io/en/stable/user/code_coverage.html).
Image/device conformance tests still execute and validate real GPU kernel
results. Code coverage and output correctness remain separate evidence.

## Backend observations

A separate read-only profiling hook supplies execution provenance. It is
independent of coverage and activates only when the reference adapter sets an
events path. It does not wrap app methods, replace functions, alter device
choice, inject results or suppress exceptions. See [diagnostics.md](diagnostics.md).

Qt-created worker threads require an explicit instrumentation entry hook because
they do not execute Python's `threading.Thread` bootstrap. The GUI launch adapter
wraps only the five existing QRunnable `run` entry points: main processing,
image loading, thumbnails, background measuring and update work. Each wrapper
installs the existing coverage thread tracer and optional read-only observer,
executes its original callback exactly once, then restores prior trace/profile
hooks. Original return values and exceptions are preserved. The conformance
case still starts work through native controls; no worker is called directly
by a case. A real `_thread.start_new_thread` harness check verifies both branch
exits, every worker line, completion diagnostics and hook restoration.
