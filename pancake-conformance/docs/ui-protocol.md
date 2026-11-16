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

## Adapter boundary

An optional launch adapter may isolate user settings, attach stable semantic
identifiers after normal construction, expose read-only viewer observations,
and instrument native worker entry points. These hooks must preserve original
arguments, results, exceptions, and application behavior. They must not invoke
business operations for cases or replace native controls.

Framework-specific mechanics, identifier mappings, source-specific limitations,
and hook regression tests live in adapters. An application may instead publish
the identifiers and observations directly in its own UI toolkit.

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
