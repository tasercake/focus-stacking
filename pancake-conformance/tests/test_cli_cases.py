from pathlib import Path
from types import SimpleNamespace


def test_invalid_method_checks_configured_argument_and_offending_value(tmp_path):
    from pancake_conformance.cases.cli import cli_cases
    from pancake_conformance.target import TargetSpec
    target = TargetSpec("other", tmp_path, ("other",), stack={
        "input": ["--sources", "{inputs}"], "output": ["--dest", "{output}"],
        "options": {"method": "--fusion"}})
    commands = []
    def command(args):
        commands.append(args)
        return SimpleNamespace(returncode=2, stderr="invalid method __invalid_method__", stdout="")
    ctx = SimpleNamespace(target=target, directory=tmp_path,
                          fixture=lambda name: SimpleNamespace(paths=(Path("one.png"), Path("two.png"))),
                          command=command)
    case = next(c for c in cli_cases() if c.id == "cli.reject.method")
    case.run(ctx)
    assert "--fusion" in commands[0]
    assert "__invalid_method__" in commands[0]
    assert "--method" not in commands[0]
