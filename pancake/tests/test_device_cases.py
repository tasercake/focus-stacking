"""Device contracts must reject fallback and missing execution evidence."""
from types import SimpleNamespace

import pytest


def result(events, returncode=0):
    return SimpleNamespace(returncode=returncode, stderr='target error', diagnostics={'events': events})


def test_device_catalog_covers_algorithms_alignment_and_precision():
    from pancake.cases.devices import device_cases
    cases = device_cases()
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids))
    assert len(cases) >= 25
    assert all(case.suite == 'devices' for case in cases)
    for method in ('laplacian', 'hybrid', 'weighted_average', 'depth_map', 'exposure_fusion'):
        assert f'devices.gpu.stack.{method}' in ids
        assert f'devices.cpu.{method}' in ids
    for mode in ('translation', 'euclidean', 'similarity', 'affine', 'breathing'):
        assert f'devices.gpu.alignment.{mode}' in ids
    assert any('precision16' in ident for ident in ids)
    assert any('auto' in ident for ident in ids)


def test_strict_gpu_contract_rejects_cpu_fallback():
    from pancake.cases.devices import require_backend
    run = result([{'event': 'stack_complete', 'completed': True, 'actual_backend': 'cpu'}])
    with pytest.raises(AssertionError, match='Expected gpu'):
        require_backend(run, 'gpu')


def test_device_contract_requires_completed_diagnostics():
    from pancake.cases.devices import require_backend
    with pytest.raises(AssertionError, match='completed execution diagnostics'):
        require_backend(result([]), 'gpu')
    with pytest.raises(AssertionError, match='did not complete'):
        require_backend(result([{'event': 'stack_complete', 'completed': False, 'actual_backend': None}]), 'cpu')
    with pytest.raises(AssertionError, match='observer_error'):
        require_backend(result([{'event': 'observer_error', 'message': 'broken'}]), 'cpu')


def test_device_contract_accepts_actual_completed_stage():
    from pancake.cases.devices import require_backend
    event = {'event': 'stack_complete', 'completed': True, 'actual_backend': 'gpu',
             'actual_backend_by_stage': {'fusion': 'gpu'}}
    assert require_backend(result([{'event': 'observer_ready'}, event]), 'gpu') is event


def test_device_catalog_contains_real_fallback_and_measured_cache_reuse():
    from pancake.cases.devices import device_cases
    identifiers = {case.id for case in device_cases()}
    assert 'devices.gpu.decode_fallback' in identifiers
    assert 'devices.auto.measured_cache_reuse' in identifiers
