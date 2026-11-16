# Portable execution diagnostics

Cases may inspect read-only execution records published to
`CONFORMANCE_EVENTS_PATH`. The suite sets a case-owned JSON Lines path for each
call. An adapter may translate this setting into its application's observation
hook. Target module names, private caches, and profiler mechanics belong in
adapters.

Records describe completed execution. Backend selection or initialization alone
does not prove GPU completion. Device cases require completed output and backend
evidence; ordinary algorithm cases validate exported images independently.

Core records include `stack_complete`, `backend_fallback`, `crop_complete`,
`measurement_complete`, `measurement_lookup`, and `device_decision`.
`stack_complete.actual_backend` is `cpu`, `gpu`, or null for incomplete work;
`actual_backend_by_stage` distinguishes fusion, alignment estimation, and warping.
`not_requested` marks stages omitted by the request. Output shape uses
height/width/channel order; matrix coordinates use x/y image order.

Records can include requested backend, effective parameters, input order,
alignment matrices, measured timings, and cache reuse. Observation must not
change target results, suppress exceptions, or initiate business operations.
`observer_error`, absent completion evidence, incomplete output, and wrong
completed backend fail diagnostic assertions.

CPU/GPU parity uses independently decoded RGB pixels. Geometry must match
before numerical comparisons. Measured timings under instrumentation are
execution observations, not uninstrumented performance benchmarks. Numeric
budgets and versioned correctness cases are explicit in the case catalog and
[numerical contract](algorithm-contract.md).
