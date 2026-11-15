import json


def test_runner_records_failure_and_continues(tmp_path):
    from stack_conformance.model import Case
    from stack_conformance.runner import run_cases

    def fail(ctx):
        raise AssertionError("wrong pixels")

    def passed(ctx):
        ctx.note("proof", "checked")

    result = run_cases([Case("bad", "unit", fail), Case("good", "unit", passed)],
                       target=None, output=tmp_path)
    assert result[0].status == "failed"
    assert result[1].status == "passed"
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["counts"] == {"passed": 1, "failed": 1}
    assert "wrong pixels" in report["cases"][0]["error"]
    assert (tmp_path / "junit.xml").is_file()


def test_case_ids_are_unique(tmp_path):
    import pytest
    from stack_conformance.model import Case
    from stack_conformance.runner import run_cases
    with pytest.raises(ValueError, match="duplicate"):
        run_cases([Case("same", "unit", lambda ctx: None)] * 2, target=None, output=tmp_path)


def test_case_id_cannot_escape_artifact_directory(tmp_path):
    import pytest
    from stack_conformance.model import Case
    from stack_conformance.runner import run_cases
    with pytest.raises(ValueError, match="path"):
        run_cases([Case("..", "unit", lambda ctx: None)], target=None, output=tmp_path)


def test_coverage_gate_failure_is_visible_in_json_and_junit(tmp_path):
    from xml.etree import ElementTree as ET
    from stack_conformance.model import Case
    from stack_conformance.runner import run_cases, record_coverage
    run_cases([Case("unit.pass", "unit", lambda ctx: None)], target=None, output=tmp_path)
    passed = record_coverage(tmp_path, {"line_percent": 50, "branch_percent": 40},
                             line_minimum=100, branch_minimum=100)
    assert not passed
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "failed"
    assert report["coverage_gate"]["passed"] is False
    root = ET.parse(tmp_path / "junit.xml").getroot()
    assert root.attrib["failures"] == "1"
    assert root.find("testcase[@name='coverage.thresholds']/failure") is not None
