# P8 asynchronous native dialogs and menus

Exact native component source `9ec334dda83db9e8719f3da84cf091367f6e6e7c`.
Built and checked with Rust 1.100.0, GTK 3.24.41 and ATK 2.52.0 on Ubuntu
24.04.5 x86-64. The standalone probe uses the production Linux panel and
popup modules. The product's Slint controller migration is a separate
integration step. [Dependency lock](harness-Cargo.lock.txt) ·
[Clippy](clippy.txt) · [Build](build.txt) · [Binary and input hashes](inputs.sha256)

The exact first integrated product replay `8f1da27` reproduced the failure
to reopen a menu after its preceding modal action.
[Product failure evidence](../p8-product-replay/README.md)

The private Xvfb/AT-SPI run completed native Open Cancel, immediate Open,
accepted a Unicode PNG, selected its Unicode folder, and selected a Unicode
save path. The probe wrote a marker to the native-chosen save path and
verified the original PNG was unchanged. It selected an actual Recent
row, cleared the folder history, immediately reopened File and observed
the disabled empty row. It also revealed the source in Thunar and closed
the probe cleanly. The host label was read while the same native chooser or
popup stayed open, confirming the launch returned before the native
response. The fixture is a desktop service probe and supplies no product
case passes. [Panel outcomes](panels.json) · [Native menu observations](menus.json)
· [Physical actions and snapshots](ui-actions.jsonl.gz) · [Shutdown](shutdown.json)

Run from the repository root with the P7 private desktop tools on PATH and
the frozen conformance Python environment selected.

```sh
evidence=pancake/docs/p8-async-native
probe=artifacts/npa/harness
mkdir -p "$probe/src"
for file in Cargo.toml Cargo.lock; do
  cp "$evidence/harness-$file.txt" "$probe/$file"
done
for file in lib.rs gtk_probe.rs main.rs; do
  cp "$evidence/harness-$file.txt" "$probe/src/$file"
done
cargo +1.100.0 clippy --locked --manifest-path "$probe/Cargo.toml" --features native --lib
cargo +1.100.0 build --locked --manifest-path "$probe/Cargo.toml" --features native
export PYTHONPATH="$PWD/pancake-conformance/src"
flock -n -x "/tmp/pancake-conformance-desktop-$(id -u).lock" \
  "$UV_PROJECT_ENVIRONMENT/bin/python" "$evidence/native-probe.py.txt" \
  artifacts/a8 "$probe/target/debug/pancake-native-probe"
```
