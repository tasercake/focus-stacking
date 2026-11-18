# Headless image input regression

On 2026-11-18 a clean checkout at `2608589f6a1fca495b9dab0cefe0a3d4a230f002`
built and tested the reordered NumPy header and bounded RAW input changes.
The checkout used the same Ubuntu 24.04.5 x86-64 and Rust 1.100.0 host documented
in the [P6 assurance receipt](../../p6-assurance-evidence/README.md).
The headless run unset `DISPLAY` and `WAYLAND_DISPLAY`. The raw
[report](report.json.gz), [provenance](provenance.json) and
[release hashes](release.sha256) preserve the matching revision, contract,
descriptor and lock. The [diagnostics](diagnostics.txt) identify all seven
malformed-data process calls across the five decoder rejection cases.

| Check | Result |
|---|---|
| `bash scripts/check.sh fast` from `pancake/` | Exit 0. [Log](fast.log.gz) |
| `bash scripts/check.sh deps` from `pancake/` | Exit 0. [Log](deps.log.gz) |
| `cargo test --locked -p pancake --test cpu_npy --test cpu_image_io` | Exit 0. 16 tests passed with zero skips. [Log](codecs.log.gz) |
| `cargo build --release --locked -p pancake-cli` | Exit 0. [Log](release.log.gz) |
| Frozen `pancake-conformance run` using the unmodified Pancake descriptor and `--no-coverage` | 25/25 mapped P1 IDs passed, no unsupported or failed IDs. |

The conformance invocation selected the exact IDs with
`jq -r '.cases[] | select(.primary_milestone == "P1") | .id' "$adapter/case-roadmap.json"`.
Each ID was supplied as a separate `--case` argument. The referenced decoder
diagnostics confirm genuine source or size failures. Full host, platform and
performance acceptance retain their own results at the appropriate revisions.
