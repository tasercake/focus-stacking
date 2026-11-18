# Pancake P8 desktop services

Verified on 2026-11-18 on Ubuntu 24.04.5 x86-64, kernel 6.8.0-147-generic,
Ryzen 9 7950X3D. The native service probe uses GTK 3.24.41, ATK 2.52.0,
Gio 2.80.0, Thunar 4.18.8 and Rust 1.100.0 (0ef1bc386). The GTK/ATK
Rust bindings are 0.19.0. The probe exercises the production Linux service
modules pinned at `2cf26782b3fb6f08666a5ed619b6425e6daa2ee1` against the
unchanged Linux native conformance transport. It uses the suite's private X11
and D-Bus session. The probe's own small GTK window supplies the controls
that invoke the real modules. The release GUI includes the Slint controller.

The test-first history checkpoint `cb2dc7f` failed for the missing
`RecentFolders` API. The four tests pass on the pinned implementation and
exercise canonical Unicode MRU history, failure-preserving writes, malformed
and oversized files, and bounded entries. Scoped workspace Clippy passed.
[History red](history-red.txt) · [History tests](history.txt) · [Clippy](clippy.txt)

An attached GTK submenu reported `AXMenu` for its owner despite appearing at
the pointer. The revised File menu exposes the real actionable
`AXMenuItem` and expands a second native File popup with recent entries.
[Initial role result](submenu-role-red.txt)

The private native probe cancelled and reopened a chooser in the same
process, accepted an actual original Unicode PNG, selected its Unicode parent
directory and resolved a Unicode save path. The save probe wrote a marker
through the chosen path. Image encoding is verified separately by the stacking
suite. The probe selected a native Recent item, cleared the history on disk,
read the disabled empty item, revealed the actual source in Thunar and
observed native focus. File > Close Window exited normally. The source PNG
was byte-identical after the actions. The native trace contains real
AT-SPI snapshots and physical input.
[Panel results](panels.json) · [Menu and reveal results](menus.json) ·
[Native trace](ui-actions.jsonl.gz) · [Shutdown](shutdown.json) ·
[Binary and source hashes](probe-hashes.txt)

## Reproduce the scoped probe

From a checkout of the source with the evidence files available:

```sh
probe=artifacts/p8-native/harness
evidence=pancake/docs/p8-desktop-evidence
mkdir -p "$probe/src"
cp "$evidence/harness-Cargo.toml.txt" "$probe/Cargo.toml"
cp "$evidence/harness-Cargo.lock.txt" "$probe/Cargo.lock"
cp "$evidence/harness-lib.rs.txt" "$probe/src/lib.rs"
cp "$evidence/harness-main.rs.txt" "$probe/src/main.rs"
cargo +1.100.0 test --locked --manifest-path "$probe/Cargo.toml" --features native --lib
cargo +1.100.0 clippy --locked --manifest-path "$probe/Cargo.toml" --features native --lib
cargo +1.100.0 build --locked --manifest-path "$probe/Cargo.toml" --features native
export PYTHONPATH="$PWD/pancake-conformance/src"
flock -x "/tmp/pancake-conformance-desktop-$(id -u).lock" \
  "$UV_PROJECT_ENVIRONMENT/bin/python" "$evidence/native-probe.py.txt" \
  artifacts/n8 "$probe/target/debug/pancake-native-probe"
```

Use the pinned conformance Python environment with Pillow and the existing
P7 private desktop prerequisites. Xvfb, Openbox and xdotool must be on PATH.
AT-SPI was enabled on the test session's D-Bus by the P7 Openbox wrapper. Use
a new short artifacts path to keep the private Unix socket path within its
length limit. [Compiled scope](build.txt)

The native product recent-folder and source-context cases still need the
Slint controller. macOS and Windows execution was unverified. The observed
Linux host used X11. The isolated service probe supplies no product case
passes or package credit.
