# Semantic native UI contract

The interface suite preserves workflows and observable results: import sources,
choose processing options, run a stack, inspect or compare images, change the
view, export pixels, retain results, persist preferences, cancel work, and
recover from file errors. It does not require a particular arrangement of
panels, control classes, menu labels, status messages, shortcuts, or zoom step.
Optional features are declared in the target's `capabilities`; unsupported
cases are reported as `unsupported`, not passed.

## Native boundary

`CaseContext.open_ui()` wraps the native macOS or Linux session in `SemanticUI`. The
wrapper maps declarative selectors and input sequences to operating-system
Accessibility, keyboard, and pointer operations. It does not call target
business methods. Action completion is not evidence of application success:
cases separately wait for observed UI state or validate exported files.

A target can publish the semantic identifiers directly, or provide `[ui]`
mappings in its descriptor. For example, this implementation uses a dropdown
instead of method radio cards and displays different words:

```toml
capabilities = ["cli", "native_gui", "preferences"]

[ui.controls]
method = { id = "fusion-dropdown" }
alignment = { id = "motion-dropdown" }
"stack.start" = { id = "combine-button" }

[ui.choices]
method = { hybrid = "Detail blend", laplacian = "Pyramid" }
alignment = { off = "Disabled", translation = "Move only" }

[ui.actions]
"method.hybrid" = [{ select = "method", value = "hybrid" }]
"method.laplacian" = [{ select = "method", value = "laplacian" }]
"settings.open" = [{ key = ",", modifiers = ["control"] }]

[ui.observations]
selected_method = { selector = { id = "fusion-dropdown" }, attribute = "value", values = { "Detail blend" = "hybrid", "Pyramid" = "laplacian" } }
frame_count = { count = { role = "AXButton" }, within = { id = "source-grid" } }

[ui.settings_choices]
"settings.theme" = ["light", "dark"]
```

Provide mappings for every action, choice, and observation used by selected
cases. Unknown or missing controls fail explicitly. The mapping changes only
presentation details. Raw rendered text remains available, and no action
writes a successful postcondition into the accessibility snapshot.

## Mapping forms

`[ui.controls]` maps semantic identifiers to native selector dictionaries.
Selectors can use `id`, `role`, `title`, or an observed `path`. Collection
selectors can use `within`, an item `role`, and `index`, or a `text_pattern`
matching text on the item or its descendants. The returned click target is a
real path from a fresh native snapshot. Thus a source grid, nested outline, or
flat list can expose the same count and selection behavior.

`[ui.actions]` maps an action to an ordered array of native input steps. Steps
are `click`, `select` with `value`, or `key` with optional `modifiers`. Clicks
use native Accessibility activation by default; `physical = true` requests
pointer input and can include `button`, `count`, and relative `position`.
Unmapped actions activate their semantic identifier directly. Linux uses XTest
pointer clicks for visible controls because synchronous AT-SPI actions can block
inside modal Qt dialogs. Both paths still require separately observed results.
See [Linux setup](linux.md) for desktop isolation and platform overrides.

`[ui.choices]` maps canonical option values to displayed strings. The wrapper
maps actual observed choices back to their canonical values. It never assumes
that sending a selection made it succeed.

`[ui.observations]` reads real accessibility data. A rule can select an
attribute, read a JSON field, extract a regular-expression group, translate a
value, count matching descendants, or identify one selected control. A count
with `direct = true` counts only direct children of the declared container.
Radio-card and dropdown observations can therefore expose the same selected
method without requiring the same control structure. Viewer observations use
read-only accessible metadata for image presence, scale, center, comparison
state, divider position, and fit mode. Source/result selection observations
must describe the currently displayed item, not the last requested action.

`[ui.initial_values]` may declare target-specific numerical settings needed for
CLI/GUI parity. Only controls actually exposed for the selected method are
edited. `[ui.advanced_values]` declares the setting exercised by the optional
advanced-control case. These are target data, not global engine defaults.

## Feature scope

The core workflow uses semantic processing and export controls. Optional
capabilities include `preferences`, `about`, `lightroom`, `layout_panels`,
`advanced_controls`, `recent_folders`, `batch_export`, `source_context`,
`viewport_export`, `retained_results`, `manual_crop`, `pause_resume`, and
`gpu_preference`. Declaring a feature commits the target to its observable
case, while leaving its presentation and implementation free. Backend evidence
has a separate [diagnostic contract](diagnostics.md).

Automatic updater preferences, release feeds, version ordering, downloads,
installation, and delivery mechanisms are outside application conformance.
Readable Lightroom integration status is optional and never installs or starts
another application.

## GUI verification

Run live GUI tests only inside a configured macOS VM. Native pytest smoke
cases require both `--gui-vm` and an explicit `--target PATH`; otherwise they
skip. Use `--gui-vm-persist` to retain the guest. Driver unit tests use fake
native sessions or construct events without sending host input.

The guest needs a logged-in Aqua session, Xcode command-line tools,
Accessibility permission, and Automation permission for System Events. Native
file dialogs always navigate to a verified case-owned directory; remembered
locations are not accepted. Screenshots, accessibility trees, action traces,
and exported files remain evidence. Guest exports remain pending until host
CLI pixel comparisons complete. See [VM setup](gui-vm-setup.md).


Native selectors may use `any_of` for alternative observable presentations, such
as a modal sheet or a dialog window. Exact native identifiers take precedence
over broader role selectors. Matching never creates a UI state or calls target
business logic. `empty_when` in a count observation requires the declared native
empty-state text; an absent container alone does not imply zero images. Large
virtualized lists use a declared `source_total` observation from an actual UI
counter or status label rather than assuming all rows appear in the AX tree.

A popup action acknowledgement does not prove that a menu opened. Selection
requires a visible option and the committed resulting value. If AXShowMenu
explicitly leaves a control collapsed, the driver may try its advertised
AXPress action once. Expanded but unreadable popups still fail; no option index
or postcondition is inferred. Pan checks first establish a zoom above observed
fit scale. Disabled recent-history placeholders are read as published state,
without treating their zero native bounds as clickable geometry.
