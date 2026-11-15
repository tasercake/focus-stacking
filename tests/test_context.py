import hashlib


def test_stack_records_hashes_of_actual_inputs(tmp_path):
    from stack_conformance.context import CaseContext
    from stack_conformance.model import ProcessResult
    from stack_conformance.target import TargetSpec
    target = TargetSpec("other", tmp_path, ("other",), stack={"options": {
        "device": {"cpu": ["--cpu"]}, "kernel_size": "--kernel", "pyramid_levels": "--levels", "scale_factor": "--scale"}})
    context = CaseContext(target, tmp_path / "case")
    source = tmp_path / "ad-hoc.png"
    source.write_bytes(b"generated input")
    context.command = lambda args: ProcessResult(args, 1, "", "expected test failure", 0)
    context.stack([source])
    actual = context.notes["requests"][0]["inputs"]
    assert actual == [{"name": "ad-hoc.png", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]
def test_guest_defers_cli_parity_and_rejects_direct_cli(tmp_path, monkeypatch):
    import pytest
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    target = TargetSpec("example", tmp_path, ("unused",))
    ctx = CaseContext(target, tmp_path / "case", environment={"CF_VM_GUEST": "1"})
    fixture = ctx.fixture("focus")
    output = ctx.directory / "gui.tif"
    output.write_bytes(b"GUI output")
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method="hybrid", output_format="tif", bit_depth=16)
    request = ctx.notes["host_parity_requests"][0]
    assert request["gui_output"] == "gui.tif"
    assert request["inputs"][0]["path"].startswith("fixtures/focus/")
    assert len(request["inputs"][0]["sha256"]) == 64
    assert request["options"]["method"] == "hybrid"
    with pytest.raises(RuntimeError, match="host"):
        ctx.command(["--help"])
