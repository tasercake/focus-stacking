# Immediate viewer commands

The [matched redraw experiment](../p10-viewer-redraw-evidence/README.md)
measured a visible P95 around 41 ms with both binaries. The pinned Fluent
Button starts 150 ms background, border, and text animations when its
states change. Retained-result, view mode, and fit/zoom/navigation
commands all used this component. This created a narrower source-level
hypothesis about unnecessary decorated frames during viewer interaction.

At `9681d09`, a test drove the real embedded workspace through its
offscreen Slint software renderer. Scrolling first changed the displayed
photograph. Moving the pointer to the Fit command then left an active
animation in the window and failed the test.
[Exact failing test](red.log).

At `5f6ce9a`, viewer commands use an immediate-state control styled by
the application's palette. The control keeps its accessible button
identity, enabled and checked state, default action, focus target,
pointer activation, and Space and Return activation. The test passed
after actually clicking Fit, checking that the portrait returned to its
original visible size, then navigating by Tab to the 1:1 command and
activating it with Return. It checks the displayed pixels and an absence
of active decoration at both states. All 16 GUI tests, effective strict
GUI Clippy, formatting, and reviewed source inventory passed.
[Exact CPU checks](green-and-clippy.log.gz).

The physical latency result is pending. The calibrated T50 inputs,
before/after images, color tolerance, event sequence, physical
renderer, and process reducer remain the measurement contract. The
packaged `d6359e1` executable can serve as the unchanged control,
with the production GUI/core, dependency resolution, and conformance
inputs identical to the base `2143eda`. A paired run checks the same
native controls and the original visible image witnesses under both
idle and real numerical load. [Source and protocol hashes](source-and-protocol.txt).
