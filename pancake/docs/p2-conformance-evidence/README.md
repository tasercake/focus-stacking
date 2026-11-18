# P2 conformance evidence

## First integrated host run

The 2026-11-18 locked release at `18c17b6f1dd2ff2a15ccea985fe430ac1eb7a666`
ran the 109 frozen P1 and P2 host cases. The suite completed with exit 1.

| Selection | Passed | Failed | Unsupported |
|---|---:|---:|---:|
| P1 regression | 25 | 0 | 0 |
| P2 | 78 | 6 | 0 |
| Total | 103 | 6 | 0 |

The independent worktree checked out the exact clean source revision and
copied the job integration agent's locked release. The source and staged
executable SHA-256 matched before the run. [Hardware and hashes](18c17b6-execution.txt)
and [raw provenance](18c17b6-provenance.json).

The release build ran from `pancake/` under Rust 1.100.0. The artifact owner
used these build flags. [Locked build transcript](18c17b6-release.log).

```sh
CARGO_BUILD_JOBS=4 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
  RUSTC_WRAPPER=/tmp/pancake-tools/bin/pancake-rust-cache \
  cargo +1.100.0 build --release --locked -p pancake-cli
```

Run from the workspace root with a new output path and private XDG runtime
directory. The unchanged descriptor pins CPU defaults and supplies explicit
GPU flags where the oracle calls for them.

```sh
adapter=pancake-conformance/src/pancake_conformance/adapters/pancake
args=()
while IFS= read -r case_id; do
    args+=(--case "$case_id")
done < <(jq -r '.cases[] | select(.primary_milestone | test("^P[12]$")) | .id' \
    "$adapter/case-roadmap.json")
export XDG_RUNTIME_DIR=$(mktemp -d)
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/nvidia_icd.json
env -u DISPLAY -u WAYLAND_DISPLAY -u DBUS_SESSION_BUS_ADDRESS -u XDG_SESSION_TYPE \
  -u PANCAKE_RUNTIME uv run --project pancake-conformance --frozen \
  pancake-conformance run --target "$adapter/pancake.toml" "${args[@]}" \
  --no-coverage --output artifacts/pancake-conformance/p2-18c17b6-host
```

All 25 P1 cases passed the same independent diagnostic checks used for P1.
P2 rejection diagnostics identify the missing input pattern, undecodable
file, missing export parent or unsupported format. The 30 corrupt-later
cases each preserved the seeded export bytes and emitted no completion or
fallback event. Completed calls in passing cases recorded 37 CPU completions
and 13 physical RTX 3090 Vulkan completions. Three CPU and three GPU calls
completed in the six failing cases, where the output shape assertion failed.

[Original report](18c17b6-report.json.gz),
[actual completion events](18c17b6-completion-events.json.gz) and
[independent accounting and checked diagnostics](18c17b6-accounting.json).

## Remaining P2 regression

The six IDs `algorithms.coverage.gray_array.{hybrid,weighted_average,depth_map}.{cpu,gpu}`
load 2D float32 NumPy images, complete the requested stacks and export RGB PNG
with observed shape `(129, 193, 3)`. The frozen oracle requires a single-plane
PNG of shape `(129, 193)`. All native grayscale container cases in this
selection passed their separate RGB output oracles.

Use `--case algorithms.coverage.gray_array.weighted_average.cpu` with the
same frozen suite command for a one-case replay. A direct two-frame reproduction
uses arrays made by the Python below. The observed PNG was RGB with shape
`(17, 19, 3)`. [Reproduction hashes and result](18c17b6-gray-array-repro.txt).

```python
import numpy as np

first = np.tile(np.arange(19, dtype=np.float32) * 12, (17, 1))
np.save("a.npy", first)
np.save("b.npy", np.roll(first, 1, axis=1))
```

```sh
./pancake/target/release/pancake-cli --cpu --method weighted_average \
  --input a.npy b.npy --output result.png
```
