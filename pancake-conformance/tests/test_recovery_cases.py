"""Recovery contracts must remain public-boundary and selected by the CLI."""

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
