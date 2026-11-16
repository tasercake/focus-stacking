from pathlib import Path


def test_service_adapter_preserves_real_semver_and_display_semantics(tmp_path):
    from pancake_conformance.context import CaseContext
    from pancake_conformance.target import TargetSpec
    descriptor = Path(__file__).resolve().parents[1] / "chimpstackr_reference/chimpstackr.toml"
    context = CaseContext(TargetSpec.load(descriptor), tmp_path)
    result = context.probe("service.updates.version", options={"versions": ["v1.2.3", "2.0.0-rc1", "bad"]})
    assert result.ok, result.error
    assert result.arrays == {}
    versions = result.values["versions"]
    assert versions[0]["version"] == {"major": 1, "minor": 2, "patch": 3, "prerelease": False, "commits": 0}
    assert versions[1]["version"]["prerelease"] is True
    assert versions[2]["version"] is None
    assert versions[0]["display"] == "1.2.3"
