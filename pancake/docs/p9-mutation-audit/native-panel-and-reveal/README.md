# Native file panel and source reveal mutation receipts

Two previously missed GUI mutations were caught on
`ad81502d1e9b92c3a0d9a188691e76f12a673db3`, a test-only change based on
`8694b55`. Each one-mutant run selected a byte-identical diff from native
shard 255/256 on `287828a`. Both unmodified baselines passed all 144 CPU
tests across 19 executables, including all 18 GUI tests. Each mutant built
and failed its intended test with exit 101. Both cargo-mutants processes
exited 0 with a `CaughtMutant` record. [Machine-readable receipt](receipt.json).

| Exact archived mutation | Authentic observation |
| --- | --- |
| `desktop_menu::reveal` returns `Ok(())` | A missing source inside an owned temporary directory must return the actual path diagnostic before file-manager dispatch. The mutant reports success. |
| `panel::linux::build` returns three default GTK widgets | A real file-panel request with no display returns the `gtk_init_check` setup error and leaves its caller's completion untouched. The mutant constructs a `Dialog` without initializing GTK and fails in the child. |

The GTK test re-executes its own GUI test binary and selects exactly one
test. It clears the child's environment, preserves a supplied dynamic-linker
path, and sets an owned home and runtime directory. Its X11 backend has
no display or inherited accessibility, session, or Wayland endpoint. The
child executes the regular panel entry point. The parent checks its exit
and verifies that the expected single test ran. GTK's state stays local to
that process. The reveal assertion uses canonicalization before any
platform-specific dispatch, so it requires no file-manager service.

The existing native import case still drives a real chooser through cancel,
reopen, file import and folder import. The existing frame-context case still
invokes Reveal and observes the application lose and recover native focus.
The prior private X11 replay specifically observed Thunar presenting the
fixture directory. Actual selected-item behavior on a file-manager success
path needs that real service or Finder in its native test session. These two
negative assertions qualify the targeted mutations under the workspace CPU
selector. [Existing native behavior evidence](../../p8-product-replay/README.md).

The Linux host used CPUs 0 and 1 with at most two build jobs. Rust was
1.100.0 and cargo-mutants 27.1.0. The locked dependency graph, production
bodies, mutation selectors, and conformance source were preserved. Scoped
strict GUI Clippy passed with the generated dependency policy. Formatting,
reviewed-source validation, and six Miri policy tests also passed. The
archives retain both exact one-mutant invocations, raw baseline and failure
logs, hardware and selection provenance, and the 8.2 GiB owned-target
cleanup. The wider mutation roster and hosted assurance are tracked
separately. [Raw replays](raw-native-replays.tar.gz) · [Checksums](SHA256SUMS).
