# T50 Hybrid matched-job preflight

The initial preparation reviewed retained evidence and wrote a quiet launch
plan during the D150 campaign. After D150 ended, the sealed candidate and
reference were staged and all 52 TIFFs were generated for read-only reuse
by the viewer A/B and this benchmark. One complete diagnostic pair
established matching stationary RGB16 geometry. The candidate took 3.084×
the reference time and produced different measured detail transfer.
The full timing schedule was closed. [Diagnostic evidence](pair-001/README.md)

[Materialized input receipt](stage-001/verified-stage.json) ·
[Raw verification](stage-001/materialization.json.gz) ·
[Prepared candidate and reference provenance](stage-001/prepared-provenance.json.gz) ·
[Package, reference, generator and resource records](stage-001/stage-observations.tar.gz) ·
[Checksums](stage-001/SHA256SUMS)

The Linux materializer took 229.215 seconds on logical CPU 15, with nice
+12, idle I/O priority, one decode worker and numeric thread limits of one.
Maximum RSS was 83,676 KiB. Available disk space at its start and finish was
141,441,183,744 B and 123,378,569,216 B during concurrent build activity.
Available host memory was 44,954,508 KiB and 46,841,696 KiB at the same points.
All 52 file records, codec-decoded pixel hashes and independent zlib-decoded
hashes match the frozen receipt. The normal user service manager applied
exactly 28 GiB of host memory and zero swap for a scope probe. The
[staged launch command](stage-001/launch-pair.sh.txt) uses that same control.
Benchmarks and the viewer release the shared inputs before authenticated
cleanup.

## Exact inputs and prior closure

The generated 6000×4000 RGB16 recipe uses seed `20261117`, 256×256
tiles, fifty distinct focus positions, a sharp RGB16 truth, and a categorical
depth truth. The frozen receipt SHA-256 is
`8881a4968bb95f5a911b040a6ebc9635a9cbdc5a759ac0443605de33f700849c`.
Its 52 file hashes and 52 independent decoded-pixel hashes matched a complete
Linux rematerialization. The CLI consumes only `focus_000.tif` through
`focus_049.tif`, in receipt order. The two independently generated TIFFs are
reserved for review. [Recipe](../../../t50-generated/README.md) ·
[Linux verification](../../../../pancake/docs/p2-corpus-evidence/t50-linux-verification.json)

The full `5e10244` Hybrid pass was on the RTX 3090 through Vulkan, with all
50 reference-to-source transforms exactly identity and the agreed one-pixel
symmetric crop. Its independent 3998×5998 RGB16 output MAE was 843.33/65535
against generated truth across the entire centered overlap. All 50 focus
regions remained visible, with vertical second-difference variance ratios
from 0.8667 to 0.8918. That one job completed within its 360-second deadline.
The receipt has no timing or resource measurement. The sealed release
`12f2151` includes newer Hybrid fusion and registration code and needs its own
result and comparison. [Previous full T50 result](../registration-recheck/README.md)

## Run the first pair when the host is quiet

Use the packaged `12f2151` default CLI with Vulkan and the locked ChimpStackr
`ab7a927` OpenCL reference on the same physical RTX 3090, OpenCL index 0 and
candidate index 0. The runner validates UUID
`GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac`, PCI `0000:01:00.0`,
and real GPU completion. Use identical affinity and worker limits.
The frozen profile is `T50.hybrid.gpu` with similarity alignment, first
reference, kernel 6, eight levels, scale 6, zero slabs and overlap,
automatic crop, TIFF16 and both automatic settings and quality reporting
disabled. Keep application and runtime caches inside the fresh run directory.

1. Wait for D150 and any viewer work to finish. Reserve a quiet window with
   the normal desktop load recorded. Create an isolated checkout of
   `12f2151c8a198b5209c8f4d506dbd17fd9aaa74f`. Stage its pinned, clean reference
   submodule and its existing frozen reference environment. The benchmark
   expects the interpreter at the descriptor directory's `.venv/bin/python`.
   Keep the frozen generator environment separate from the reference runtime.
2. Verify the sealed Debian archive and extract it into owned scratch.
   Place the verified extracted binary at the descriptor's
   `pancake/target/release/pancake-cli` without installing the package. The
   expected package SHA-256 is
   `0d5a428309fedb6de8ed741c9ba79bb75463ac219972b87c931bbac702b02123`.
   The exact CLI SHA-256 is
   `32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055`,
   the Cargo lock SHA-256 is
   `f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`,
   and the candidate descriptor SHA-256 is
   `84e2bd96f121395051cc8d626a06ebece7367171d59018158439d9ca2aaa10ac`.
   Preserve the package receipt and locked-build command. The runner's
   build receipt binds the stage's absolute executable path, executable
   hash, source commit, lock hash and descriptor hash. [Package seal](../../../../pancake/docs/p9-linux-package-evidence/12f2151/package-verification.json)
3. Materialize full T50 with the frozen recipe and 15 GiB generator reserve.
   Keep the ownership and materialization receipts throughout the two jobs.
   Require at least 40 GiB host `MemAvailable` and 8 GiB free on the selected
   GPU before starting the pair. Use a 28 GiB memory scope with swap disabled
   for these diagnostics. This leaves 12 GiB of initial host headroom.
   Confirm the local user service manager applies the limits before launching
   the jobs. The scope limits host allocation and does not cap GPU residency.
   Preserve an abort and its evidence if time, memory, decode, or device
   validation fails.
4. Run the [one-pair command](paired-diagnostic.py.txt) shown below. It uses
   the unchanged runner and captures the real argv, workload metadata,
   timeout, runtime, shape, output hashes, and 8 ms nominal RSS/GPU traces.
   Before any timing campaign, inspect both outputs against the same immutable
   truth and all 50 known focus strips. Each TIFF should decode independently
   as genuine RGB16. A different crop, false motion, CPU fallback, allocation
   failure, or unreadable export stops the timing campaign. Preserve the
   original evidence and inspect the cause before attempting another run.

Run from the staged `12f2151` checkout. The variables point at fresh owned
scratch, the sealed package, the saved P9 producer summary, this evidence
directory, and the existing frozen generator interpreter.

```bash
set -euo pipefail
release_source=$PWD
ref_project=pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
ref_python="$release_source/$ref_project/.venv/bin/python"
frozen=qualification/t50-generated/evidence/native-t50-receipt.json
check_sha() { printf '%s  %s\n' "$1" "$2" | sha256sum --check -; }
check_sha 0d5a428309fedb6de8ed741c9ba79bb75463ac219972b87c931bbac702b02123 "$sealed_deb"
check_sha 8881a4968bb95f5a911b040a6ebc9635a9cbdc5a759ac0443605de33f700849c "$frozen"
check_sha 58bb68533311c48696a3a844d80eef2f37a3c1f39649305948c838b7002663dc pancake/docs/performance-targets.json
test "$(git rev-parse HEAD)" = 12f2151c8a198b5209c8f4d506dbd17fd9aaa74f
test -z "$(git status --porcelain)"
mkdir "$scratch"
dpkg-deb --extract "$sealed_deb" "$scratch/package"
install -D -m 755 "$scratch/package/usr/bin/pancake-cli" pancake/target/release/pancake-cli
check_sha 32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055 pancake/target/release/pancake-cli
check_sha f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc pancake/Cargo.lock
check_sha 84e2bd96f121395051cc8d626a06ebece7367171d59018158439d9ca2aaa10ac pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml
python3 - "$sealed_producer_summary" "$scratch/build-receipt.json" <<'PY'
import json
import sys
from pathlib import Path

producer = json.loads(Path(sys.argv[1]).read_text())
assert producer["source_commit"] == "12f2151c8a198b5209c8f4d506dbd17fd9aaa74f"
record = {
    "commit": producer["source_commit"],
    "lock_sha256": producer["cargo_lock_sha256"],
    "descriptor_sha256": producer["descriptor_sha256"],
    "component": "cli",
    "executable": str(Path("pancake/target/release/pancake-cli").resolve()),
    "binary_sha256": producer["binaries"]["pancake-cli"]["sha256"],
    "build": producer["release_build_command"],
    "producer": producer,
}
Path(sys.argv[2]).write_text(json.dumps(record, indent=2) + "\n")
PY
"$generator_python" qualification/t50-generated/t50_generated.py \
  --materialize-from "$frozen" --output "$scratch/inputs" \
  --receipt "$scratch/materialization.json"
awk '$1=="MemAvailable:" { enough=$2>=41943040 } END { exit !enough }' /proc/meminfo
nvidia-smi -i GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac \
  --query-gpu=memory.free --format=csv,noheader,nounits |
  awk '{ enough=$1>=8192 } END { exit !enough }'
export PYTHONPATH="$release_source/pancake-conformance/src:$release_source/qualification/p10-performance"
env -u DISPLAY -u WAYLAND_DISPLAY systemd-run --user --scope --quiet \
  -p MemoryMax=28G -p MemorySwapMax=0 \
  "$ref_python" "$preflight_evidence/paired-diagnostic.py.txt" \
  --input-root "$scratch/inputs" --build-receipt "$scratch/build-receipt.json" \
  --truth-review "$preflight_evidence/../registration-recheck/scale-recheck.py.txt" \
  --output "$scratch/diagnostic"
```

The first pair deliberately stops before any 34-job schedule. When both
outputs have been reviewed, the unchanged `p10.py run` command selects
`--runtime wgpu-vulkan --profile T50.hybrid.gpu`, the same `--gpu-uuid`,
both index flags set to 0, the existing build receipt and input root,
`--threads` equal to the permitted affinity width, a fresh `--output`, and
`--timeout 900`. Its schedule contains 17 jobs per target plus one backend
diagnostic per target. A different runtime or affinity after a resource abort
requires a new, explicitly identified profile. CPU-versus-CPU is separately
valid with the same 50 RGB16 TIFFs and unchanged quality settings.

Review and hash the two diagnostic TIFFs before removing them. After all
consumers finish, invoke `t50_generated.py --cleanup-from "$scratch/materialization.json"
--output "$scratch/inputs" --receipt "$scratch/cleanup.json"` using the same
generator environment. That command rechecks all 52 file hashes and
authenticates the directory before deleting the generated TIFFs. Preserve
the receipts and remove the diagnostic's owned output, cache and package
extraction after review.

## Resource estimates and open checks

| Resource | Read-only estimate and basis |
|---|---|
| Corpus space | Exact Linux payload 2,775,174,405 B. Generator preflight 3,067,213,930 B plus 16,106,127,360 B reserve. The full runner holds at most two output pairs, around 576 MB at 144 MB per uncompressed TIFF, plus package, traces and caches. Start with at least 24 GiB free. |
| Candidate memory | 288 MB per packed RGB f32 allocation. The `12f2151` Hybrid constructor budgets about 2.944 GB for levels plus scratch under a 3 GiB fusion share of the 4 GiB logical job cap. A device page still must fit a packed RGB frame. The logical cap excludes allocator reserve and measured RSS/VRAM. |
| Reference GPU memory | Pinned ChimpStackr estimates 15.5 packed f32 frames for 24 MP aligned Hybrid, about 4.464 GB including its headroom. Its explicit GPU mode bypasses the Auto memory test and can still fall back if OpenCL allocation or execution fails. User-space memory limits apply only to the host. |
| Host RSS | Plan around several GiB for candidate and up to 12 GiB for reference until measured. On the smaller 5088×3392 R50 CPU functional diagnostic with four allowed CPUs, observed lower-bound process high-water marks were 2.51 and 8.28 GiB respectively. The full T50 OpenCL loader can have up to eight workers, a lookahead frame, and retained reference data. Those mechanisms and temporary precision conversion can raise peaks. |
| Time | Plan a few minutes for 52-image generation, verification and hashing, then up to 30 minutes for a first 900-second-per-job pair before review. The prior full Vulkan candidate completed within six minutes. A tentative 1–6 minutes per job gives 0.6–3.6 hours for the 36-job campaign plus validation. There is no matched T50 timing baseline. Refine the window using the first pair. |

The pinned TIFF reader uses OpenCV unchanged-depth decode. RGB16 enters
the reference Hybrid path as float32 values scaled by `255/65535`. It
exports RGB16 by rounding after multiplication by 257. The OpenCL input
helper decodes high-bit TIFFs twice before using the f32 path, which affects
cost. Source inspection reveals no unconditional 8-bit conversion for
T50 Hybrid. The first real reference export must independently establish
genuine precision and stationary geometry. The reference's transform
confidence policy differs from Pancake's repaired self-repeat check, so
the prior candidate's identity matrices cannot establish reference geometry.

The E9 Vulkan receipt already shows GPU sampling gaps above the frozen
20 ms limit at teardown on this same host. Preserve actual T50 sample gaps
and lower bounds. A complete pair can support a functional decision while
that resource metric remains pending. [Prior resource evidence](../integrated-e9-12f2151/README.md)
