# P8 X11 chooser handoff diagnostics

The unchanged Linux native import case reproduced the lost immediate Open
click on two clean integrated GUI builds on Ubuntu 24.04.5 x86-64. Both
runs were on the private Xvfb/Openbox/AT-SPI desktop and completed 0/1.
[8d306e9 observed run](c14-provenance.json) · [Raw result](c14-report.json.gz) ·
[e643089 native-owner run](c15-provenance.json) · [Raw result](c15-report.json.gz)

The passive C14 wrapper launches read-only XInput and X11 property observers
on the case-owned display, then execs the supplied Pancake binary under the
same PID. The first Open press and the second Open press both reached the
server at x=384, y=170 over X11 frame window 2097466. Pancake's managed Slint
XID 4194307 regained both the window-manager active state and X11 keyboard
focus 0.40 seconds before the second click. The second press and release
occurred, with no successor GTK dialog. These observations place the defect
after the X server accepted the pointer input and restored focus. They do
not determine whether winit received the individual events.
[Native monotonic trace](c14-x11.jsonl.gz)

C15 tested safe GTK transient ownership via the actual Slint X11 raw window
handle together with explicit GTK modal release before hide. The integrated
build completed. The unchanged case still timed out when reopening the
chooser, so this candidate supplies no passing evidence.
[Build](c15-build.txt)

To launch the diagnostic, use the original frozen suite and its private
desktop. Stage both retained probe scripts side by side as `observe.py` and
`with-observer.sh`, mark the latter executable, and select the same
application binary as the target command. Set an ignored output directory
in `PANCAKE_X11_OBSERVATIONS`. The wrapper refuses execution outside a
case-owned X11 session. [Observer](observe.py.txt) · [Wrapper](with-observer.sh.txt)
