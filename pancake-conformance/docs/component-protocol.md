# Optional component hook transport

A target descriptor may provide a `probe` command accepting
`--request PATH --response PATH`. Both paths belong to an isolated call
directory. The command runs as an external process, with argument arrays rather
than shell parsing. This transport is available for explicit component
extensions; the portable catalog does not require an updater, a delivery
service, or any particular release mechanism.

Requests carry `schema_version: 1`, an `operation` string, numeric `arrays`, and
structured `options`. Responses carry `schema_version: 1`, Boolean `ok`,
`arrays`, and structured `values`. A semantic failure exits zero and returns
`ok: false` with an `error` object containing a nonempty `kind`. A process
failure, timeout, missing response, or invalid schema fails the call. Exception
class names are not cross-language requirements.

Arrays use `{dtype, shape, data}` with row-major flattened values, or
`{dtype, shape, real, imag}` for complex values. Supported types are Boolean,
8/16/32/64-bit signed and unsigned integers, float32/64, and complex64/128.
Values must be finite and match the shape; object and pickle payloads are
forbidden. Returned arrays are retained as `.npy` artifacts. Optional frozen
baseline comparisons use exact integer/Boolean values and `atol=rtol=1e-5`
for floating/complex values.

Component execution stays on the host when GUI workflows run in a VM. An
extension must define its own observable contract and independent oracle;
exposing an application's private helper does not make that helper a portable
feature requirement.
