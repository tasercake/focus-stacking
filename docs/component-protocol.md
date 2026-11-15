# Component hook protocol

Cases remain independent of the target language, module names and UI toolkit.
The target descriptor's `probe` argv selects a process which accepts
`--request PATH --response PATH`. Shell parsing is never used. Both paths belong
to one isolated case call directory. Component execution stays on the host,
including when `--gui-vm` selects guest GUI execution.

Request:

```json
{"schema_version":1,"operation":"service.updates.check","arrays":{},"options":{"endpoint":"http://127.0.0.1:12345/releases","current_version":"1.0.0","include_prerelease":false}}
```

Success:

```json
{"schema_version":1,"ok":true,"arrays":{},"values":{"release":null}}
```

Semantic failure still exits zero and returns `ok:false` with
`error:{"kind":"...","message":"..."}`. A nonzero process exit, missing
response, invalid protocol or timeout fails the case. Error type names and
diagnostics are not Python-specific conformance requirements.

| Operation | Contract |
| --- | --- |
| `service.updates.version` | Parse/display release versions; expose current version |
| `service.updates.check` | Fetch a real HTTP feed; choose eligible newer stable/prerelease and native asset |
| `service.updates.download` | Download real bytes; verify SHA256, progress, cancellation and failure cleanup |
| `service.updates.installation` | Report actual installation capability; source launch refuses self-replacement |

Exact options and independent oracles are in `cases/services.py`. HTTP fixtures
are tiny generated responses from an OS-assigned loopback port. Their status,
headers, lengths and SHA256 hashes enter the frozen fixture contract. Request
contracts normalize only case-owned path prefixes and local ephemeral ports;
payloads, routes, query strings and semantic options stay fixed. Full requests
and responses remain artifacts. No public update service or installed app is
modified. Native cases use the same local service through `services.updates`.

The reference launcher delegates service operations to the original ChimpStackr
functions. Endpoint substitution is an opt-in configuration hook. Parsing,
network requests, cancellation, integrity checks, exceptions, worker signals,
dialogs and preferences execute unchanged. No staging helper is launched and
no frozen/platform identity is substituted.

The protocol also defines optional numeric arrays for future reachable
components: `{dtype,shape,data}` with row-major flattened values, or
`{dtype,shape,real,imag}` for complex values. Supported types are Boolean,
8/16/32/64-bit signed/unsigned integers, float32/64 and complex64/128. Arrays
must be finite and match shape; object/pickle data are forbidden. Returned
arrays are retained as `.npy` and frozen as data: integer/Boolean values exact,
floating/complex values with `atol=rtol=1e-5`. Current service operations use
structured values and independent semantic oracles, not numeric arrays.
