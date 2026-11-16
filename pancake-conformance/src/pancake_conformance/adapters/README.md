# Application adapters

Application-specific code, target descriptors, dependency projects, source
coverage scopes, tests, and verification records belong in this directory.
Each runtime project owns its dependency lock and installs the suite as a local
editable dependency. Core installation does not install target applications.

A target descriptor may select an importable adapter module, a runtime project,
and optional source instrumentation. See the suite's
[generic target contract](../../../docs/conformance.md).

Available integration: [ChimpStackr](chimpstackr_reference/README.md).
