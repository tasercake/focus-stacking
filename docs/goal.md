# Conformance goal

Build and verify a language- and UI-framework-independent macOS conformance
suite against the pinned Python ChimpStackr reference, with host CLI/algorithm/
physical-device execution and optional headless Tart guest GUI execution.
Application behavior must remain unchanged. All supported cases must pass.

The coverage target is **100% of used, reachable code and branch exits in this
macOS source target**. Confirmed dead, unused, or unreachable code is outside
that target, following the user's scope revision on 2026-11-16. Do not add
test-only callers merely to execute unused production functions.

Keep raw coverage unchanged. Report scoped coverage separately, with a pinned,
reviewable exclusion manifest, exact source ranges, and evidence for each
exclusion. Hard-to-trigger errors and unmeasured code are not automatically
dead or unreachable. An exclusion never counts as execution or a passed case.

Continue all test runs with `--gui-vm --gui-vm-persist`. Keep VM headless and
host keyboard, pointer and foreground application untouched. Guest GPU limits
remain explicit unsupported cases. Preserve generated fixtures, frozen output
references, host/guest source normalization, and per-case artifacts.
