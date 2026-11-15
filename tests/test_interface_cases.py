"""Native interface conformance cases are external and toolkit independent."""
from pathlib import Path


def test_interface_cases_have_unique_identifiers():
    from stack_conformance.cases.interface import interface_cases

    cases = interface_cases()
    assert cases
    assert len(cases) == len({case.id for case in cases})
    assert all(case.suite == "interface" for case in cases)


def test_native_method_and_alignment_controls(tmp_path):
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    from stack_conformance.cases.interface import interface_cases

    target = TargetSpec.load(Path(__file__).parents[1] / "targets/chimpstackr.toml")
    case = next(case for case in interface_cases() if case.id == "interface.controls.method-alignment")
    case.run(CaseContext(target, tmp_path))


def test_native_export_round_trip(tmp_path):
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    from stack_conformance.cases.interface import interface_cases

    target = TargetSpec.load(Path(__file__).parents[1] / "targets/chimpstackr.toml")
    case = next(case for case in interface_cases() if case.id == "interface.algorithm.weighted_average")
    case.run(CaseContext(target, tmp_path))


def test_interface_suite_covers_workflow_boundaries():
    from stack_conformance.cases.interface import interface_cases

    from stack_conformance.cases.interface_settings import settings_cases
    identifiers = {case.id for case in [*interface_cases(), *settings_cases()]}
    assert {"interface.startup.empty", "interface.import.native-dialogs", "interface.export.formats",
            "interface.viewer.navigation-comparison", "interface.settings.persistence",
            "interface.layout.panels", "interface.lifecycle.pause-cancel", "interface.compute.gpu"} <= identifiers
