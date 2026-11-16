# Reference GUI VM bootstrap

See [automatic setup](../../../../../docs/gui-vm-bootstrap.md) for the portable
bootstrap contract. From the repository root:

```sh
adapter=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
uv run --project "$adapter" --locked pancake-conformance run \
  --target "$adapter/chimpstackr.toml" --gui-vm
```

## Verification — 2026-11-16

The final clean-guest replay passed `interface.startup.empty`,
`interface.import.native-dialogs`, and `interface.algorithm.laplacian`, including
host CLI pixel parity. Tart was hidden from the host PATH. Bootstrap used its
verified cached Tart app bundle and cloned a new guest from the pinned image.
The base image was already in Tart's OCI cache; its multi-gigabyte network fetch
was not repeated. An earlier run downloaded and verified the Tart release bundle.

The guest reported SIP enabled, all five permission checks true (Accessibility,
input posting, System Events, screen access, screenshot capture), and a persistent
1440 × 1000 / 2880 × 2000 display mode. A warm run also passed native import and
Laplacian export with CLI pixel parity.

After adapter isolation, use this complete harness command:

```sh
adapter=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
uv run --project "$adapter" --locked pytest pancake-conformance/tests \
  --target "$adapter/chimpstackr.toml" --gui-vm --gui-vm-persist -q
```

Before integration with the concurrent contract refactor, the complete harness
passed **281 tests** in 353.64 seconds. Its native control and weighted-average
export smoke tests ran in the default dedicated VM. Three dependency deprecation
warnings came from vncdotool's VNC authentication implementation.

Bootstrap unit checks cover archive integrity and traversal, the embedded app
profile, concurrent installation, guest ownership, loopback-only VNC, exact OCR
labels, reconnecting frame reads, permission completeness, expected consent
prompts, persistent display verification, Recovery SIP enablement, and early
Tart process failure. No physical-GPU behavior was validated by these GUI runs.

## Integrated adapter and feature-contract verification

After integrating with the current adapter and portable feature-contract layout,
the command above plus the adapter test directory passed **307 tests** in
186.83 seconds. Both native smoke cases ran inside the managed VM; the export
case completed host CLI pixel verification. Two vncdotool authentication
deprecation warnings remained.

The integrated run also verified warm startup after the original temporary run
directory had been removed. Bootstrap restarted the managed guest, retained its
VNC log privately in the cache, and reused that log for the next smoke case.
The old manually provisioned reference VM is not the descriptor's default.
