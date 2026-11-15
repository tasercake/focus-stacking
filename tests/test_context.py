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
