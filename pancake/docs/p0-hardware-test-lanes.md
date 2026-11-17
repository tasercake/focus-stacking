# P0 hardware and native test-lane audit

Date: 2026-11-17, Asia/Singapore. Source revision: `8fcbc52` (P0 planning
baseline over `00bd137`). Audit worktree: `codex/p0-hardware`.

## Verdict

**P0.02 is blocked on access qualification for the complete promised hardware
matrix.** Local Apple hardware is identified. A later read-only probe verified
the existing Linux x86-64 RTX 3090 host is reachable; its runtime/GUI tools remain
unqualified, and AMD/Intel/Windows access remains unresolved. This is an access
inventory, not a CubeCL runtime pass or an application conformance run.

The plan's previous assertion that the final physical-GPU GUI case requires a
physical Mac is too narrow. The current unchanged suite supports a private Linux
Xvfb desktop with native AT-SPI/XTest input and host physical GPU compute.
A Linux GPU machine is a valid route to `interface.compute.gpu`; no suite change
is needed. Actual Slint accessibility, display/backend integration, and GPU
completion still need qualification on that route.

## Observed local resources

| Resource | Observation | What this establishes |
|---|---|---|
| Host | macOS 26.2, build 25C56; Darwin 25.2.0, arm64; Mac16,7 | A native ARM64 macOS lane is present. |
| CPU | Apple M4 Pro, 14 cores (10 performance + 4 efficiency) | Physical ARM64 CPU identified; native CubeCL CPU execution was not tested by this audit. |
| GPU | Apple M4 Pro, 20 cores; system profiler reports Metal 4 support | Physical Apple GPU identified; neither native CubeCL Metal nor current wgpu execution was tested here. |
| Memory | 51,539,607,552 bytes (48 GiB) | Capacity for local feasibility workloads; this is not a measured application memory budget. |
| Rust | Only `aarch64-apple-darwin` target installed for the default toolchain and pinned 1.100.0 | No installed x86-64 target was found for those toolchains. A cross-build or emulator would not prove execution on physical x86-64 hardware. |
| Xcode | Selected developer directory is `/Applications/Xcode.app/Contents/Developer`; Swift/Clang found there | Native compiler tools are installed. Default SDK-version resolution initially failed; uncached explicit macOS SDK query succeeded with 26.4. |
| uv | 0.12.17 | Local suite/runtime tool exists. Current conformance CI pins 0.13.8; cross-platform lock compatibility must be qualified rather than assumed. |
| Docker | Client/server 29.4.0, active OrbStack context; Linux engine reports aarch64, 14 CPUs, 16,819,834,880 bytes | A responding ARM64 Linux engine exists. No physical NVIDIA/AMD/Intel device or GPU runtime was established. It is not native x86-64 evidence. |

Machine serial numbers, hardware UUIDs, network endpoints, and private-key data
are deliberately excluded from this report.

## Existing virtualization and connection inventory

Tart 2.41.1 reports `chimpstackr-conformance` running, and `pancake-conformance`
stopped. Several stopped bootstrap-validation guests and cached base images
also exist. Both named conformance guests have Darwin configuration and
1440x1000 virtual display configuration. No guest was cloned, booted, stopped,
or sent GUI input by this audit through Tart.

The existing running guest returned an address through `tart ip`, but the
configured identity `~/.ssh/pancake-conformance` does not exist. No SSH connection
was attempted with that absent identity, so login, Aqua session, Accessibility,
Automation, native tools, and source/binary deployment remain unverified.
The running guest belongs to existing work; it must not be repurposed or stopped
without checking its owner and lease.

The inspected `~/.ssh/config` contains an OrbStack include, and the included
configuration declares only the `orb` host. No external x86-64/GPU SSH alias was
found. This is not proof that no remote workstation exists; it means this audit
did not establish its current authorized endpoint or access method.

That initial configuration-only inventory is superseded for NVIDIA access by
the [runtime audit's remote addendum](p0-runtime-feasibility.md): the existing
authorized hostname `krishna-desktop` responded to a BatchMode SSH probe with
Linux 6.8.0-147-generic x86-64, NVIDIA GeForce RTX 3090, driver 580.178.04,
24576 MiB. No installation, compilation, runtime kernel or GUI job was executed.
An absent SSH-config alias was not proof that this host was inaccessible.

**Inventory command side effect:** `orb list` unexpectedly attempted to start
OrbStack's VM and returned `start VM: timed out waiting for VM to start`.
Subsequent read-only Docker queries received engine responses. No conclusion is
drawn about whether the engine was already running or was started by a command.
No further OrbStack machine-start/stop commands were issued. Avoid using that
command as a guaranteed passive preflight in repeat audits.

## Linux physical-GPU GUI route

Source inspection establishes the following route, without executing native
Linux input or an application:

| Owning source | Observed behavior |
|---|---|
| [`cli.py`](../../pancake-conformance/src/pancake_conformance/cli.py#L194) | On Linux, any selected interface cases enter `isolated_desktop` automatically before `run_cases`. There is no physical-GPU capability removal in this branch. |
| [`linux_ui.py`](../../pancake-conformance/src/pancake_conformance/linux_ui.py#L17) | Starts private Xvfb, Openbox, D-Bus, runtime directory and service home; removes inherited accessibility/session addresses; replaces host `DISPLAY`. Processes are reaped on exit. |
| [`macos_ui.py`](../../pancake-conformance/src/pancake_conformance/macos_ui.py#L404) | Linux native session requires the isolated-desktop environment and constructs `LinuxUISession`; it cannot silently attach to a host desktop. |
| [`interface.py`](../../pancake-conformance/src/pancake_conformance/cases/interface.py#L327) | GPU GUI case selects the actual device preference, stacks Hybrid, and requires completed `actual_backend = gpu` diagnostics. It does not prescribe macOS or OpenCL internally. |
| [`runner.py`](../../pancake-conformance/src/pancake_conformance/runner.py#L160) | GPU/physical-GPU capability stripping applies specifically to the macOS VM batch. Its 375+1 limitation is not a universal suite limitation. |

On a provisioned Linux GPU host, run the same descriptor without `--gui-vm`:

```sh
uv run --project pancake-conformance --frozen pancake-conformance run \
  --target pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml \
  --case interface.compute.gpu --no-coverage \
  --output artifacts/pancake-conformance/linux-physical-gui-UNIQUE_RUN_ID
```

Prerequisites are documented in [Linux setup](../../pancake-conformance/docs/linux.md):
Xvfb, Openbox, xdotool, xprop/X11 tools, D-Bus, system Python GI/AT-SPI bindings,
and required native GUI libraries. Source-reveal cases also need a working
`xdg-open` file manager. For Pancake, actual CubeCL/wgpu/CUDA/HIP drivers and
Slint AT-SPI publication must be proven; the reference's OpenCL driver is not
a requirement for Pancake's implementation. Xvfb supplies display isolation,
not physical GPU compute or proof of GPU residency.

The private display setup contains Qt environment variables because it also
supports the current reference. Their presence is not proof that Slint works;
Slint's required renderer/accessibility backend must be tested unchanged through
this generic native driver. An offscreen compute path plus software presentation
can still provide genuine GPU fusion, provided telemetry is truthful.

## Historical evidence versus current access

The committed reference record
[`linux-validation.json`](../../pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference/docs/linux-validation.json)
reports a 2026-11-16 Linux x86-64 reference run: 341 host and 35 GUI cases,
376 passed, zero unsupported, NVIDIA GeForce RTX 3090. It identifies reference
application commit `ab7a92708269c01c6094729f6cdfaf1415677364` and retained report
hashes. It corroborates that the Linux route previously worked for ChimpStackr.

This audit did not replay that run, inspect the machine, or establish its current
connection. The record does not qualify Pancake, CubeCL CUDA, or present hardware
availability. Hosted CI definitions are also not evidence of a physical GPU:
current CI runs Linux/macOS regressions and Linux GUI smoke, but no advertised
NVIDIA/AMD/Intel physical-GPU runner is configured there.

## Minimum prerequisites before P0.02 can pass

| Lane | Available now | Remaining requirement |
|---|---|---|
| Apple ARM64 CPU/wgpu/native Metal | Local physical host identified | Execute shared kernel battery and qualify native runtime/JIT/package behavior. Use dedicated isolation for native input. |
| Native x86-64 + NVIDIA CUDA/wgpu | Existing remote RTX 3090 host reachable; Linux x86-64/device/driver read-only probe passed | Verify native CPU/CUDA/wgpu toolchains, isolated desktop/runtime tools, real kernels and physical-GPU GUI completion. Access alone does not qualify execution. |
| AMD HIP/wgpu | Not established | Physical supported AMD device, ROCm/HIP and wgpu driver, native execution and required desktop access. |
| Intel wgpu | Not established | Physical Intel GPU and supported Vulkan/D3D12 driver, actual kernel execution and package validation. |
| macOS GUI VM | Named guests exist; one unrelated guest is running | Dedicated guest ownership/lease, valid key/login, permissions, native compiler/runtime installation, and reproducible binary preparation. |
| Promised Windows/macOS x86 platform coverage | No native lane established by this audit | Actual supported machine/runner access for builds, runtime execution, native libraries, and packages; cross-compilation alone is insufficient. |

Windows and macOS package lanes remain separate from the Linux full-conformance
route. A Linux 376/376 result would not certify every promised platform/backend.
If the support matrix changes, record the explicit decision before claiming P0
closure; do not silently reduce hardware promises to fit available machines.

## Reproduction and scope

Commands used: `uname -srm`, `sw_vers`, selected `sysctl` fields,
`system_profiler SPHardwareDataType SPDisplaysDataType -json`, `command -v`,
`rustup target list --installed`, `xcode-select -p`, `xcrun --find`,
`xcrun --no-cache --sdk macosx --show-sdk-version`, `tart --version`,
`tart list --format=json`, `tart ip` for the already-running guest, selected
Tart config fields, Docker version/info fields, and SSH Host/Include directives.
No credentials or identities were printed. No network discovery scan, external
SSH login, host native input, application conformance case, or runtime kernel
execution occurred.

Only this report is modified in this worktree. Conformance source and adapters
are unchanged. Verification completed:

- `bash scripts/check.sh all` passed with existing installed tool executables on
  PATH. This worktree owns its generated Cargo outputs; no tool policy was changed.
- `git diff --check` and local Markdown source-link checks passed.
- Linux/macOS x86-64/Windows native checks and Linux address/thread sanitizers
  were not run. No physical GPU runtime or application conformance test was run.

The scaffold has zero application tests and no application coverage percentage.
Its passing local gates are not runtime, hardware, or application conformance
evidence. Guardrail fixtures passed their expected rejection checks.

## Execution update: isolated Linux/NVIDIA lane

The earlier inventory-only status is superseded for the available Linux host.
No host desktop input or host package/driver installation was used. Passwordless
sudo is unavailable; Docker group access and the installed NVIDIA container
runtime provide an isolated qualification route instead.

A task-owned container, `pancake-p0-linux-20261117`, uses existing
`node:22.23.4-bookworm`, image
`sha256:a62a6676db6b68fd1aa959a36ce361a002b74f0936d3e38db544420d9b164990`.
It exposes GPU compute/utility/graphics, with no host display, home, credential or
project mount and no published port. Source copies come from independent P0
worktrees. Existing unrelated containers, applications and VMs remain untouched.

| Qualification | Observed result |
|---|---|
| Native build tools | Isolated Rust 1.100.0 installed; NVIDIA driver 580.178.04 and CUDA 12.5 already exist on host. |
| Private desktop | Xvfb 21.1.7, Openbox 3.6.1, xdotool, private D-Bus, AT-SPI 2.46.0 installed inside container. |
| Actual suite boundary | Unchanged `isolated_desktop` allocated 1440x1000 display, private service home and accessibility bus; all owned desktop processes reaped on exit. Same private environment sees physical RTX 3090 Vulkan. |
| Suite self-tests | 309 passed, two explicit live-GUI smoke skips. These test the harness, not Pancake. |
| Shared blur: native x86-64 CPU | Exact-value/tail/border tests pass using LLVM CPU JIT; identity AMD Ryzen 9 7950X3D, `cpu_x86_64_load-512_f16-chain`. |
| Shared blur: wgpu Vulkan | Same tests pass; adapter NVIDIA GeForce RTX 3090, `DiscreteGpu`, Vulkan. Software fallback is explicitly rejected. |
| Shared blur: native CUDA | Same image definition passes exact-value/border/tail qualification with CUDA runtime enabled. Identity RTX 3090, `ptx_sm86`; existing NVRTC 12.5 libraries copied into container. No driver install. |
| Shared blur: Apple native Metal | Same image definition passes on local M4 Pro through `cubecl/metal-native`, separate from Metal through wgpu. Identity `msl_Apple M4 Pro`. |

Kernel-source/lock revisions and the final post-integration reruns belong to the
[P0 fix report](p0-unblock-report.md). First successful runtime probes are useful
qualification evidence; they do not establish five-method, memory-budget,
Slint-native-input, full-conformance or performance acceptance.

Host PCI inventory exposes one GPU: NVIDIA RTX 3090. Vulkan also reports a
software llvmpipe adapter; it is not AMD/Intel GPU evidence. Existing libvirt
inventory has no VM. No AMD GPU, Intel GPU, Windows or macOS guest login lane has
been established. User confirmed no AMD/Intel/Windows test hosts or runners while independent
work continued; P0.02 remains blocked. These conditions cannot be removed by dependency exceptions.
