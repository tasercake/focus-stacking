"""Route live desktop smoke tests through the same runner boundary as the CLI."""
import pytest


def pytest_addoption(parser):
    parser.addoption("--target", help="Explicit target descriptor for live VM smoke cases")
    parser.addoption("--gui-desktop", action="store_true", help="Run native smoke cases on isolated Linux desktop")
    parser.addoption("--gui-vm", action="store_true", help="Run native smoke cases in configured macOS VM")
    parser.addoption("--gui-vm-persist", action="store_true", help="Keep test VM running")


@pytest.fixture
def native_case_runner(request, tmp_path):
    if not (request.config.getoption("--gui-vm") or request.config.getoption("--gui-desktop")) or not request.config.getoption("--target"):
        pytest.skip("Live GUI smoke tests require --gui-vm or --gui-desktop and explicit --target")
    from pancake_conformance.cli import main
    def run(case_id):
        arguments = ["run", "--target", request.config.getoption("--target"), "--case", case_id, "--output", str(tmp_path / "run")]
        if request.config.getoption("--gui-vm"):
            arguments.append("--gui-vm")
            if request.config.getoption("--gui-vm-persist"):
                arguments.append("--gui-vm-persist")
        code = main(arguments)
        if code:
            # CI must expose target startup errors, not just the wrapper assertion.
            from pathlib import Path
            import json
            report = tmp_path / "run" / "report.json"
            if report.exists():
                for case in json.loads(report.read_text())["cases"]:
                    if case.get("error"):
                        print(case["error"])
            for log in (tmp_path / "run").rglob("target.stderr"):
                print(f"{Path(log).name}:\n{log.read_text()}")
        assert code == 0
    return run
