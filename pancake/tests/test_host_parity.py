"""A guest GUI verdict cannot pass until its host CLI comparison passes."""
from pathlib import Path
import sys

import pytest

from pancake.context import CaseContext
from pancake.model import CaseResult
from pancake.target import TargetSpec


@pytest.mark.parametrize("changed", [False, True])
def test_host_resolves_deferred_gui_pixels_with_actual_cli(tmp_path, changed):
    from PIL import Image
    from pancake.runner import verify_guest_parity
    case_dir = tmp_path / "fetched/cases/gui"
    ctx = CaseContext(None, case_dir, environment={"PANCAKE_VM_GUEST": "1"})
    fixture = ctx.fixture("focus")
    output = case_dir / "gui.png"
    with Image.open(fixture.paths[0]) as image:
        if changed:
            image = Image.new("RGB", image.size, (0, 0, 0))
        image.save(output)
    ctx.record_output(output, "gui")
    ctx.assert_cli_parity(output, fixture, mean_limit=0, max_limit=0, method="example")
    script = tmp_path / "target.py"
    script.write_text('import sys,shutil\na=sys.argv\nshutil.copyfile(a[a.index("--input")+1],a[a.index("--output")+1])\n')
    target = TargetSpec("example", tmp_path, (sys.executable, str(script)), stack={"options": {
        "method": "--method", "device": {"cpu": ["--cpu"]}, "kernel_size": "--kernel",
        "pyramid_levels": "--levels", "scale_factor": "--scale"}})
    result = CaseResult("gui", "interface", "pending", 0, notes=ctx.notes,
                        outputs={"gui": "gui.png"}, execution_environment="vm")
    verify_guest_parity(result, target=target, artifacts=tmp_path / "fetched", environment={})
    assert result.status == ("failed" if changed else "passed")
    assert result.notes["host_verification_pending"] is False
    assert (case_dir / "host-parity/call-01/stdout.txt").is_file()
    assert len(result.notes["requests"]) == 1
    assert Path(result.outputs["output-01.png"]) == Path("host-parity/output-01.png")


def test_guest_phase_is_pending_in_report_until_host_checks(tmp_path):
    from pancake.model import Case
    from pancake.runner import run_cases
    def native(ctx):
        ctx.note("host_verification_pending", True)
    results = run_cases([Case("gui", "interface", native)], target=None, output=tmp_path)
    assert results[0].status == "pending"
