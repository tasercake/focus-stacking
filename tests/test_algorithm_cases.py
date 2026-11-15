"""Recipe catalog and failure-detection checks; no target internals are loaded."""
from types import SimpleNamespace

import pytest


def test_algorithm_catalog_covers_required_dimensions():
    from stack_conformance.cases.algorithms import algorithm_cases
    cases = algorithm_cases()
    identifiers = [case.id for case in cases]
    assert len(identifiers) == len(set(identifiers))
    assert len(cases) >= 80
    for method in ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion"):
        assert any(method in identifier and "stack" in identifier for identifier in identifiers)
    for mode in ("translation", "euclidean", "similarity", "affine", "breathing"):
        assert any(mode in identifier and "alignment" in identifier for identifier in identifiers)
    assert all(case.suite == "algorithms" for case in cases)


def test_stack_recipe_rejects_failed_process(tmp_path):
    from stack_conformance.cases.algorithms import algorithm_cases
    from stack_conformance.fixtures import generate_fixture
    case = next(case for case in algorithm_cases() if case.id == "algorithms.stack.hybrid")
    context = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                              stack=lambda *a, **kw: SimpleNamespace(returncode=1, stderr="broken", stdout=""),
                              note=lambda *a: None)
    with pytest.raises(AssertionError, match="broken"):
        case.run(context)


def test_stack_recipe_rejects_missing_output(tmp_path):
    from stack_conformance.cases.algorithms import algorithm_cases
    from stack_conformance.fixtures import generate_fixture
    case = next(case for case in algorithm_cases() if case.id == "algorithms.stack.hybrid")
    context = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                              stack=lambda *a, **kw: SimpleNamespace(returncode=0, stderr="", stdout="", output=tmp_path / "missing.png"),
                              note=lambda *a: None)
    with pytest.raises(AssertionError, match="Missing or empty"):
        case.run(context)


def test_catalog_preserves_known_alignment_defects_as_compatibility_cases():
    from stack_conformance.cases.algorithms import algorithm_cases
    identifiers = {case.id for case in algorithm_cases()}
    assert "algorithms.compatibility.translation_overcrop" in identifiers
    assert "algorithms.compatibility.ambiguous_breathing_slabs.hybrid" in identifiers


def test_catalog_exercises_generated_raw_and_mixed_dimensions():
    from stack_conformance.cases.algorithms import algorithm_cases
    identifiers = {case.id for case in algorithm_cases()}
    for method in ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion"):
        assert f"algorithms.input.bayer_dng.{method}" in identifiers
        assert f"algorithms.alignment.mixed_dimensions.{method}" in identifiers
