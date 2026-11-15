import json
import os
import subprocess
import sys

from stack_conformance import main


def test_single_entrypoint_lists_machine_readable_cases(capsys):
    assert main(["list", "--json"]) == 0
    records = json.loads(capsys.readouterr().out)
    assert records
    assert len({x["id"] for x in records}) == len(records)
    assert all(set(x) == {"id", "suite", "description"} for x in records)


def test_entrypoint_rejects_empty_selection(tmp_path, capsys):
    assert main(["run", "--case", "does-not-exist", "--output", str(tmp_path / "run")]) == 2
    assert "no cases" in capsys.readouterr().err


def test_entrypoint_has_exact_suite_selection(capsys):
    assert main(["list", "--suite", "cli", "--json"]) == 0
    assert all(x["suite"] == "cli" for x in json.loads(capsys.readouterr().out))


def test_optimized_execution_cannot_disable_conformance_checks():
    result = subprocess.run([sys.executable, "-O", "-m", "stack_conformance", "list", "--json"],
                            capture_output=True, text=True, env=dict(os.environ), check=False)
    assert result.returncode != 0
    assert "optimization" in result.stderr.lower()


def test_coverage_threshold_validation_precedes_target_execution(capsys):
    assert main(["run", "--min-line-coverage", "101", "--target", "/missing-target.toml"]) == 2
    assert "coverage thresholds" in capsys.readouterr().err
