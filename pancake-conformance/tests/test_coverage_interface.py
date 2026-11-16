"""Native workflow coverage keeps portable file and UI contracts."""
import importlib.util

import numpy as np
from PIL import Image
import png
import pytest
import tifffile


def test_gui_coverage_catalog_covers_public_workflows():
    assert importlib.util.find_spec("pancake_conformance.cases.coverage_interface") is not None, "Native coverage workflows are missing"
    from pancake_conformance.cases.coverage_interface import coverage_interface_cases

    cases = coverage_interface_cases()
    assert {case.id for case in cases} == {
        "interface.export.batch", "interface.result.manual-crop",
        "interface.import.recent-folders", "interface.viewer.keyboard-boundaries",
    }
    assert all(case.suite == "interface" and case.description for case in cases)
    assert all(not case.required_capabilities for case in cases)


def _write_batch(directory, image):
    directory.mkdir(exist_ok=True)
    tifffile.imwrite(directory / "result.tif", image, photometric="rgb")
    height, width = image.shape[:2]
    with (directory / "result.png").open("wb") as file:
        png.Writer(width, height, greyscale=False, bitdepth=16).write(file, image.reshape(height, width * 3).tolist())
    Image.fromarray(np.rint(image.astype(float) / 257).astype(np.uint8)).save(directory / "result.jpg", quality=95)


def test_batch_oracle_checks_three_precisions_and_lossless_identity(tmp_path):
    from pancake_conformance.cases.coverage_interface import validate_batch_exports

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    _write_batch(tmp_path, image)
    paths = validate_batch_exports(tmp_path, image.shape)
    assert {path.suffix for path in paths} == {".jpg", ".png", ".tif"}
    tifffile.imwrite(tmp_path / "result.tif", image + 1, photometric="rgb")
    with pytest.raises(AssertionError, match="pixel error"):
        validate_batch_exports(tmp_path, image.shape)


def test_batch_oracle_rejects_missing_format_and_unrelated_names(tmp_path):
    from pancake_conformance.cases.coverage_interface import validate_batch_exports

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    _write_batch(tmp_path, image)
    (tmp_path / "result.jpg").unlink()
    with pytest.raises(AssertionError, match="three batch"):
        validate_batch_exports(tmp_path, image.shape)
    _write_batch(tmp_path, image)
    (tmp_path / "result.jpg").rename(tmp_path / "other.jpg")
    with pytest.raises(AssertionError, match="same result"):
        validate_batch_exports(tmp_path, image.shape)


def test_manual_crop_oracle_checks_subset_geometry_and_noop_identity(tmp_path):
    from pancake_conformance.cases.coverage_interface import validate_manual_crop

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    cropped = image[2:-1, 3:-2].copy()
    paths = [tmp_path / name for name in ("before.tif", "after.tif", "again.tif")]
    for path, pixels in zip(paths, (image, cropped, cropped), strict=True):
        tifffile.imwrite(path, pixels, photometric="rgb")
    validate_manual_crop(*paths, image.shape)
    tifffile.imwrite(paths[2], cropped + 1, photometric="rgb")
    with pytest.raises(AssertionError, match="pixel error"):
        validate_manual_crop(*paths, image.shape)
    tifffile.imwrite(paths[1], cropped + 2, photometric="rgb")
    with pytest.raises(AssertionError, match="rectangular subset"):
        validate_manual_crop(*paths, image.shape)


def test_manual_crop_oracle_rejects_unchanged_shape(tmp_path):
    from pancake_conformance.cases.coverage_interface import validate_manual_crop

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    paths = [tmp_path / name for name in ("before.tif", "after.tif", "again.tif")]
    for path in paths:
        tifffile.imwrite(path, image, photometric="rgb")
    with pytest.raises(AssertionError, match="reduce both"):
        validate_manual_crop(*paths, image.shape)


def test_native_folder_inputs_exclude_fixture_truth_and_metadata(tmp_path):
    from pancake_conformance.cases import coverage_interface
    from pancake_conformance.fixtures import generate_fixture

    assert hasattr(coverage_interface, "copy_input_folder"), "Native folder fixture contains unrelated reference files"
    fixture = generate_fixture("focus", tmp_path / "generated")
    paths = coverage_interface.copy_input_folder(fixture, tmp_path / "native-inputs")
    assert len(paths) == 3
    assert {p.name for p in paths} == {p.name for p in fixture.paths}
    assert set(paths) == set((tmp_path / "native-inputs").iterdir())
    assert all(p.read_bytes() == original.read_bytes() for p, original in zip(paths, fixture.paths, strict=True))


def test_recent_workflow_opens_target_declared_action():
    from types import SimpleNamespace
    from pancake_conformance.cases.coverage_interface import _recent_menu
    actions = []
    def wait(predicate, **kwargs):
        assert predicate({"nodes": [{"id": "recent.open", "role": "AXMenuItem", "size": [100, 20]}]})
    _recent_menu(SimpleNamespace(action=actions.append, wait=wait))
    assert actions == ["file.menu", "recent.open"]


def test_recent_clear_checks_observed_empty_state():
    from pancake_conformance.cases.coverage_interface import _clear_recent_folders
    state = {"empty": False}
    def action(name):
        if name == "recent.clear":
            state["empty"] = True
    def wait(predicate, **kwargs):
        tree = {"nodes": [{"id": "recent.open", "role": "AXMenuItem", "size": [100, 20]},
                          {"id": "recent.clear", "role": "AXMenuItem", "size": [100, 20], "enabled": True},
                          {"id": "recent.empty", "role": "AXMenuItem", "size": [100, 20], "enabled": not state["empty"]}]}
        value = predicate(tree)
        assert value
        return value
    from types import SimpleNamespace
    _clear_recent_folders(SimpleNamespace(action=action, wait=wait))
    assert state["empty"]


def test_recent_menu_waits_for_each_visible_native_transition():
    from pancake_conformance.cases.coverage_interface import _recent_item
    class UI:
        phase = 'idle'
        def action(self, name):
            if name == 'file.menu':
                assert self.phase == 'idle'
                self.phase = 'file'
            elif name == 'recent.open':
                assert self.phase == 'file', 'Recent submenu opened before parent was observed'
                self.phase = 'recent'
        def wait(self, condition, **kwargs):
            name = 'recent.open' if self.phase == 'file' else 'folder'
            node = {'id': name, 'title': name, 'role': 'AXMenuItem', 'size': [100, 20]}
            result = condition({'nodes': [node]})
            assert result
            return result
    assert _recent_item(UI(), 'folder')['id'] == 'folder'
