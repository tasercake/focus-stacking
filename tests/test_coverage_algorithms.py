"""Coverage expansion stays at portable process and file boundaries."""
from types import SimpleNamespace

import pytest


def test_coverage_algorithm_catalog_is_portable_and_unique():
    from stack_conformance.cases.coverage_algorithms import coverage_algorithm_cases
    cases = coverage_algorithm_cases()
    identifiers = [case.id for case in cases]
    assert len(identifiers) >= 16
    assert len(identifiers) == len(set(identifiers))
    assert all(case.suite == "algorithms" and case.id.startswith("algorithms.coverage.") for case in cases)
    assert any("precision.affine" in name for name in identifiers)
    assert any("mixed_precision" in name for name in identifiers)
    assert any("partial_corrupt" in name for name in identifiers)
    assert any("hdr_multibatch" in name for name in identifiers)


def test_precision_recipe_rejects_process_failure(tmp_path):
    from stack_conformance.cases.coverage_algorithms import coverage_algorithm_cases
    from stack_conformance.fixtures import generate_fixture
    case = next(case for case in coverage_algorithm_cases() if case.id.endswith("precision.affine"))
    context = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                              stack=lambda *a, **kw: SimpleNamespace(returncode=1, stderr="processing failed", stdout=""),
                              note=lambda *args: None, directory=tmp_path)
    with pytest.raises(AssertionError, match="processing failed"):
        case.run(context)
