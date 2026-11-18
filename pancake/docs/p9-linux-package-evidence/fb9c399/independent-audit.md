# Independent audit of the matched Linux package

On 2026-11-18, the frozen adapter verifier independently replayed the
receipt checks under the same suite source as the original run. It read
the original `h`, `g`, and `p` artifacts and the actual Debian archive.
It reported 376/376 and regenerated a byte-identical ledger with SHA-256
`a860fc37375dc68a15783af6e58f3608f53acc7322ae8688e343697407f92c47`.
The 341 host, 34 isolated GUI and one physical GPU GUI cases are disjoint.
The run evidence records an actual RTX 3090 stack completion using wgpu
Vulkan at PCI `0000:01:00.0` with null `fallback_reason`.
[Strict ledger](linux-ledger.json.gz), [application events](physical-gpu-app-events.jsonl.gz).

The audit verified all 39 package evidence checksums. It streamed the
retained `.deb` through `dpkg-deb --fsys-tarfile` and independently hashed
both executables and the included notice inventory. The digests matched
the package receipt and the executables matched `c1e2cac` byte for byte.
The new source digest binds the qualification adapter, while the case
contract, descriptor, and Cargo and uv locks match the earlier run. The
original exact fast, dependency, and package gate exit statuses were all 0.
[Raw capture identities](source-contract-preflight.json), [package hashes](package-verification.json).

The evidence changes were reapplied as docs-only commits to the sanitized
`86d4df2` history. The exclusion check enumerated reachable Git object ID
strings with replacements and grafts disabled and compared their individual
digests to the excluded ID digest. It did not read the excluded object's
contents. The original source had 7,943 reachable objects and the sorted ID
list matched the established root digest. The sanitized base and both
evidence commits passed the same exclusion check. The 41-file native About
manifest also verified, and its strict comparator retained exit 1.
[Original source ancestry](clean-ancestry.json),
[About comparator](../../p9-cpu-assurance-evidence/fb9c399/native-about-target/live/ordinary-comparator.status).

From the exact suite checkout, use the existing artifact paths and a fresh
output file for an offline receipt verification.

```sh
uv run --project pancake-conformance --frozen --no-sync python -m \
  pancake_conformance.adapters.pancake.release_ledger verify \
  --host "$audit_root/artifacts/p9-fb9c399/h" \
  --isolated-gui "$audit_root/artifacts/p9-fb9c399/g" \
  --physical-gpu-gui "$audit_root/artifacts/p9-fb9c399/p" \
  --package "$audit_root/artifacts/pancake-packages/linux-fb9c399" \
  --output "$fresh_output"
```
