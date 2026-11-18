# Exact 0a9ae85 native CUDA build

The standalone native CUDA CLI compiled and linked at `0a9ae85b88519a795e3b6ba90860c3b3e664bcaa`, repository tree `fde57a0b461e3ea031ea969e1e841927bead17f9` and Pancake tree `a0efab90fdc3c5f4731d9e0af29acf3f7c5f7d9e`. The exact Cargo lock SHA-256 is `f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`. The original Rust 1.100.0 build used `--locked --offline --release`, `cubecl/cuda`, `CUDARC_CUDA_VERSION=12050`, two direct jobs on logical CPUs 12 and 13 and a task-owned Cargo target. Both observed compiler processes had the expected `12–13` affinity. The build exited 0 after 4m50s. [Build receipt](receipt.json) · [Raw build records](raw-build-records.tar.gz) · [Archive digest](raw-build-records.sha256)

The exact static ELF inspection recorded 281 CUDA and 1,364 NVPTX symbol matches. The feature tree includes CubeCL CUDA 0.11.4 and excludes the GUI, Slint and optional native HIP runtime. The four CUDA runtime files were rehashed against the already reviewed CUDA 12.5 and Linux driver bytes. The read-only retained CLI at `artifacts/pancake-linux-native/0a9ae85/pancake-cli` has SHA-256 `0734a90ba35ef3534fd6a66a86682ef98662e87a9f0ecc8b25c42b3fccdbdad3` and GNU Build ID `223d96ea4ead73d82eb2173d0169c26b8b8f5e5b`. It is independently retained alongside its exact build receipt.

This is compile and link evidence for the standalone native CUDA executable. No application launch, device query, performance test or GPU-memory observation ran. Independently scoped actual execution and device-memory qualification remain pending for this exact artifact. The notice-bearing Debian package and its complete conformance ledger retain their own provenance.

## Prepared real E9 CUDA witnesses

The functional command stages two complete fresh-process jobs on the exact nine previously authenticated E9 originals. It validates the same physical RTX, actual CUDA and absence of fallback, all registration maps, complete RGB16 decoding and the unchanged encoded and decoded hashes. It freezes the validated inputs and executable before and after. These witnesses use a fresh cache per launch and supply no P10 timing or device-memory credit. Run from a clean checkout of the exact source, with the pinned qualification Python and an explicit exclusive device lease. `PRIVATE_INPUTS` denotes the existing scoped original stage and `FRESH_OUTPUT` a new directory under the same ownership.

```sh
export PYTHONPATH="$ROOT/pancake-conformance/src:$ROOT/qualification/p10-performance"
env -u LD_LIBRARY_PATH -u LD_PRELOAD taskset -c 12,13 "$QUAL_PY" "$EVIDENCE/e9-native-smoke.py.txt" run \
  --binary "$RETAINED/pancake-cli" --receipt "$RETAINED/build-receipt.json" \
  --input-root "$PRIVATE_INPUTS" --output "$FRESH_OUTPUT"
```

The `preflight` subcommand checks the same source, artifact, libraries and input bytes without an application launch or device query. [Prepared witness tool](e9-native-smoke.py.txt)
