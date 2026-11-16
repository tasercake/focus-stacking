# Dedicated macOS GUI guest

Use a dedicated Tart macOS VM to keep interface input away from the host desktop.
The same native Accessibility driver runs in its logged-in Aqua session.
CLI, algorithms, and physical-device tests stay on the host.

## Automatic setup

`--gui-vm` can provision a missing dedicated guest. See [bootstrap](gui-vm-bootstrap.md).
The steps below also support existing custom guests.

## Provision once

1. Install Tart on a native Apple Silicon macOS host. Create a dedicated arm64
   macOS guest; record its name in `[gui_vm]`.
2. Create a non-root desktop user, enable Remote Login, configure SSH key access,
   and sign in to its Aqua session. Keep that session unlocked and available.
3. Install uv and Xcode command-line tools inside the guest. Match the Python
   version declared by the target's runtime environment.
4. Grant Accessibility and Automation access for System Events to the guest
   test process. Screen Recording permits target-window failure screenshots.
5. Configure a dedicated guest directory and identity in the target descriptor:

```toml
[gui_vm]
name = "focus-conformance"
ssh_user = "admin"
guest_root = "/Users/admin/focus-conformance"
ssh_identity = "~/.ssh/focus-conformance"
python = "3.12.16"
```

`guest_root` must be a dedicated directory beneath that user's home. Transport
replaces suite-owned source and target checkout directories there. Do not use a
personal project directory. The VM lease permits one suite invocation at a time.

## Run

```sh
pancake-conformance run --target /absolute/path/to/target.toml --gui-vm
```

Guest boot is headless by default, with no host clipboard or audio passthrough.
`--gui-vm-visible` shows its window. `--gui-vm-persist` keeps it running afterward;
otherwise the runner stops it. Missing SSH, Aqua login, tools, permissions, or
native arm64 support fail preflight. There is no host GUI fallback.

Transport preserves workspace-relative paths, target Git objects and tags,
locks, runtime manifests, suite source, and target descriptor. It excludes host
credentials, unrelated projects, environments, and bytecode. A declared
`[runtime] project` selects the guest dependency environment; otherwise the suite
project is used. Adapter-specific dependencies belong to that runtime project.

Guest results retain logs, source fingerprints, action traces, exports, and
coverage shards. Pending GUI pixel comparisons finish through host CLI calls.
Physical-GPU GUI cases remain explicitly unsupported in a guest. Adapter setup
notes record implementation-specific runtime pins and prior VM validation.
