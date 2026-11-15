"""Portable native result and filename contracts, without desktop access."""
import numpy as np
import pytest
import tifffile


def test_portability_catalog_has_bounded_cpu_native_scenarios():
    from stack_conformance.cases.interface_portability import portability_cases

    cases = portability_cases()
    assert {case.id for case in cases} == {'interface.portability.retained-results',
                                          'interface.portability.unicode-paths'}
    assert all(case.suite == 'interface' and case.description for case in cases)
    assert all('physical_gpu' not in case.required_capabilities for case in cases)


def test_result_selection_uses_semantic_row_text_not_frame_or_child_rows():
    from stack_conformance.cases.interface_portability import result_row, result_rows

    snapshot = {'nodes': [
        {'id': 'frames', 'role': 'AXList', 'path': [0]},
        {'role': 'AXRow', 'value': 'Hybrid', 'path': [0, 0]},
        {'id': 'results', 'role': 'AXList', 'path': [1]},
        {'role': 'AXRow', 'path': [1, 0]},
        {'role': 'AXStaticText', 'value': 'Hybrid\n3 frames', 'path': [1, 0, 0]},
        {'role': 'AXRow', 'value': 'Weighted Average\n3 frames', 'path': [1, 1]},
    ]}
    assert len(result_rows(snapshot)) == 2
    assert result_row(snapshot, 'Hybrid')['path'] == [1, 0]
    assert result_row(snapshot, 'Weighted Average')['path'] == [1, 1]
    with pytest.raises(AssertionError, match='one result'):
        result_row(snapshot, 'Depth Map')


def test_result_selection_rejects_duplicate_method_rows():
    from stack_conformance.cases.interface_portability import result_row

    snapshot = {'nodes': [{'id': 'results', 'role': 'AXList', 'path': [1]},
                          {'role': 'AXRow', 'value': 'Hybrid', 'path': [1, 0]},
                          {'role': 'AXRow', 'value': 'Hybrid', 'path': [1, 1]}]}
    with pytest.raises(AssertionError, match='one result'):
        result_row(snapshot, 'Hybrid')


def test_retained_export_validator_rejects_replaced_or_mutated_old_result(tmp_path):
    from stack_conformance.cases.interface_portability import validate_retained_exports

    old = (np.arange(8 * 10 * 3, dtype=np.uint16).reshape(8, 10, 3) * 173)
    new = (np.arange(12 * 14 * 3, dtype=np.uint16).reshape(12, 14, 3) * 79)
    first, second, restored = (tmp_path / name for name in ('first.tif', 'second.tif', 'restored.tif'))
    for path, pixels in ((first, old), (second, new), (restored, old)):
        tifffile.imwrite(path, pixels, photometric='rgb')
    validate_retained_exports(first, second, restored, (12, 14, 3))
    tifffile.imwrite(restored, old + 1, photometric='rgb')
    with pytest.raises(AssertionError, match='pixel error'):
        validate_retained_exports(first, second, restored, (12, 14, 3))


def test_unicode_save_name_exercises_cjk_accent_space_and_non_bmp():
    from stack_conformance.cases.interface_portability import UNICODE_EXPORT_NAME

    assert UNICODE_EXPORT_NAME.endswith('.tif')
    assert ' ' in UNICODE_EXPORT_NAME and 'é' in UNICODE_EXPORT_NAME
    assert any('\u4e00' <= char <= '\u9fff' for char in UNICODE_EXPORT_NAME)
    assert any(ord(char) > 0xffff for char in UNICODE_EXPORT_NAME)


def test_old_result_remains_testable_when_native_ax_row_loses_attributes():
    from types import SimpleNamespace
    from stack_conformance.cases.interface_portability import _select_older_result

    snapshot = {'nodes': [
        {'id': 'results', 'role': 'AXList', 'path': [1]},
        {'role': 'AXRow', 'path': [1, 0]},
        {'role': 'AXStaticText', 'title': 'Hybrid\n4 frames', 'path': [1, 0, 0]},
        {'path': [1, 1]},  # Observed old Qt AX row: visible, but attrs unavailable.
        {'id': 'status', 'value': 'Hybrid result · 321 × 257'},
        {'id': 'export.start', 'enabled': True},
    ]}
    actions = []
    def key(name):
        actions.append(('key', name))
        assert name == 'down'
        snapshot['nodes'][-2]['value'] = 'Weighted Average result · 311 × 251'
    def wait(condition, **kwargs):
        assert condition(snapshot), kwargs.get('description')
    ui = SimpleNamespace(snapshot=lambda: snapshot,
                         click=lambda selector: actions.append(('click', selector)),
                         key=key, wait=wait)
    _select_older_result(ui, 'Hybrid', 'Weighted Average')
    assert actions == [('click', {'path': [1, 0]}), ('key', 'down')]


def test_new_result_wait_rejects_old_export_enabled_before_new_job_finishes():
    from types import SimpleNamespace
    from stack_conformance.cases.interface_portability import _wait_for_result

    snapshot = {'nodes': [{'id': 'status', 'value': 'Weighted Average result'},
                          {'id': 'export.start', 'enabled': True}]}
    observed = []
    ui = SimpleNamespace(wait=lambda condition, **kwargs: observed.append(condition(snapshot)))
    _wait_for_result(ui, 'Hybrid')
    assert observed == [False]
    snapshot['nodes'][0]['value'] = 'Hybrid result'
    _wait_for_result(ui, 'Hybrid')
    assert observed == [False, True]
