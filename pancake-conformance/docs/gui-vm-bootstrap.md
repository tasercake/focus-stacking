# Automatic GUI VM setup

On an Apple Silicon Mac, `--gui-vm` provisions a dedicated Tart guest when the
configured VM does not exist. Git, uv, initialized target submodules, network
access, and enough disk space for the macOS image and runtime are required.
Homebrew, host Xcode, and host desktop permission grants are not required by
bootstrap. The application adapter's host runtime must still be selected with
uv, as documented by that adapter.

From the repository root, select a target descriptor:

```sh
uv run --project pancake-conformance --locked pancake-conformance run \
  --target /absolute/path/to/target.toml --gui-vm
```

Use the adapter's runtime project when it declares one. Its setup guide lists
the corresponding uv command. The `--gui-vm` flag supplies VM prerequisites;
the selected runtime supplies application dependencies.

The first run downloads a checksum-pinned Tart app bundle if Tart is absent,
clones a digest-pinned macOS base image, configures its desktop, creates a
dedicated SSH key, copies the host uv executable, and installs the target's
Python version. The base image supplies Swift command-line tools. Its upstream
SIP setting is restored to enabled through guest Recovery before tests run.

The remembered guest display mode is set persistently to 1440 × 1000 with a
2880 × 2000 Retina framebuffer and checked again after the setup process exits.

Permissions are checked from a LaunchAgent using the same Python environment
as the suite. Bootstrap grants Accessibility and Screen Recording through guest
System Settings and accepts the guest's System Events request, and clears the additional screen-capture
consent dialog before test input begins. It does not
change TCC databases, disable SIP, or send input to the host desktop. The visual
provisioner uses OCR against the pinned English-language guest UI. Unexpected
UI, ambiguous labels, or denied permissions fail setup with retained evidence.

Tart assets, guest ownership records, and SSH keys live in
`~/Library/Caches/pancake-conformance/`. This state is independent of checkout
paths. Tart keeps VM disks in its normal storage. First image download is about
27 GB; the configured guest has an 80 GB virtual disk. Bootstrap disables Tart's
automatic pruning and does not overwrite existing VMs.

Existing VMs without a suite ownership record retain manual configuration and
must meet the usual preflight requirements. Managed guests are reused; interrupted
setup resumes on the next run. If an interrupted setup left the guest in
Recovery, bootstrap restarts it before retrying. `--gui-vm-persist` leaves the
guest running after the run; otherwise it stops. `--gui-vm-visible` opts into a
host VM window; provisioning and Recovery remain headless.

Run evidence includes `vm-preflight.json`, `vm-permissions.json`, and the last
guest provisioning screenshot. Tart logs include temporary VNC credentials and
are created with mode 0600. A private VNC log is retained in the bootstrap cache
so warm runs do not depend on an earlier run directory. Do not publish those logs or bootstrap cache keys.
Guest services remain on Tart's default NAT network; VNC input is restricted to
the loopback endpoint emitted by Tart.

Version pins live in `src/pancake_conformance/vm_bootstrap.py`. Update the Tart
archive checksum and image digest only after repeating the cold-start permission
and GUI smoke checks. The default guest Python version is 3.12.14, available in the tested uv
Python catalog. A target can override it with `gui_vm.python`.
