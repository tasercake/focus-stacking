# Linux package evidence

## Integrated Linux package candidate `12f2151`

The locked workspace release built both executables on Ubuntu 24.04.5 x86-64
from `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f` using Rust 1.100.0. The
candidate passed `check.sh fast`, `check.sh deps`, and four package-tool
regressions. [Build and verification summary](12f2151/summary.json).

The local package is at
`artifacts/pancake-packages/linux-12f2151/pancake_0.1.0_amd64.deb`.
It is 69,404,690 bytes with SHA-256
`0d5a428309fedb6de8ed741c9ba79bb75463ac219972b87c931bbac702b02123`.
APT simulated the local installation. Rootless extraction verified the
binaries, native dynamic libraries, desktop entry, CLI help and 1,036
dependency notices, including both licenses from the pinned vendored
`oneshot`. The inventory identifies 27 of 583 selected packages whose
locked sources supplied no recognized notice. The packaging record is
informational for redistribution review.
[Package verification](12f2151/package-verification.json).
[Dependency-notice inventory](12f2151/notice-inventory.json.gz).

The strict verifier accepted all 376 frozen case IDs using the package
executables. The host lane passed 341/341. Isolated GUI passed 34/34,
including all 20 P7 and 14 P8 interface IDs. The physical GUI case passed
on the RTX 3090 at PCI `0000:01:00.0` (driver `580.178.04`) using actual
wgpu Vulkan. [Strict aggregate ledger](12f2151/linux-ledger.json.gz).

The embedded Slint compiler call, its single toolkit import, locked Slint
and Rowan records, and pinned Rowan tree match the earlier packaged runtime
witness at `5216ba4`. The exact Linux CLI production graph remains
independent of the UI graph. [Slint source and dependency comparison](12f2151/slint-source-boundary.log.gz).

`artifacts/p9-12f2151/{h,g,p}` retains the raw case directories, private desktop
logs and provenance. Both GUI lanes used a short private Xvfb path for the
native accessibility socket. The original paths remain in the byte-for-byte
receipts, and the verifier read the directories after relocation to the
workspace. [Host receipt](12f2151/host-receipt.json.gz).
[Isolated GUI receipt](12f2151/isolated-gui-receipt.json.gz).
[Physical GPU GUI receipt](12f2151/physical-gpu-receipt.json.gz).
[Verifier stdout](12f2151/verify.log).

The package remains provisional while required Apple execution, retained
platform build and release decisions, complete assurance and the unchanged
performance targets remain open. See the [implementation plan](../implementation-plan.md).

## Integrated Linux package candidate `5216ba4`

The Linux x86-64 Debian package for
`5216ba4227e14033483a21bb5eca1c6c168ef840` is retained under
`artifacts/pancake-packages/linux-5216ba4/pancake_0.1.0_amd64.deb`. It is
69,262,768 bytes with SHA-256
`f3caa23753ff1a670d895b33bff58d26ab6d48aa58f961e5bab731d985371ed1`.
The producer compiled at `bc19261` and reran the locked release build after
sealing `5216ba4`. The sealed build reused the same executable bytes. The
application sources, manifests and Cargo.lock are identical across those
revisions. The recorded differences concern assurance, tooling or
documentation. [Build source witness](5216ba4/source-stage.json).
[Sealed release build](5216ba4/sealed-release-build.log).

The archive's two executables match those used for the conformance runs.
APT's local simulation resolves the package and `ldd` resolves the extracted
executables' linked dependencies. The extracted desktop entry launches the
correct GUI and forwards both spaced and non-BMP file paths unchanged.
The packaged GUI opens on a private desktop while a benign
`std-widgets.slint` file is present in its working directory. Its file-open
trace records no reads of that file. [Desktop entry receipt](5216ba4/desktop-entry-receipt.json).
[Packaged interpreter receipt](5216ba4/slint-receipt.json).

The strict aggregate verifier passed with all 376 frozen cases accounted for.
The host lane passed 341/341 using the extracted package. Isolated native GUI
passed 34/34 using software presentation. The separate physical-GPU GUI lane
passed 1/1 on the RTX 3090 at `0000:01:00.0`, and actual completion telemetry
identifies wgpu Vulkan. All three lanes attest to the same application source,
descriptor, locks, package executable bytes and hardware inventory. The local
raw records stay under `artifacts/p9-5216ba4`. The candidate stays provisional
pending the remaining platform, integrated assurance and frozen performance
conditions. [Host receipt](5216ba4/host-receipt.json).
[Isolated GUI receipt](5216ba4/isolated-gui-receipt.json).
[Physical GPU GUI receipt](5216ba4/physical-gpu-receipt.json).
[Aggregate ledger](5216ba4/linux-ledger.json.gz).

## P7 release checkpoint `0859deb`

Pancake's locked Linux x86-64 release CLI and GUI produced a 69,265,760 byte
Debian package on Ubuntu 24.04. The archive SHA-256 is
`d5cfb3d07f0452b56d690e633cb77af47841b8326ed4b4ea4eccec595b1d7df4`.
The workspace retains the archive under
`artifacts/pancake-packages/linux-0859deb/pancake_0.1.0_amd64.deb`. Both extracted
binaries match the release build hashes, their linked libraries resolve, and
the desktop entry validates. APT simulated installation with the installed
dependency set. The native installation test used rootless extraction into a
temporary directory and executed the resulting binaries. A separate private
desktop run launched the packaged desktop entry through `gio`, observed its
Pancake window and checked the live process arguments. Both file paths arrived
as individual arguments, including a path with spaces and non-BMP Unicode.

The unchanged conformance suite passed all five selected smoke cases against
the actual extracted CLI and GUI. Headless help, glob processing, desktop
startup, weighted-average stacking and close with unsaved work all executed.
The independently decoded GUI and CLI TIFFs also had identical file hashes.
The packaged interpreter opened real windows from both test directories and
did not read the local test widget file.

This checkpoint predates subsequent GUI and registration changes. Its receipts
apply to the exact `0859deb` binary, lock and descriptor. Final platform and
full-case acceptance need a combined revision and fresh matching runs.

- [Package and smoke receipt](0859deb/receipt.json)
- [Packaged desktop entry launch and argv](0859deb/desktop-entry-receipt.json)
- [Native launch and Slint source-path check](0859deb/slint-receipt.json)
- [Frozen conformance stdout](0859deb/conformance.log)
- [Frozen conformance report](0859deb/report.json.gz)
- [Frozen runner provenance](0859deb/provenance.json.gz)
- [APT simulation](0859deb/apt-simulation.txt)
