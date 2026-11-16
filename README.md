# Focus-stacking research

Research and tools for building a high-quality macro focus-stacking benchmark.

- [Bokehforge](bokehforge/README.md): `uv` project with dataset download and processing CLI, source configuration, tests, and documentation.
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

The root project provides `stack-conformance`, an independent CLI for
portable ChimpStackr CLI, algorithm, device and native-interface contracts.
Application source remains unchanged. Bokehforge's data CLI and generated data
remain separate from these synthetic conformance fixtures.

```sh
git submodule update --init submodules/ChimpStackr
uv sync --extra chimpstackr
uv run --extra chimpstackr stack-conformance run --gui-vm --gui-vm-persist
```

Configure the [dedicated headless macOS guest](docs/gui-vm-setup.md) once. GUI
cases then leave the host desktop untouched; CLI, algorithms and physical-device
cases stay on the host. The root pytest suite includes native smoke cases,
so pass `--gui-vm --gui-vm-persist` while using the host desktop.

See the [conformance guide](docs/conformance.md) for target descriptors, immutable
references, case selection, artifacts and raw/scoped coverage.

The [verification record](docs/verification.md) reports the full passing replay,
coverage totals, runtime pins and remaining gaps.
