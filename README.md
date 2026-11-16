# Focus-stacking research

Research and tools for building a high-quality macro focus-stacking benchmark.

- [Bokehforge](bokehforge/README.md): `uv` project with dataset download and processing CLI, source configuration, tests, and documentation.
- [Pancake](pancake/README.md): isolated focus-stacking project, starting with a standalone conformance suite and thin ChimpStackr reference adapter.
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

The [Pancake project](pancake/README.md) owns the `pancake` CLI, portable
application contracts, tests, configuration, and documentation. ChimpStackr
remains the reference target at `submodules/ChimpStackr`.

```sh
git submodule update --init submodules/ChimpStackr
uv sync --project pancake --frozen --extra chimpstackr
uv run --project pancake --frozen --extra chimpstackr pancake list
```

Configure the [dedicated headless macOS guest](pancake/docs/gui-vm-setup.md) once. GUI
cases then leave the host desktop untouched; CLI, algorithms and physical-device
cases stay on the host. Pancake's pytest suite includes native smoke cases,
so pass `--gui-vm --gui-vm-persist` while using the host desktop.

See the [conformance guide](pancake/docs/conformance.md) for target descriptors, immutable
references, case selection, artifacts and raw/scoped coverage.

The historical [verification record](pancake/docs/verification.md) reports the full passing replay,
coverage totals, runtime pins and remaining gaps.
