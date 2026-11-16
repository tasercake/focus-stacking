# Adapter isolation verification — 2026-11-16

Application-specific configuration, dependency metadata, coverage scope, tests,
and historical evidence now live under `src/pancake_conformance/adapters/`.
The core suite requires an explicit target and uses declared adapter hooks,
source instrumentation, runtime project, and fixture settings.

Validation completed:

- Core environment synchronized without application or Qt dependencies:
  251 tests passed; two native smoke tests skipped because no target was selected.
- Isolated adapter runtime: 17 tests passed, including real service subprocesses.
- Real adapter smoke: all 11 selected cases passed with coverage enabled:
  CLI help, all nine service cases, and weighted-average stacking.
- Core lint, both lock consistency checks, source distribution, and wheel passed.
  Package inspection found no environments, artifacts, or application dependencies
  in wheel metadata. Case-insensitive source/path scans found no application-name
  references outside adapters, including nonignored and ignored text files.
- Upstream source checkout remained clean. Full native GUI/VM replay was not run.

[Smoke report](../artifacts/adapter-boundary-verified/report.json) and
[coverage summary](../artifacts/adapter-boundary-verified/coverage/summary.json)
are local generated artifacts. This smoke measured raw execution of 907/7,256
lines and 94/1,812 branch exits. These partial-run totals verify instrumentation;
they do not replace historical full-suite coverage evidence.

Generic VM unit checks cover explicit runtime selection, workspace containment,
source transport without nested environments, source provenance, and dispatch.
