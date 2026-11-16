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
