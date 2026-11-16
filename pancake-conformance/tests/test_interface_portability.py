"""Portable native result and filename contracts, without desktop access."""
import numpy as np
import pytest
import tifffile


def test_portability_catalog_has_bounded_cpu_native_scenarios():
    from pancake_conformance.cases.interface_portability import portability_cases

    cases = portability_cases()
    assert {case.id for case in cases} == {'interface.portability.retained-results',
                                          'interface.portability.unicode-paths'}
    assert all(case.suite == 'interface' and case.description for case in cases)
    assert all('physical_gpu' not in case.required_capabilities for case in cases)


def test_retained_export_validator_rejects_replaced_or_mutated_old_result(tmp_path):
    from pancake_conformance.cases.interface_portability import validate_retained_exports

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
    from pancake_conformance.cases.interface_portability import UNICODE_EXPORT_NAME

    assert UNICODE_EXPORT_NAME.endswith('.tif')
    assert ' ' in UNICODE_EXPORT_NAME and 'é' in UNICODE_EXPORT_NAME
    assert any('\u4e00' <= char <= '\u9fff' for char in UNICODE_EXPORT_NAME)
    assert any(ord(char) > 0xffff for char in UNICODE_EXPORT_NAME)


def test_old_result_selection_is_semantic_without_row_order():
    from types import SimpleNamespace
    from pancake_conformance.cases.interface_portability import _select_older_result
    state = {"method": "hybrid"}
    actions = []
    def action(name):
        actions.append(name)
        state["method"] = name.rsplit(".", 1)[1]
    snapshot = {"nodes": [{"id": "export.start", "enabled": True}]}
    ui = SimpleNamespace(action=action, observe=lambda *args: state["method"],
                         wait=lambda predicate, **kwargs: predicate(snapshot))
    _select_older_result(ui, "hybrid", "weighted_average")
    assert actions == ["results.select.weighted_average"]
    assert state["method"] == "weighted_average"


def test_result_wait_requires_selected_result_and_export_availability():
    from types import SimpleNamespace
    from pancake_conformance.cases.interface_portability import _wait_for_result
    snapshot = {"nodes": [{"id": "export.start", "enabled": True}]}
    selected = ["weighted_average"]
    observed = []
    ui = SimpleNamespace(observe=lambda *args: selected[0],
                         wait=lambda predicate, **kwargs: observed.append(predicate(snapshot)))
    _wait_for_result(ui, "hybrid")
    selected[0] = "hybrid"
    _wait_for_result(ui, "hybrid")
    snapshot["nodes"][0]["enabled"] = False
    _wait_for_result(ui, "hybrid")
    assert observed == [False, True, False]
