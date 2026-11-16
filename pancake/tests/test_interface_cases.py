"""Native interface conformance cases are external and toolkit independent."""


def test_interface_cases_have_unique_identifiers():
    from pancake.cases.interface import interface_cases

    cases = interface_cases()
    assert cases
    assert len(cases) == len({case.id for case in cases})
    assert all(case.suite == "interface" for case in cases)


def test_native_method_and_alignment_controls(native_case_runner):
    native_case_runner("interface.controls.method-alignment")


def test_native_export_round_trip(native_case_runner):
    native_case_runner("interface.algorithm.weighted_average")


def test_interface_suite_covers_workflow_boundaries():
    from pancake.cases.interface import interface_cases

    from pancake.cases.interface_settings import settings_cases
    identifiers = {case.id for case in [*interface_cases(), *settings_cases()]}
    assert {"interface.startup.empty", "interface.import.native-dialogs", "interface.export.formats",
            "interface.viewer.navigation-comparison", "interface.settings.persistence",
            "interface.layout.panels", "interface.lifecycle.pause-cancel", "interface.compute.gpu"} <= identifiers
