import hashlib
import json

import pytest


def _fixture(tmp_path):
    from pancake.coverage import source_provenance
    source = tmp_path / "src"
    source.mkdir()
    (source / "module.py").write_text("x = 1\nif x:\n    x = 2\nelse:\n    x = 3\n")
    report = {"files": {str(source / "module.py"): {
        "executed_lines": [1, 2, 3], "missing_lines": [5],
        "executed_branches": [[2, 3]], "missing_branches": [[2, 5]]}}}
    profile = {"schema_version": 1, "name": "macos-source",
               "source_sha256": source_provenance(source)["source_sha256"],
               "exclusions": [{"file": "module.py", "ranges": [[5, 5]], "category": "unreachable",
                               "reason": "Opposite platform body", "evidence": "Constant platform condition"}]}
    return source, report, profile


def test_scope_removes_only_reviewed_lines_and_branch_exits_without_changing_raw(tmp_path):
    from pancake.coverage_scope import scoped_summary
    source, report, profile = _fixture(tmp_path)
    before = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    scope = scoped_summary(report, source, profile)
    assert scope["line_total"] == scope["line_covered"] == 3
    assert scope["branch_total"] == scope["branch_covered"] == 1
    assert scope["line_percent"] == scope["branch_percent"] == 100
    assert scope["excluded_lines"] == 1 and scope["excluded_branches"] == 1
    assert hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest() == before
    profile["exclusions"] = []
    assert scoped_summary(report, source, profile)["line_percent"] == 75


def test_scope_rejects_source_drift_unproven_rules_and_executed_exclusions(tmp_path):
    from pancake.coverage_scope import scoped_summary
    source, report, profile = _fixture(tmp_path)
    profile["exclusions"][0]["ranges"] = [[3, 5]]
    with pytest.raises(ValueError, match="executed"):
        scoped_summary(report, source, profile)
    profile["exclusions"][0]["ranges"] = [[5, 5]]
    profile["exclusions"][0]["evidence"] = ""
    with pytest.raises(ValueError, match="evidence"):
        scoped_summary(report, source, profile)
    profile["exclusions"][0]["evidence"] = "Static source review"
    (source / "module.py").write_text("x = 0\n")
    with pytest.raises(ValueError, match="source"):
        scoped_summary(report, source, profile)
