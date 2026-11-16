"""Recipe catalog and failure-detection checks; no target internals are loaded."""
from types import SimpleNamespace

import pytest


def test_algorithm_catalog_covers_required_dimensions():
    from pancake_conformance.cases.algorithms import algorithm_cases
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
    from pancake_conformance.cases.algorithms import algorithm_cases
    from pancake_conformance.fixtures import generate_fixture
    case = next(case for case in algorithm_cases() if case.id == "algorithms.stack.hybrid")
    context = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                              stack=lambda *a, **kw: SimpleNamespace(returncode=1, stderr="broken", stdout=""),
                              note=lambda *a: None)
    with pytest.raises(AssertionError, match="broken"):
        case.run(context)


def test_stack_recipe_rejects_missing_output(tmp_path):
    from pancake_conformance.cases.algorithms import algorithm_cases
    from pancake_conformance.fixtures import generate_fixture
    case = next(case for case in algorithm_cases() if case.id == "algorithms.stack.hybrid")
    context = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                              stack=lambda *a, **kw: SimpleNamespace(returncode=0, stderr="", stdout="", output=tmp_path / "missing.png"),
                              note=lambda *a: None)
    with pytest.raises(AssertionError, match="Missing or empty"):
        case.run(context)


def test_catalog_requires_corrected_alignment_contracts():
    from pancake_conformance.cases.algorithms import algorithm_cases
    identifiers = {case.id for case in algorithm_cases()}
    assert "algorithms.alignment.translation_bounded_crop" in identifiers
    assert "algorithms.alignment.repeated_breathing_slabs.hybrid" in identifiers


def test_catalog_exercises_generated_raw_and_mixed_dimensions():
    from pancake_conformance.cases.algorithms import algorithm_cases
    identifiers = {case.id for case in algorithm_cases()}
    for method in ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion"):
        assert f"algorithms.input.bayer_dng.{method}" in identifiers
        assert f"algorithms.alignment.mixed_dimensions.{method}" in identifiers


def test_flat_oracle_rejects_legacy_black(tmp_path):
    import numpy as np
    from PIL import Image
    from pancake_conformance.cases.algorithms import _flat
    from pancake_conformance.fixtures import generate_fixture
    output = tmp_path / 'black.png'
    Image.fromarray(np.zeros((65, 99, 3), np.uint8)).save(output)
    ctx = SimpleNamespace(fixture=lambda name: generate_fixture(name, tmp_path),
                          stack=lambda *a, **kw: SimpleNamespace(returncode=0, stderr='', output=output),
                          note=lambda *a: None)
    with pytest.raises(AssertionError, match='pixel'):
        _flat(ctx, 'weighted_average')


@pytest.mark.parametrize('tag', [5, 7])
def test_orientation_oracle_rejects_old_180_degree_compensation(tmp_path, tag):
    import numpy as np
    from PIL import Image
    from pancake_conformance.cases.algorithms import _extended_input
    from pancake_conformance.fixtures import generate_fixture
    from pancake_conformance.validators import read_image
    fixture = generate_fixture(f'orientation{tag}', tmp_path)
    output = tmp_path / 'swapped.png'
    Image.fromarray(np.rot90(read_image(fixture.truth_path), 2)).save(output)
    ctx = SimpleNamespace(fixture=lambda name: fixture,
                          stack=lambda *a, **kw: SimpleNamespace(returncode=0, stderr='', output=output),
                          note=lambda *a: None)
    with pytest.raises(AssertionError, match='pixel'):
        _extended_input(ctx, f'orientation{tag}')
