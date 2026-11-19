# Prepared exact 8694b55 T50 diagnostic

Run the unchanged pinned ChimpStackr and exact combined Debian CLI once each with `T50.hybrid.gpu` after R50 completes, the shared T50 owner authenticates its 52 files, the full viewer workload releases the device, and the coordinator grants the exclusive diagnostic slot. Use the stage owner's read-only input lease. The historical 26.7 s reference and 82.4 s candidate complete jobs suggest reserving about two to three minutes for the pair, plus original rehash and decoded review. They do not predict a new warm median. There is no warmup, repeat, method change or retry in this helper.

| Item | Exact requested identity |
| --- | --- |
| Package revision | `8694b555666a1ddf4051e2839bbced4bcc625859` |
| Debian archive | 69,494,350 bytes, SHA-256 `7dbc969e1813bc62aa4df206bb77982e3f7705298f753e12b7a493ae89ce3784` |
| Packaged CLI | 122,279,832 bytes, SHA-256 `e5fa8d2cb31a55071c999a83e35b4c3d31d6c569717b7baca328c16ea7ed4b6f` |
| Cargo lock | `f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc` |
| Reference Git and runtime lock | `ab7a92708269c01c6094729f6cdfaf1415677364`, SHA-256 `fda57ac5eea063aebcc278eb57a90228e6da32fe2d8f67d7025ac367f4b51036` |
| GPU | RTX 3090 `GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac`, index 0 for each API, PCI `0000:01:00.0` |
| Method and order | Reference OpenCL then Pancake wgpu Vulkan, 50 native RGB16 inputs, Hybrid, first-anchor similarity, kernel 6, eight levels, scale 6, no slabs, auto crop and RGB16 TIFF |

The historical launch and the exact 8694 descriptors produce the same options after the input list and output file. The reference uses the frozen interpreter with `-m src.cli`. The candidate uses the exact staged package ELF and `PANCAKE_RUNTIME=wgpu` in its isolated child environment. The R50 camera-specific launcher does not apply. [Package receipt](../../../../pancake/docs/p9-linux-package-evidence/8694b55/package-verification.json) · [Historical launch](../t50-12f2151-preflight/pair-001/raw-pair.tar.gz)

## Stage outside any active measurement

The current source-only stage is `/tmp/pancake-worktrees.t3paqgWM/t50-shared-8694b55`. Use the owner's exact checkout and input path, or an equivalently clean exact checkout that borrows those same inputs. Place the copied [diagnostic helper](diagnostic-pair-8694.py.txt) as `$scratch/diagnostic-pair-8694.py`. A new borrowed directory should contain no source files beyond ignored task artifacts. Leave a previously verified identical package extraction in place.

```bash
workspace=/home/krishna/Documents/focus-stacking
release=/tmp/pancake-worktrees.t3paqgWM/t50-shared-8694b55
profile="$release/pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference"
package="$workspace/artifacts/pancake-packages/linux-8694b55/pancake_0.1.0_amd64.deb"
git -C "$workspace" show c6ecfe1:pancake/docs/p9-linux-package-evidence/8694b55/package-verification.json > "$scratch/package-receipt.json"
printf '%s  %s\n' 7dbc969e1813bc62aa4df206bb77982e3f7705298f753e12b7a493ae89ce3784 "$package" | sha256sum -c
dpkg-deb -x "$package" "$scratch/extracted"
cli="$release/pancake/target/release/pancake-cli"
if [ ! -e "$cli" ]; then
  mkdir -p "$(dirname "$cli")"
  install -m 0555 "$scratch/extracted/usr/bin/pancake-cli" "$cli"
fi
printf '%s  %s\n' e5fa8d2cb31a55071c999a83e35b4c3d31d6c569717b7baca328c16ea7ed4b6f "$cli" | sha256sum -c
# Only if the exact reference checkout is missing. Clone from the existing local object store.
if [ ! -e "$release/submodules/ChimpStackr/.git" ]; then
  git clone --no-checkout --local "$workspace/submodules/ChimpStackr" "$release/submodules/ChimpStackr"
  git -C "$release/submodules/ChimpStackr" switch --detach ab7a92708269c01c6094729f6cdfaf1415677364
fi
uv sync --offline --frozen --python 3.12.12 --project "$profile"
```

Write the `p10._prepared_targets` receipt for the existing executable using the archived release identity. This is package staging and performs no build.

```bash
python3 - "$release" "$scratch/package-receipt.json" "$scratch/build-receipt.json" <<'PY'
from pathlib import Path
import hashlib
import json
import sys

release, proof, output = (Path(value).resolve() for value in sys.argv[1:])
data = json.loads(proof.read_text())
descriptor = release / "pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml"
lock = release / "pancake/Cargo.lock"
cli = release / "pancake/target/release/pancake-cli"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

assert digest(cli) == data["binaries"]["pancake-cli"]["sha256"]
assert digest(lock) == data["cargo_lock_sha256"]
receipt = {
    "commit": data["source_commit"], "lock_sha256": digest(lock),
    "descriptor_sha256": digest(descriptor), "executable": str(cli),
    "binary_sha256": digest(cli), "component": "cli", "package_receipt_sha256": digest(proof),
}
with output.open("x") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
PY
```

The wrapper uses the exact worktree's `p10.py`, builds argv from the frozen profile and adapter, and makes exactly two diagnostic launches, each capped at 900 s. Supply a new output path and the authorized quiet receipt. Use identical common CPU affinity and poller settings for both samples. Optional truth review uses the earlier pinned helper and evaluates the same input set and truth only after both jobs finish.

```bash
git -C "$release" status --short
git -C "$workspace" show 8694b55:qualification/p10-performance/evidence/registration-recheck/scale-recheck.py.txt > "$scratch/truth-review.py"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$release/pancake-conformance/src:$release/qualification/p10-performance"
export OPENBLAS_NUM_THREADS=1
env -u DISPLAY -u WAYLAND_DISPLAY "$profile/.venv/bin/python" "$scratch/diagnostic-pair-8694.py" \\
  --input-root "$authenticated_full_t50" --package "$package" \\
  --package-receipt "$scratch/package-receipt.json" --build-receipt "$scratch/build-receipt.json" \\
  --quiet-receipt "$exclusive_gpu_receipt" --output "$scratch/diagnostic-pair" \\
  --truth-review "$scratch/truth-review.py"
```

The helpers put the OpenCL preflight under the run root, and per-arm cache, launch argv, stderr, stdout, events, sample JSON, resource traces and TIFF under the fresh diagnostic directory. The shared runner captures process-tree RSS via procfs and attributed per-process GPU memory via NVML. Keep the actual acquisition gaps and leave any unqualified peak pending. The helper retains the stages and raw warning counts without making alignment offload a required stage. Cleanup of the shared input set remains with the materializer after all readers release it. Rehash each export before removing it.
