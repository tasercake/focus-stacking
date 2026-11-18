# P7 native UI development

The first safe Slint application checkpoint is
`ea487ef3bbbce3e04212895aa758f479aca79be3`. Its isolated Linux native run
passed these real application cases, using the unchanged contract and a
descriptor that pointed at the debug GUI binary.

- `interface.controls.method-alignment`
- `interface.startup.empty`
- `interface.controls.advanced-visibility`
- `interface.settings.persistence`
- `interface.settings.lightroom-status`
- `interface.about`

The seventh selected case, `interface.sprint.viewer-input`, failed at the
expected boundary because positional images were not wired at this checkpoint.
The [report](p7-ui-evidence/controls-prototype.json) and
[provenance](p7-ui-evidence/controls-prototype-provenance.json) retain all
seven outcomes. The [P0 run](p7-ui-evidence/controls-p0-red.json) failed all six
control cases because the binary did not exist. A first real
[implementation run](p7-ui-evidence/advanced-race.json) passed five and exposed
a race between advanced-control expansion and the first new native element
being published. The revised action opens the real panel and moves keyboard
focus into the panel using Tab, with no artificial delay or injected state.
Both [failing](p7-ui-evidence/advanced-race-actions.jsonl.gz) and
[passing](p7-ui-evidence/advanced-pass-actions.jsonl.gz) native action traces
are retained.

The checkpoint used Rust 1.100.0, Ubuntu 24.04 x86_64 kernel
6.8.0-147-generic and a Ryzen 9 7950X3D host with a GeForce RTX 3090 and NVIDIA
580.178.04. These six cases exercise visual controls, preferences and native
input. They supply no physical GPU computation evidence.

Run `CARGO_PROFILE_DEV_DEBUG=0 CARGO_INCREMENTAL=0 cargo build --locked
--jobs 4 -p pancake-gui` from `pancake/`. The tested executable SHA-256 was
`f7e8bc7cc759895f3b6eb49e027719dc883b5332625a967e4c4bcef72aae5ee5`.
Cargo.lock SHA-256 was
`6b2cac8f004397ed97a4fb45cab802acccc86bf3e33e67de33074f8ab75864e3`.
The focused GUI Rust tests and strict Clippy checks with the
policy-generated configuration passed. The marked checkpoint has no
integrated GPU job or release build result.

### Isolated desktop setup

The unchanged conformance driver creates the Xvfb, Openbox and D-Bus
processes. On this host the task extracted Ubuntu packages locally and used
their executable, shared-library, config and theme directories through
`PATH`, `LD_LIBRARY_PATH`, `XDG_CONFIG_DIRS` and `XDG_DATA_DIRS`.
System libraries and user desktop state were untouched.

AccessKit needs accessibility enabled on its private session bus. Use a
path-local Openbox launcher for conformance that rejects invocations outside
the test desktop and invokes the same D-Bus call as the P0 oracle before
starting the normal window manager.

```sh
#!/bin/sh
set -eu
test "${PANCAKE_CONFORMANCE_LINUX_DESKTOP:-}" = 1
case "${XDG_RUNTIME_DIR:-}" in
    */artifacts/*/runtime) ;;
    *) exit 1 ;;
esac
gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus \
    --method org.freedesktop.DBus.Properties.Set org.a11y.Status IsEnabled '<true>' >/dev/null
exec /absolute/path/to/staged/openbox "$@"
```

Run the unchanged `pancake-conformance run --no-coverage` command with
the listed case IDs, a local adapter copy pointing at the debug binary and
a unique short artifact path. Use the release descriptor for integration
verification. For a long worktree path, keep the run directory name short
enough for the private accessibility Unix socket.

Source import, render, stack jobs, export, lifecycle and the remaining GUI
cases require further implementation and independent verification.

### Shared job and desktop workflow integration

The decoded source/viewer slice passed its native startup, layout, zoom and
fit checks. The unchanged weighted-average case subsequently selected actual
frames in the app, completed the shared worker and exported genuine TIFF16
pixels with CLI parity. The native RAW import/merge/export case passed on the
same staged host engine.

The software-presentation debug checkpoint `8f1da27b65c` passed 9 of 11
selected GUI cases with native input on Linux. The real 64-frame lifecycle
paused, resumed, cancelled, settled and successfully reused the worker.
The native export matrix, retained results, signed pixel crop, viewport
snapshot, compare/navigation, non-BMP paths and recovery cases passed.
The two failures occurred when users reopened an in-process GTK picker
immediately after cancelling it. The [raw report](p7-ui-evidence/workflow-debug-a.json)
and [provenance](p7-ui-evidence/workflow-debug-a-provenance.json) retain
every selected status. This development run used the debug binaries from
that checkpoint while strict-lint follow-ups were being edited.

The follow-up uses a private GDK display round-trip and restores focus to
the Slint owner after native panel closure. It also loads repository-owned
Slint source under a builtin URI, so source resolution stays in the pinned
widget bundle, and introduces a four-entry display-only preview cache.
