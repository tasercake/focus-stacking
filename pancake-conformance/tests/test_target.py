import sys
from pathlib import Path

import pytest


def test_default_reference_descriptor_uses_app_subdirectory():
    from pancake_conformance.cli import _parser
    from pancake_conformance.target import TargetSpec
    project = Path(__file__).resolve().parents[1]
    descriptor_path = _parser().parse_args(["run"]).target
    assert descriptor_path == project / "targets/chimpstackr/chimpstackr.toml"
    target = TargetSpec.load(descriptor_path)
    assert target.root == project.parent / "submodules/ChimpStackr"
    assert target.coverage_scope == descriptor_path.parent / "chimpstackr-coverage.json"
    assert target.coverage_scope.is_file()


def descriptor(tmp_path, extra=""):
    path = tmp_path / "target.toml"
    path.write_text('schema_version = 1\nname = "example"\nroot = "."\ncli = ["{python}", "-m", "example"]\n'
                    '[stack]\ninput = ["--input", "{inputs}"]\noutput = ["--output", "{output}"]\n'
                    '[stack.options]\nmethod = "--method"\nalign = "--align"\n'
                    'device = { cpu = ["--cpu"], gpu = ["--gpu"], auto = [] }\n' + extra)
    return path


def test_descriptor_preserves_argv_boundaries(tmp_path):
    from pancake_conformance.target import TargetSpec
    target = TargetSpec.load(descriptor(tmp_path))
    assert target.root == tmp_path
    assert target.command("cli") == [sys.executable, "-m", "example"]
    args = target.stack_arguments([Path("space name.png"), Path("另一个.png")], Path("out.tif"),
                                  {"method": "hybrid", "align": True, "device": "cpu"})
    assert args == ["--input", "space name.png", "另一个.png", "--output", "out.tif",
                    "--method", "hybrid", "--align", "--cpu"]


def test_unsupported_options_cannot_silently_pass(tmp_path):
    from pancake_conformance.target import TargetSpec
    target = TargetSpec.load(descriptor(tmp_path))
    with pytest.raises(ValueError, match="unsupported"):
        target.stack_arguments([], Path("out.png"), {"invented": 1})


def test_descriptor_rejects_unknown_schema(tmp_path):
    from pancake_conformance.target import TargetSpec
    path = descriptor(tmp_path)
    path.write_text(path.read_text().replace("schema_version = 1", "schema_version = 99"))
    with pytest.raises(ValueError, match="schema"):
        TargetSpec.load(path)


def test_command_overrides_do_not_execute_shell(tmp_path):
    from pancake_conformance.target import TargetSpec
    target = TargetSpec.load(descriptor(tmp_path))
    assert target.with_commands(cli=[sys.executable, "literal;$(whoami)"]).command("cli")[-1] == "literal;$(whoami)"


def test_descriptor_rejects_empty_command_override(tmp_path):
    from pancake_conformance.target import TargetSpec
    with pytest.raises(ValueError, match="command"):
        TargetSpec.load(descriptor(tmp_path)).with_commands(cli=[])


def test_command_preserves_literal_json_arguments(tmp_path):
    from pancake_conformance.target import TargetSpec
    target = TargetSpec("other", tmp_path, ("other", "--config", '{"mode":"cpu"}', "{target}"))
    assert target.command("cli") == ["other", "--config", '{"mode":"cpu"}', str(tmp_path)]


def test_coverage_scope_path_is_relative_to_descriptor(tmp_path):
    from pancake_conformance.target import TargetSpec
    path = descriptor(tmp_path)
    path.write_text(path.read_text().replace('name = "example"', 'name = "example"\ncoverage_scope = "scope.json"'))
    (tmp_path / "scope.json").write_text('{}')
    assert TargetSpec.load(path).coverage_scope == tmp_path / "scope.json"
