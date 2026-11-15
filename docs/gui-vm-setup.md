# Isolated macOS GUI test VM

The GUI VM backend runs the same native Accessibility, keyboard, pointer, and
file-panel scenarios in a separate macOS desktop. The host launches no VM viewer
when visibility is disabled. Host keyboard, pointer, clipboard, audio, and user
preferences are not test inputs.

## Prerequisites

Use an Apple Silicon Mac with hardware virtualization, enough disk space for a
macOS image and its test environment, and a logged-in user. Install Tart with:

```sh
brew install openai/tools/tart
```

If Homebrew 7 rejects Tart's untrusted `softnet` dependency, trust that formula
and repeat the installation:

```sh
brew trust --formula openai/tools/softnet
brew install openai/tools/tart
```

The supported image is `ghcr.io/cirruslabs/macos-tahoe-base:latest`. Its download
is approximately 27 GB compressed at the time of setup. Tart's
[quick start](https://tart.run/quick-start/) documents image cloning and the
initial `admin` / `admin` guest credentials. The
[image templates](https://github.com/cirruslabs/macos-image-templates) distinguish
base images, which contain Homebrew and command-line tools, from vanilla images.

## Create the dedicated guest

Do not reuse a personal desktop VM. These commands create a dedicated test
machine without overwriting another image or pruning existing Tart storage:

```sh
TART_NO_AUTO_PRUNE=1 tart clone \
  ghcr.io/cirruslabs/macos-tahoe-base:latest chimpstackr-conformance
tart set chimpstackr-conformance --cpu 4 --memory 8192 --display 1440x1000 \
  --no-display-refit --disk-size 80
tart run chimpstackr-conformance --no-graphics --no-clipboard --no-audio
```

Use the default NAT network. Do not expose guest SSH or VNC to the internet. Find
the guest address with `tart ip chimpstackr-conformance --wait 60`, then connect
with `ssh admin@GUEST_IP`. Use a dedicated SSH key; do not copy a personal private
key into the guest. Keep the private key and known-hosts file outside version
control. The reference descriptor uses `~/.ssh/chimpstackr-conformance`.
Create that key only if the path is free, and authorize its public key in the
guest through the initial password-authenticated SSH connection. The descriptor
contains these transport fields:

```toml
[gui_vm]
name = "chimpstackr-conformance"
ssh_user = "admin"
guest_root = "/Users/admin/stack-conformance"
ssh_identity = "~/.ssh/chimpstackr-conformance"
```

Tart's `--no-graphics` flag prevents a host window. Automated runs must not
invoke Screen Sharing, `open vnc://...`, or a host desktop automation client.
For one-time manual setup, you can choose to open the dedicated guest with
`tart run chimpstackr-conformance --no-clipboard --no-audio`, grant permissions
inside that guest, shut it down, and resume normal headless runs. The test CLI's
`--gui-vm-visible` flag is also an explicit visibility opt-in.

Our setup used a programmatic guest-only VNC client instead. That client is a
provisioning tool, not a committed test dependency. Tart can expose its VNC
endpoint without opening a viewer:

```sh
tart run chimpstackr-conformance --no-graphics --vnc-experimental \
  --no-clipboard --no-audio
```

Its output contains a loopback VNC URL and temporary password. Treat that URL as
a credential. Connect with a programmatic VNC client that sends events only to
that endpoint. Tart's
[run implementation](https://github.com/openai/tart/blob/main/Sources/tart/Commands/Run.swift)
prints the URL instead of opening a host viewer when `--no-graphics` is set.

## Guest runtime and desktop

The guest must have an unlocked Aqua session for `admin`. SSH alone is not a GUI
session. Check the console user and GUI launch domain inside the guest:

```sh
stat -f '%Su' /dev/console
launchctl print gui/$(id -u) >/dev/null
xcrun swiftc --version
```

Install `uv` and Python 3.12 inside the guest:

```sh
/opt/homebrew/bin/brew install uv
/opt/homebrew/bin/uv python install 3.12
```

See the official [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/)
and [managed Python guide](https://docs.astral.sh/uv/guides/install-python/).
The VM transport copies the project
and initialized ChimpStackr submodule to `/Users/admin/stack-conformance`, then
runs `uv sync --locked --extra chimpstackr`. GUI jobs run through an `admin`
LaunchAgent in `gui/<uid>`, not as a root daemon or an SSH background process.

The reference runtime is pinned to the official Qt for Python CI revision
`b920c23932946fddc7bb8969f221dd7cf1d7a8d4`. Its PySide package version is
`6.12.0a1.dev1794566397`, but its loaded Qt version is **6.12.1**. This build
contains the [upstream native Accessibility ownership fix](https://github.com/qt/qtbase/commit/b74d6cb3c5e8418602494ae549b60839d88ef858).
Released Qt 6.12.0 invalidates table interfaces; older Qt 6.9.0 also has native
Accessibility lifetime faults. Neither is a valid substitute for the locked
runtime. The two official wheel URLs and SHA256 hashes are in `uv.lock`.
Archive those runtime wheels with the lockfile and frozen baseline when making
a long-term reference. An unavailable artifact is an environment error; do not
silently select another runtime. This constraint belongs to the ChimpStackr
reference adapter, not to portable conformance cases or future target apps.

Run provenance records both PySide and actual Qt versions. Each GUI call also
retains `shutdown.json`; an unexpected process failure, including a crash during
finalization, fails the case even when its earlier pixel checks succeeded.

## Guest permissions

The native helper needs Accessibility and permission to post input events.
Keyboard input also needs Automation access to **System Events**. Screen
Recording permits screenshots of the target window. Grant missing permissions
in the guest's **System Settings → Privacy & Security**, through the guest VNC
connection. Permission dialogs and actions must never target the host desktop.

Do not disable SIP, alter TCC databases, or add global permission bypasses. The
upstream base-image builder already provisions some remote automation grants;
those image defaults are distinct from changes made during this setup. Its
[permission setup script](https://github.com/cirruslabs/macos-image-templates/blob/main/scripts/update-tcc-database.sh)
is documented for provenance, not an instruction to execute it. Validate the
actual test job's permissions after launch; grants to SSH do not prove that an
independent LaunchAgent has access.

If macOS shows a new permission request after the source-hashed helper changes,
grant it through the guest UI and rerun the failed case. A denied permission
must fail clearly; it must not become a passing test.

## Verification and limits

Before accepting a guest setup, verify native file import, native Save dialogs,
stack/export pixel parity, viewer navigation, zoom, pan, and comparison-divider
input inside the guest. Record guest runtime, Aqua session, native trust, input
posting permission, and target-window screenshots with the run artifacts.

Capture the host frontmost application PID immediately before and after the
guest dialog and gesture checks using a read-only API. This provides evidence
that guest input did not activate a host application. Host activity can change
that PID independently; record the actual observations.

Virtual macOS hardware does not imply a usable OpenCL device. Report unavailable
GPU cases explicitly as unsupported. CPU cases must still execute and pass.
Physical host GPU checks are separate evidence. Linux and Windows guests are
outside the current backend contract.

Coverage from host and guest is merged only after the adapter verifies target
source content and revision. Guest source paths are mapped to the matching host
source before line and branch union; target files remain one denominator.
Never-imported files remain in the report. Host physical-GPU CLI coverage can
contribute valid source coverage, but it cannot certify an unsupported guest GUI
GPU scenario. Result summaries preserve that unsupported status separately from
passed cases.

Use the VM backend for conformance runs. The following leaves the guest running
for repeated checks and keeps its window hidden:

```sh
uv run --extra chimpstackr stack-conformance run --gui-vm --gui-vm-persist \
  --suite interface --output artifacts/interface-vm
```

`--gui-vm-visible` is opt-in. Omitting `--gui-vm-persist` stops the dedicated VM after the run, including a
VM that was already running. Visibility controls startup only; reusing a running
VM does not open or close its existing viewer. Keep this dedicated VM headless. A guest run uses `--no-gui-vm` internally to prevent recursive
VM startup. Do not run host-native GUI smoke tests while using the host desktop.

## Provisioned reference guest

The setup on 2026-11-15 used Tart 2.41.1 and image digest
`sha256:65c3133a633fda8753cf1f71f2d55727792d534a2125b0032466563dcc8e58fd`.
The guest reports macOS 26.6.2 (25G83), arm64, `admin` UID 501, Swift 6.3.3,
uv 0.13.8, and managed Python 3.12.16. Its configuration is four CPUs, 8192 MB
RAM, an 80 GB disk, and a 1440 × 1000 point display.

The upstream image initially reported SIP disabled. Before conformance
validation, setup raised security through the guest's Recovery UI:

1. Shut down the guest, then start Tart with `--recovery --no-graphics
   --vnc-experimental --no-clipboard --no-audio`.
2. Through guest VNC, select **Options → Continue → Utilities → Terminal**.
3. Run `csrutil enable`, accept full boot security, and authenticate as the guest
   administrator.
4. Shut down Recovery and start the normal guest with the headless flags.
5. Verify `csrutil status` reports `System Integrity Protection status: enabled.`

No host security settings or TCC database entries were changed. Setup evidence
is kept under the ignored `artifacts/vm-setup` directory; its VNC credentials and
SSH provisioning files must not be committed.


Guest permission provisioning required enabling **python3.12** under
Accessibility and allowing its request to control **System Events**, using only
guest VNC. The actual LaunchAgent/native-helper trust response then reported
`trusted=true` and `post_event_access=true`. The guest's restored display mode
initially differed from its Tart configuration; selecting **1440 × 1000
(Default)** in guest Displays produced the expected 2880 × 2000 Retina frame.

The first clean boundary run passed native file/folder import, TIFF Save and
host CLI pixel parity, and viewer zoom, pan, comparison-divider, and navigation.
Its host frontmost application remained Chrome PID 20157 immediately before and
after those guest actions. The corresponding report is
`artifacts/vm-native-boundaries/report.json`; read-only focus captures are in
`artifacts/vm-setup/host-frontmost-startup-after.json` and
`artifacts/vm-setup/host-frontmost-native-after.json`.


Native GUI cases execute in the guest. Any GUI-versus-CLI image comparison is
recorded as pending until artifacts return to the host. The host verifies source
provenance and input/output hashes, runs the configured CLI on the same fixture
bytes, and checks pixel parity before reporting a final pass. This preserves
physical-host CLI/device coverage without running headless cases in the VM.

Screen Recording also required enabling **python3.12** through the guest privacy
pane. A fresh Aqua LaunchAgent then captured the actual ChimpStackr window
through the suite's `MacOSUISession.screenshot` method. The target-window PNG
and successful native trust result are recorded as
`artifacts/vm-setup/target-window.png` and
`artifacts/vm-setup/screenshot-result.json`. The setup LaunchAgent was unloaded
and its target/helper processes were reaped before handing the VM back to the
normal runner.


## Target synchronization boundary

The current transport requires both the target descriptor and its Git source
checkout to be inside this project workspace. It copies the suite, descriptors,
lockfile, and tracked target files, plus a Git bundle for target provenance.
It does not copy host virtual environments, SSH credentials, or arbitrary build
outputs.

A future compiled target must have its guest binary and runtime dependencies
installed before the run. Configure the GUI command to that guest executable,
and keep its matching Git source checkout in the workspace for provenance.
The backend does not build, sign, package, or install arbitrary language targets.
It runs the configured application against the same native interface contract.
