# Linux native conformance

The Linux runner executes the same behavior cases as macOS. CLI, component and
physical GPU work stays on the host. GUI cases automatically use a private Xvfb
X11 display, Openbox window manager and D-Bus session, including a private AT-SPI
accessibility bus. No host desktop input or accessibility session is used. The
runner stops its desktop processes on exit and retains desktop and driver logs.

## Setup (Ubuntu/Debian)

Install native desktop dependencies once:

```sh
sudo apt-get install xvfb openbox xdotool x11-utils dbus-x11 python3-gi \
  gir1.2-atspi-2.0 gir1.2-gtk-3.0 at-spi2-core ocl-icd-libopencl1 libegl1 libopengl0 \
  libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0
```

The AT-SPI transport uses `/usr/bin/python3` with the distribution's GI bindings,
not the target's Python interpreter. Override `PANCAKE_ATSPI_PYTHON` if the system
Python lives elsewhere. Application libraries stay in the adapter's locked uv
environment. Use a current uv version supporting its cross-platform lock.

Install and run the selected target using its adapter's setup instructions. From
the suite directory, the general commands are:

```sh
uv run --locked --project path/to/adapter pancake-conformance run --target target.toml
uv run --locked --project path/to/adapter pytest tests path/to/adapter/tests \
  --gui-desktop --target target.toml
```

`--gui-vm` continues to select the macOS Tart transport and requires an Apple
Silicon Mac. Do not supply it on Linux. GUI cases on Linux always create their
own desktop; a pre-existing `$DISPLAY` is not used. The private session selects
the generic Qt platform theme so file dialogs don't inherit host GTK/portal
settings. They remain real file dialogs operated through accessibility and input.
Source-context cases also require a working `xdg-open` file manager (for example
Thunar). GPU cases require an actual OpenCL GPU and working driver; requests
that fall back to CPU cannot satisfy those assertions.

Portable driver and orchestration tests run on both operating systems in CI.
The two native smoke tests run with `--gui-desktop --target ...` on Linux or
`--gui-vm --target ...` on macOS.

## Platform presentation mappings

Target descriptors can override presentation or environment details with
`[platforms.linux]` and `[platforms.darwin]`. Overrides recursively merge tables;
scalar and array values replace the corresponding base value. Behavior cases
and validators stay shared. For example:

```toml
[platforms.linux.ui.controls]
"frames.reveal" = { role = "AXMenuItem", title = "Show in File Manager" }
```

The native driver normalizes AT-SPI roles to the existing transport vocabulary
(`AXButton`, `AXWindow`, etc.). These names describe the wire schema; Linux
observations still come from the operating system's AT-SPI tree, and actions
use AT-SPI actions or XTest keyboard/pointer events. No target business methods
are invoked by the driver.
