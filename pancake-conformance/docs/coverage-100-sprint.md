# Reachable coverage sprint

The 100% reachable-source coverage goal remains unmet. This sprint preserves the
raw denominator and existing reviewed scope; no exclusions were added or widened.
ChimpStackr source and behavior remain unchanged at
`046266223945cc1cbf8eacd295c00ee08d42d095`.

## Execution boundary

All test commands used `--gui-vm --gui-vm-persist`. Native GUI cases ran only in
the headless `chimpstackr-conformance` Tart guest. CLI, numerical algorithms and
physical-device cases ran on the host. The reference descriptor reuses the
provisioned guest and SSH identity; the suite move does not rename those resources.
An unavailable guest never causes host GUI fallback.

## Added contracts

Eight cases use generated files, native controls and exported pixels:

- Six GUI recovery workflows: filtered recursive folder import, GPU preference
  with explicit actual-device reporting, source disappearance after import,
  conflicting batch-export destination and retry, export cancellation, and
  unsaved-window close/cancel/export/discard.
- Two host numerical workflows recover known translation in 4097 x 257 frames
  through multiscale CPU and physical-GPU alignment, including the high-precision
  CPU cascade. Each case generates only its two small compressed input files.

The GPU-request GUI case may complete through CPU fallback in the guest. It
records that actual backend and does not certify physical-GPU GUI execution.
The separate physical-GPU GUI case stays explicitly unsupported in this guest.

## Measurement limits

The five native Numba bodies in the existing measurement-limit ledger account
for 57 missing executable source statements and 26 missing branch exits. Their
bodies execute outside ordinary Python tracing. They remain in the scoped
measurement denominator, and compile-time notifications do not count as runtime
execution. Even perfect tracing coverage of every other scoped statement and
branch would leave a Python-tracer ceiling of 99.125% lines and 98.337% branches.
This is a measurement ceiling, not a claim that every native branch was tested.

GUI GPU initialization, GPU calibration and physical-GPU settings paths cannot
execute in the GPU-less guest. Host CLI/device GPU tests remain separate evidence.
Recoverable driver/allocation/build failures, rare UI events and other untested
errors remain measured gaps; no absence from a run proves dead code.

## Verification

Fresh 308-case baseline: 307 passed, zero failed, one unsupported. Raw coverage
was 5967/7256 statements and 1178/1812 branch exits. Existing reviewed scope was
5914/6514 statements (90.789%) and 1178/1563 branch exits (75.368%).

The complete harness passed 262 tests with VM flags. All eight new cases passed
across targeted runs. A separate expanded replay was interrupted after an
intermittent existing Unicode native-popup failure; it is not a passing full
replay and no new reference manifest was published.

A separately labelled union of only complete, zero-failure runs (the full baseline,
the two-case cascade rerun and the three-case recovery rerun) covers 5938/6514
scoped statements (91.158%) and 1182/1563 branch exits (75.624%). Raw totals are
5991/7256 statements and 1182/1812 branch exits. This union is not a new full-suite
replay. Its inputs and missing inventories remain in
`artifacts/coverage-100-passing-union/`. Interrupted evidence remains in
`artifacts/coverage-100-final/`; it is not imported into the passing-run union.
