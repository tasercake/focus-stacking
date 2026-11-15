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


def test_state_directory_is_declarative_and_case_owned(tmp_path):
    import pytest
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    target = TargetSpec("example", tmp_path, ("unused",), state={"compute_cache": "{home}/cache"})
    ctx = CaseContext(target, tmp_path / "case")
    assert ctx.state_directory("compute_cache") == tmp_path / "case/home/cache"
    assert not ctx.state_directory("compute_cache").exists()
    target.state["outside"] = str(tmp_path / "external")
    with pytest.raises(ValueError, match="case"):
        ctx.state_directory("outside")


def test_ui_service_endpoints_use_declarative_target_mapping(tmp_path, monkeypatch):
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    import stack_conformance.macos_ui as native
    import pytest
    seen = {}
    monkeypatch.setattr(native, "open_session", lambda *args, **kwargs: seen.update(kwargs))
    target = TargetSpec("example", tmp_path, ("unused",), gui=("unused",),
                        services={"updates": "TEST_RELEASE_ENDPOINT"})
    ctx = CaseContext(target, tmp_path / "case")
    ctx.open_ui(service_endpoints={"updates": "http://127.0.0.1:8123/releases"})
    assert seen["env"]["TEST_RELEASE_ENDPOINT"] == "http://127.0.0.1:8123/releases"
    with pytest.raises(ValueError, match="service"):
        ctx.open_ui(service_endpoints={"unknown": "http://127.0.0.1:8123"})
