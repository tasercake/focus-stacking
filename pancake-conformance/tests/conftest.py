"""Route live desktop smoke tests through the same runner boundary as the CLI."""
import pytest


def pytest_addoption(parser):
    parser.addoption("--target", help="Explicit target descriptor for live VM smoke cases")
    parser.addoption("--gui-vm", action="store_true", help="Run native smoke cases in configured macOS VM")
    parser.addoption("--gui-vm-persist", action="store_true", help="Keep test VM running")


@pytest.fixture
def native_case_runner(request, tmp_path):
    if not request.config.getoption("--gui-vm") or not request.config.getoption("--target"):
        pytest.skip("Live GUI smoke tests require --gui-vm and explicit --target; host GUI execution is disabled")
    from pancake_conformance.cli import main
    def run(case_id):
        arguments = ["run", "--target", request.config.getoption("--target"), "--case", case_id, "--output", str(tmp_path / "run")]
        if request.config.getoption("--gui-vm"):
            arguments.append("--gui-vm")
            if request.config.getoption("--gui-vm-persist"):
                arguments.append("--gui-vm-persist")
        assert main(arguments) == 0
    return run
