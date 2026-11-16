"""Native interface conformance cases are external and toolkit independent."""


def test_interface_cases_have_unique_identifiers():
    from pancake_conformance.cases.interface import interface_cases

    cases = interface_cases()
    assert cases
    assert len(cases) == len({case.id for case in cases})
    assert all(case.suite == "interface" for case in cases)


def test_native_method_and_alignment_controls(native_case_runner):
    native_case_runner("interface.controls.method-alignment")


def test_native_export_round_trip(native_case_runner):
    native_case_runner("interface.algorithm.weighted_average")


def test_interface_suite_covers_workflow_boundaries():
    from pancake_conformance.cases.interface import interface_cases

    from pancake_conformance.cases.interface_settings import settings_cases
    identifiers = {case.id for case in [*interface_cases(), *settings_cases()]}
    assert {"interface.startup.empty", "interface.import.native-dialogs", "interface.export.formats",
            "interface.viewer.navigation-comparison", "interface.settings.persistence",
            "interface.layout.panels", "interface.lifecycle.pause-cancel", "interface.compute.gpu"} <= identifiers


def test_pan_setup_exceeds_observed_fit_zoom():
    import json
    from pancake_conformance.cases.interface import _zoom_for_pan
    class UI:
        zoom = 1.25
        def node(self, name):
            assert name == 'viewer'
            return {'description': json.dumps({'zoom': self.zoom})}
        def action(self, name):
            assert name == 'viewer.zoom_in'
            self.zoom *= 1.25
        def wait(self, predicate, **kwargs):
            assert predicate({})
    ui = UI()
    _zoom_for_pan(ui, 3.5)
    assert ui.zoom > 3.5 * 1.25
