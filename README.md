# Focus-stacking research

Research and tools for building a high-quality macro focus-stacking benchmark.

- [Bokehforge](bokehforge/README.md): `uv` project with dataset download and processing CLI, source configuration, tests, and documentation.
- [Pancake-conformance](pancake-conformance/README.md): independent focus-stacking application conformance suite.
- [Pancake](pancake/README.md): future focus-stacking application rewrite in `pancake/pancake/`.
- [Research](research/README.md): artifact reviews, algorithms, measurement design, and dataset evidence.
- `submodules/`: upstream focus-stacking implementations.
- `datasets/`: generated native and standardized data; logs and runtime files stay in `datasets/.bokehforge/`.

Run Bokehforge from the repository root:

```sh
uv run --project bokehforge --frozen bokehforge data download
uv run --project bokehforge --frozen bokehforge data process
uv run --project bokehforge --frozen pytest bokehforge/tests
```

Source policy and exact source pins live in [bokehforge/config/data/](bokehforge/config/data/), outside the disposable data directory. Default native download budget remains 2 GiB; LSFD is disabled.

## Application conformance

The [Pancake-conformance suite](pancake-conformance/README.md) owns the
`pancake-conformance` CLI, portable application contracts, tests, configuration, and
documentation. It is independent of the future application rewrite. ChimpStackr
remains the reference target at `submodules/ChimpStackr`.

```sh
git submodule update --init submodules/ChimpStackr
uv sync --locked --project pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference
uv run --locked --project pancake-conformance/src/pancake_conformance/adapters/chimpstackr_reference pancake-conformance list
```

On Linux, use the [isolated native desktop](pancake-conformance/docs/linux.md). On macOS, configure the [dedicated headless macOS guest](pancake-conformance/docs/gui-vm-setup.md) once. GUI
cases then leave the host desktop untouched; CLI, algorithms and physical-device
cases stay on the host. Pancake-conformance's pytest suite includes native smoke cases,
so pass `--gui-vm --gui-vm-persist` while using the host desktop.

See the [conformance guide](pancake-conformance/docs/conformance.md) for target descriptors, immutable
references, case selection, artifacts and raw/scoped coverage.

The historical [verification record](pancake-conformance/docs/verification.md) reports the full passing replay,
coverage totals, runtime pins and remaining gaps.
