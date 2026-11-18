# Native registration geometry mutation checks

The `0a9ae85` Linux mutation shard 9/16 compiled and tested the saved change at `src/registration/estimate.rs:311:23` and recorded a survivor. That change divides the first diagonal rotation deviation by one instead of subtracting one. The resulting affine can still be finite even though its linear part no longer preserves distance.

The test-only `599dc5c` checkout calls the normal Euclidean branch of `Coordinates::convert`. Its exact 24–143–145 Pythagorean triple gives an independent rotation on a 129 × 97 canvas with a nonzero translation. The checks cover both orthonormal columns, a unit determinant, the translated center and both oriented basis points. An independently specified transpose takes each mapped point back to its original coordinate. The oracle uses no spectral search, image renderer or approximate fitting.

The exact saved mutant compiled and the existing native library executable failed the new test at the rigid-matrix assertion, with first diagonal `1.9862069` and second diagonal `0.9862069`. After restoring the estimator byte-for-byte, all 24 library tests and all three existing native CPU registration cases passed. Focused strict Clippy, formatting and reviewed source inventory validation passed. There is no full-shard, Miri or device execution claim.

[Exact original mutation](euclidean/saved.diff) · [Shard observation](euclidean/shard-outcome.json) · [Mutated run](euclidean/red.log.gz) · [Restored run](euclidean/green.log.gz) · [Exact replay inputs](euclidean/identities.json)

## Replay scope

Use an isolated checkout with the specified test-only revision and host CPU allocation. The saved patch applies relative to `pancake/` with `patch --batch --fuzz=0 -p0`. Keep a verified copy of the estimator and restore it even if the mutated test fails. Run offline and locked under Rust 1.100.0. These observations used two direct Cargo jobs on CPUs 4 and 5 of a Ryzen 9 7950X3D. The same fixture and test-only source appear on both arms.

```sh
export CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0
env -u RUSTC_WRAPPER -u RUSTC_WORKSPACE_WRAPPER taskset -c 4,5 \
  cargo +1.100.0 test --offline --locked -p pancake --lib \
  registration::estimate::tests::euclidean_parameters_produce_a_rigid_map -- --exact --test-threads=1
```

The mutated arm exits 101 at the rigid-map check. The restored verification adds `--test cpu_registration_contract` and omits the exact test filter. The source-policy check and Clippy use the unchanged repository dependency-policy generator.
