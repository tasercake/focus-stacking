"""Opt-in child-process instrumentation. No application behavior is replaced."""
import os

if os.environ.get('COVERAGE_PROCESS_START'):
    import coverage
    coverage.process_startup()

if os.environ.get('CHIMPSTACKR_CONFORMANCE_EVENTS'):
    import chimpstackr_observer
    chimpstackr_observer.install()
