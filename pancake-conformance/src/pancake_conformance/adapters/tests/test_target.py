from pathlib import Path


def test_reference_descriptor_resolves_source_and_scope():
    from pancake_conformance.target import TargetSpec
    path = Path(__file__).resolve().parents[1] / "chimpstackr_reference/chimpstackr.toml"
    target = TargetSpec.load(path)
    assert target.root == path.parents[5] / "submodules/ChimpStackr"
    assert target.coverage_source == target.root / "src"
    assert target.runtime_project == path.parent
    assert target.coverage_scope == path.parent / "chimpstackr-coverage-v2.json"
    assert target.coverage_scope.is_file()
