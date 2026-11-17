# P0.02 dedicated macOS guest access

Observed 2026-11-17, 08:01:13–08:04:36 UTC, from the independent `p0-patches`
worktree. No application binary or GUI conformance case was executed.

## Result

The existing stopped `pancake-conformance` Tart guest is reachable with its
existing suite-managed SSH key. The missing `~/.ssh/pancake-conformance` file is
not an access blocker for this managed route. The unchanged suite bootstrap
recognizes its ownership record and selects
`~/Library/Caches/pancake-conformance/keys/pancake-conformance` before waiting
for SSH. No key was created, copied, printed, or installed by this task.

| Check | Actual observation |
| --- | --- |
| Initial ownership/state | Dedicated guest stopped; existing suite ownership record and dedicated managed key present. Unrelated `chimpstackr-conformance` running. |
| Resource configuration | 4 vCPUs, 8 GiB RAM, configured display 1440×1000. These resources were reserved only during the bounded boot/check interval. Actual rendered framebuffer was not measured. |
| Lease | Acquired the unchanged suite's `TartGuiVM._acquire_lease()` flock before boot; held through cleanup, then released. |
| Authentication | Exactly one public-key SSH attempt, using the unchanged suite SSH argument builder and existing dedicated key. Succeeded as non-root `admin`, UID 501. No password attempt or credential loop. |
| Session | Console user `admin`; live `launchctl print gui/501` domain. This proves an Aqua session exists, not that a Pancake window was operated. |
| Native platform | `Darwin arm64`, macOS 26.6.2, build 25G83. SIP enabled. |
| Executed native tools | uv 0.12.17, Apple Swift 6.3.3, arm64 macOS target. |
| Existing runtimes | Managed Python 3.12.14 path and suite/reference-adapter `.venv/bin/python` paths exist. Their Python versions/dependency locks were not re-executed or reconciled in this check. |
| Current permission observation | `CGPreflightScreenCaptureAccess` returned true for the SSH-launched probe. This does not qualify a new LaunchAgent/Pancake process identity. |
| Prior permission evidence | Existing guest `.bootstrap/permissions.json` records screen capture, AX trust/post-event access, automation and screenshots true. Record is older; current AX/Automation/LaunchAgent identity was not requalified. No native helper was found in the SSH process's temporary cache directory. |
| Final state | This task stopped only the guest it started. `pancake-conformance` stopped; unrelated `chimpstackr-conformance` still running. No host GUI input or permission changes. |

## Commands and boundary

The check used the unchanged suite lease and SSH APIs directly, without calling
full `prepare()`, which can provision permissions or synchronize repositories.
After confirming the dedicated guest was stopped, it launched:

```sh
tart run pancake-conformance --no-graphics --no-clipboard --no-audio
```

It obtained only that guest's address with `tart ip pancake-conformance`, allowed
eight seconds for boot services, then issued one authenticated SSH command.
That command ran read-only native checks: `uname -s -m`, `sw_vers`, console-user
`stat`, `launchctl print gui/501`, uv/Swift versions, `csrutil status`, runtime
path checks and non-prompting screen-capture preflight. It read the existing
permission JSON without applying grants or sending input. Cleanup used the
suite's `close()` route and rechecked both named VM states.

No guest clone, image download, package installation, source synchronization,
password guessing, Recovery boot, host desktop control, or host TCC change was
performed. Tart output was retained only in an ignored mode-0600 private log;
its contents are not published. The task respected the unrelated guest's state.

Machine-readable observations:
[`p0-guest-access-evidence.json`](p0-guest-access-evidence.json).
Unchanged suite documentation:
[`../../pancake-conformance/docs/gui-vm-bootstrap.md`](../../pancake-conformance/docs/gui-vm-bootstrap.md)
and [`../../pancake-conformance/docs/gui-vm-setup.md`](../../pancake-conformance/docs/gui-vm-setup.md).

## Remaining qualification

Dedicated guest SSH/Aqua/native-tool access is demonstrated. Before claiming a
GUI lane pass, run the declared runtime and native helper in the actual suite
LaunchAgent identity, verify current Accessibility/Automation/screen permissions,
prepare the real Pancake binary and adapter, and execute the unchanged cases.
A macOS virtual guest does not qualify physical-GPU execution or native
NVIDIA/AMD/Intel/Windows lanes.
