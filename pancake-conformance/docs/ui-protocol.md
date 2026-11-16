# Native macOS interface conformance

Interface scenarios use the operating system boundary. They do not import the
application, Qt, PySide, widget classes, algorithm functions, or export helpers.
The generic driver launches the configured GUI command, then controls its PID
through macOS Accessibility, native pointer events, and System Events keyboard
input. A different implementation can use the same scenarios by publishing the
same semantic identifiers and read-only observations.

## Requirements

Run in an unlocked, logged-in macOS desktop session with Xcode command-line tools
(`xcrun swiftc`). Allow Accessibility access for the application or terminal that
starts the CLI. Also allow its Automation access to **System Events**. macOS
requires this permission for reliable keyboard input into native file panels.
Permission failures fail the run; they are not converted into passing skips.

Screen Recording permission permits target-window screenshots on failure. The
suite does not capture the whole desktop. Accessibility trees and action traces
remain available when screenshots cannot be captured. Run only one interface
suite at a time: keyboard and pointer input share the desktop.

`native_macos.swift` compiles on demand into a source-hashed temporary cache. No
Appium server, browser, downloaded fixture set, or application rebuild is needed.

## Boundary

`MacOSUISession` exposes `snapshot`, `node`, `click`, `select`, `key`, `text`,
`edit`, `drag`, `scroll`, `wait`, and native file-panel operations. The underlying
transport is JSON Lines over standard input and output. Requests name a PID,
command, and accessibility selector; responses contain `ok` and either `result`
or `error`. Every request and response is recorded in the case directory.

Selectors use a stable `id`, optionally an accessibility role, or a path from a
fresh accessibility snapshot. Native lists can repeat their identifier on rows
and columns; list assertions therefore qualify the identifier with `AXList`.
Snapshots omit the system Apple menu and the virtualized contents of native file
browsers. Native file panels are controlled through their real controls and
keyboard navigation, without walking unrelated directory contents.

Pointer input uses coordinates relative to the identified control. Accessibility
press actions activate semantic radio choices, native menu commands, and controls
that are partially clipped by the existing application layout. Both routes use public
operating-system input APIs. Popup selection opens through an advertised public
Accessibility action when available, otherwise a pointer click. Options must be
readable before native pointer selection; selection then requires the exact
committed value and popup dismissal. An invalid native accessibility tree fails
instead of inferring an invisible choice. Selecting an
already committed value sends no input. Scenarios never call an application
operation.

## Reference-only hooks

`adapters/chimpstackr_ui.py` is a launch adapter outside the submodule. It starts
the unchanged `src.run.main()` entry point. Its hooks are limited to:

1. Isolating QSettings in a case-owned INI profile; initial preference values are
   applied only when missing, so restart and fresh-profile tests remain valid.
2. Assigning stable accessibility identifiers after the four normal window
   constructors return. Arguments, return values and exceptions are preserved;
   each original constructor runs once. No application-wide Python event filter
   observes unrelated or retiring Qt objects.
3. Providing a native accessible canvas for the existing custom image viewer.
   Its description is a read-only JSON object with `has_image`, `zoom`, `center`,
   `split`, `compare`, and `fit`. These are observations, not setters or commands.
4. Installing the optional coverage/diagnostics observer on Qt-created worker
   thread entry boundaries. The original worker method runs unchanged, with its
   return value, exceptions, and prior profiling/tracing callbacks preserved.
5. Accepting an optional update-feed URL through a declared endpoint hook. The
   original network client and update UI run unchanged against a generated local
   service. Rendered release-note text is exposed as read-only accessibility
   description when the native text browser omits its value.

The fourth hook is needed because Qt creates native threads outside Python's
`threading.Thread` bootstrap. The reference observer supplies the same external
execution-diagnostics schema used by CLI/device scenarios. A future target must
publish that schema through its own instrumentation; its tests need not know
Python or Qt.

The reference submodule contains no source edits for these hooks. The adapter
contains all framework-specific knowledge. A port supplies another launch
adapter or implements the same identifiers directly in its native toolkit.

Unreadable-image preview messages do not currently have stable native AX
publication: hover status tips can replace the normal status text, and the
empty-result CPU path reports cancellation rather than a worker-error dialog.
This UI recovery sequence is a coverage gap, not a passing case. Real corrupt,
partial and oversized input rejection remains covered through CLI tests.

## Semantic identifiers

| Group | Examples |
|---|---|
| Workspace and input | `import.files`, `frames`, `results`, `status`, `device` |
| Processing controls | `stack.start`, `stack.pause`, `stack.stop`, `method.hybrid`, `alignment`, `autocrop`, `parameter.kernel` |
| Viewer | `viewer`, `zoom`, `mode.view`, `mode.compare` |
| Export | `export.start`, `export.format`, `export.depth`, `export.quality`, `export.compression`, `export.confirm` |
| Preferences | `settings.theme`, `settings.device_mode`, `settings.gpu`, `settings.auto_updates`, `settings.prereleases`, `settings.lightroom.status` |
| Updates | `updates.notes`, `updates.auto`, `updates.skip`, `updates.later`, `updates.download` |

The complete reference mapping is `IDENTIFIER_CONTRACT` in the adapter. macOS
native window wrappers may not expose a widget's identifier; readiness checks
use actual native window roles and dialog child identifiers instead.

## Native file-panel safety

Cocoa remembers native file-panel locations outside QSettings. Changing `HOME`
does not isolate those locations. The suite never accepts that remembered
destination. It navigates to an existing case-owned directory using the actual
Go to Folder sheet, checks the exact entered absolute path, and verifies the
native path menu's complete directory ancestry. Matching only the leaf directory
name is insufficient: another run can have the same case name.

The Save panel is accepted only after that verification and after checking the
filename. Existing files are not overwritten. Export checks then independently
decode the file at the requested sandbox path. Native input files also must be
inside the case directory.

The current reference menu can consume Command+A inside native panels as its
Select All Frames command. The driver therefore clears the native path editor
through its public AX value interface, then sends real text input before
accepting navigation. It does not replace the file chooser or provide a fake
path response.

## Coverage and limits

The interface suite covers method selection, every stacking method with CLI
pixel parity, all export formats and depths, native file/folder dialogs,
duplicate suppression, removal, RAW preview/export, alignment/crop, comparison
divider, zoom/pan/navigation, panel visibility, preferences/restart isolation,
unsaved-work prompts, pause/resume/cancel/reuse, and GUI-selected GPU execution.
VM mode runs this same native transport inside the guest. Its physical-GPU GUI
case remains explicitly unsupported; host device cases validate the actual GPU.

Updater preferences and readable Lightroom setup state are tested without
network downloads, installing/updating/removing user applications, or operating
Lightroom itself. Packaged-application installers, live update application,
physical touch/trackpad gestures, and other operating systems remain separate
coverage gaps. The coverage report includes their owning source files instead
of excluding them to inflate the result.
