# P8 debug product replay

Two unchanged GUI cases ran on the clean product snapshot
`8f1da27b65c2138768d2b118ee7701501368c2ca` with the exact supplied debug CLI
and GUI. Both failed and zero were unsupported. The test used Slint's
`winit-software` renderer on a private Xvfb/Openbox/AT-SPI desktop under
Ubuntu 24.04.5 x86-64. The frozen suite reported both case executions complete.
These are failure receipts. The supplied binaries, lock and descriptor are bound
to the digests below. [Raw report](report.json.gz) · [Provenance](provenance.json) ·
[JUnit](junit.xml) · [Inputs](inputs.sha256)

- `interface.import.recent-folders` opened native `AXMenuItem` rows, asked
  for replacement, preserved frames after cancellation, replaced the sources
  after confirmation and invoked Clear Menu. The immediate next physical
  click on the workspace File control published no menu. This matches the
  integrated diagnostic failure to reopen a native panel immediately after
  a prior native modal closes. [Native trace](recent-actions.jsonl.gz)
- `interface.sprint.frame-context` opened the real source menu and
  activated Show in File Manager. Thunar showed the fixture source directory
  and the native driver observed that Pancake lost focus. Thunar covered
  the View control. The attempted physical click landed inside the file
  manager and could not refocus Pancake. [Screen capture](reveal-occlusion.png) ·
  [Native trace](frame-context-actions.jsonl.gz)

After staging and digest-checking the supplied binaries under
`pancake/target/debug`, the command used the frozen suite with the P7 private
desktop prerequisites and the existing lock:

```sh
export PYTHONPATH="$PWD/pancake-conformance/src"
export SLINT_BACKEND=winit-software
"$UV_PROJECT_ENVIRONMENT/bin/python" -m pancake_conformance run --no-coverage \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --cli-command '["./target/debug/pancake-cli"]' \
  --gui-command '["./target/debug/pancake-gui"]' \
  --case interface.import.recent-folders --case interface.sprint.frame-context \
  --output artifacts/d8
```
