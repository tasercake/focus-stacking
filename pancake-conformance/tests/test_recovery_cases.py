"""Recovery contracts must remain public-boundary and selected by the CLI."""
import pytest

def test_recovery_contracts_are_selected_by_default_catalog():
    from pancake_conformance.cli import catalog
    cases = {case.id: case for case in catalog()}
    expected = {
        "interface.recovery.missing-source",
        "interface.recovery.batch-export",
        "interface.recovery.export-cancel",
        "interface.recovery.device-request",
        "interface.recovery.folder-import",
        "interface.recovery.close-unsaved",
    }
    assert expected <= cases.keys()
    assert all(cases[name].suite == "interface" for name in expected)


def test_multiscale_alignment_contracts_cover_host_cpu_and_gpu():
    from pancake_conformance.cli import catalog
    cases = {case.id: case for case in catalog()}
    assert {"algorithms.recovery.cascade.cpu", "algorithms.recovery.cascade.gpu"} <= cases.keys()


def test_error_matcher_uses_semantic_error_state_without_copy():
    from pancake_conformance.cases.recovery import _dialog
    assert _dialog({"nodes": [{"id": "dialog.error", "title": "Any localized error"}]})
    assert not _dialog({"nodes": [{"id": "unrelated", "title": "Any localized error"}]})


@pytest.mark.parametrize("backend", ["cpu", "gpu"])
def test_device_recovery_compares_surfaces_on_observed_backend(tmp_path, monkeypatch, backend):
    """A CPU-only VM and a physical GPU host must use the same parity contract."""
    import json
    from types import SimpleNamespace
    from pancake_conformance.cases import recovery
    event = {'schema_version': 1, 'event': 'stack_complete', 'completed': True,
             'actual_backend': backend}
    (tmp_path / 'events.jsonl').write_text(json.dumps(event) + '\n')
    class UI:
        directory = tmp_path
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def select(self, *args):
            pass
    calls = []
    context = SimpleNamespace(directory=tmp_path, fixture=lambda name: SimpleNamespace(shape=(3, 3, 3), paths=()),
                              open_ui=lambda **kwargs: UI(), note=lambda *args: None,
                              record_output=lambda *args: None,
                              assert_cli_parity=lambda *args, **kwargs: calls.append(kwargs))
    for name in ('_open_settings', '_close_settings', '_prepare', '_stack'):
        monkeypatch.setattr(recovery, name, lambda *args: None)
    monkeypatch.setattr(recovery, '_export', lambda *args: tmp_path / 'export.tif')
    monkeypatch.setattr(recovery, 'validate_image', lambda *args, **kwargs: None)
    recovery._device_request(context)
    assert calls[0]['device'] == backend
    assert calls[0]['mean_limit'] == 1 and calls[0]['max_limit'] == 257
