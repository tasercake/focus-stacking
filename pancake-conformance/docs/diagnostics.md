# Optional execution diagnostics

Ordinary image cases validate process completion and independently decoded
output. They do not require calibration records, device-selection algorithms,
cache files, per-stage backends, or alignment matrices. Automatic execution may
use any valid strategy and may select different devices for repeated work.

A target declaring `backend_evidence` can run explicit CPU/GPU proof cases.
It writes JSON Lines to the case-owned `CONFORMANCE_EVENTS_PATH`, directly or
through an adapter. A completion record has this minimum form:

```json
{"event":"stack_complete","completed":true,"actual_backend":"gpu"}
```

A requested or initialized backend is not proof of completed execution. Explicit
proof cases require a successful process, completed output, and truthful
aggregate backend evidence matching the request. `observer_error` fails the
diagnostic check. Missing optional telemetry is permitted in ordinary image
cases, which then make no hardware-execution claim. Extra diagnostic fields
may be retained as evidence but are not mandatory or compared as architecture.

CPU/GPU parity checks compare decoded RGB geometry and numerical error. They do
not prescribe which internal stages use a device. Instrumented timings are not
uninstrumented performance benchmarks. Source coverage remains an optional,
adapter-specific measurement described in [coverage](coverage.md).


The optional `alignment_evidence` capability enables v2 geometry oracles.
A `stack_complete` record supplies `alignment_transforms`, keyed by input path,
and `sequential_transforms` in input order when chaining. Every matrix is finite
2×3, mapping reference x/y coordinates to source x/y coordinates. These fields
specify observable geometry, not implementation language, estimator or device.
Targets without this capability report these cases as unsupported; ordinary
pixel-based alignment tests remain available.

Failed decode records must never claim successful completion or CPU fallback
from input corruption. Optional telemetry may be absent, but any published
completion or backend evidence must be truthful.
