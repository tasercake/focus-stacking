"""Native workflow coverage keeps portable file and UI contracts."""
import importlib.util

import numpy as np
from PIL import Image
import png
import pytest
import tifffile


def test_gui_coverage_catalog_covers_public_workflows():
    assert importlib.util.find_spec("stack_conformance.cases.coverage_interface") is not None, "Native coverage workflows are missing"
    from stack_conformance.cases.coverage_interface import coverage_interface_cases

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
    from stack_conformance.cases.coverage_interface import validate_batch_exports

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    _write_batch(tmp_path, image)
    paths = validate_batch_exports(tmp_path, image.shape)
    assert {path.suffix for path in paths} == {".jpg", ".png", ".tif"}
    tifffile.imwrite(tmp_path / "result.tif", image + 1, photometric="rgb")
    with pytest.raises(AssertionError, match="pixel error"):
        validate_batch_exports(tmp_path, image.shape)


def test_batch_oracle_rejects_missing_format_and_unrelated_names(tmp_path):
    from stack_conformance.cases.coverage_interface import validate_batch_exports

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
    from stack_conformance.cases.coverage_interface import validate_manual_crop

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
    from stack_conformance.cases.coverage_interface import validate_manual_crop

    image = np.arange(12 * 16 * 3, dtype=np.uint16).reshape(12, 16, 3) * 83
    paths = [tmp_path / name for name in ("before.tif", "after.tif", "again.tif")]
    for path in paths:
        tifffile.imwrite(path, image, photometric="rgb")
    with pytest.raises(AssertionError, match="reduce both"):
        validate_manual_crop(*paths, image.shape)


def test_native_folder_inputs_exclude_fixture_truth_and_metadata(tmp_path):
    from stack_conformance.cases import coverage_interface
    from stack_conformance.fixtures import generate_fixture

    assert hasattr(coverage_interface, "copy_input_folder"), "Native folder fixture contains unrelated reference files"
    fixture = generate_fixture("focus", tmp_path / "generated")
    paths = coverage_interface.copy_input_folder(fixture, tmp_path / "native-inputs")
    assert len(paths) == 3
    assert {p.name for p in paths} == {p.name for p in fixture.paths}
    assert set(paths) == set((tmp_path / "native-inputs").iterdir())
    assert all(p.read_bytes() == original.read_bytes() for p, original in zip(paths, fixture.paths, strict=True))


class RecentMenuUI:
    """Closed native menus expose cached entries whose AXPress is a no-op."""
    def __init__(self, *, clear_works=True):
        self.stage = "closed"
        self.empty = False
        self.clear_works = clear_works

    def snapshot(self):
        return {"nodes": [
            {"role": "AXMenuBarItem", "title": "File", "path": [0], "size": [30, 20],
             "enabled": True, "selected": self.stage != "closed"},
            {"role": "AXMenuItem", "title": "Open Recent", "path": [0, 0],
             "size": [160, 20] if self.stage == "file" else [0, 0], "enabled": True},
            {"role": "AXMenuItem", "title": "No Recent Folders" if self.empty else "Clear Menu",
             "path": [0, 0, 0], "size": [150, 20] if self.stage == "recent" else [0, 0],
             "enabled": self.stage == "recent" and not self.empty},
        ]}

    def click(self, selector, *, physical=True):
        if not physical:
            return  # Mirrors the successful AXPress response on the hidden host entry.
        node = next(n for n in self.snapshot()["nodes"]
                    if all(n.get(k) == v for k, v in selector.items()))
        assert all(node["size"]) and node["enabled"], "Hidden/disabled entry was clicked"
        if node["title"] == "File":
            self.stage = "file"
        elif node["title"] == "Open Recent":
            self.stage = "recent"
        else:
            self.empty = self.clear_works
            self.stage = "closed"

    def wait(self, condition, **kwargs):
        result = condition(self.snapshot())
        if not result:
            raise TimeoutError(kwargs.get("description", "native menu state"))
        return result


def test_recent_menu_opens_native_hierarchy_instead_of_pressing_hidden_cache():
    from stack_conformance.cases.coverage_interface import _recent_menu
    ui = RecentMenuUI()
    _recent_menu(ui)
    assert ui.stage == "recent", "Recent submenu remained hidden after successful AXPress"


def test_recent_menu_waits_for_pending_confirmation_to_close():
    from stack_conformance.cases.coverage_interface import _recent_menu

    class ClosingPromptUI(RecentMenuUI):
        closing_prompt = True

        def wait(self, condition, **kwargs):
            if self.closing_prompt:
                pending = self.snapshot()
                pending["nodes"].append({"role": "AXWindow", "subrole": "AXDialog"})
                result = condition(pending)
                if result:
                    return result
                self.closing_prompt = False
            return super().wait(condition, **kwargs)

        def click(self, selector, **kwargs):
            assert not self.closing_prompt, "File menu was clicked before confirmation closed"
            super().click(selector, **kwargs)

    ui = ClosingPromptUI()
    _recent_menu(ui)
    assert ui.stage == "recent"


def test_recent_clear_requires_visible_empty_state_before_restart():
    from stack_conformance.cases import coverage_interface
    ui = RecentMenuUI()
    coverage_interface._clear_recent_folders(ui)
    assert ui.empty and ui.stage == "recent"
    assert not ui.snapshot()["nodes"][-1]["enabled"]
    with pytest.raises(TimeoutError, match="No Recent Folders"):
        coverage_interface._clear_recent_folders(RecentMenuUI(clear_works=False))


def test_recent_clear_waits_for_native_menu_close_before_reopening():
    from stack_conformance.cases.coverage_interface import _clear_recent_folders

    class ClosingMenuUI(RecentMenuUI):
        closing_menu = False

        def click(self, selector, **kwargs):
            assert not self.closing_menu, "Menu was clicked before previous selection closed it"
            super().click(selector, **kwargs)
            if selector.get("title") == "Clear Menu":
                self.closing_menu = True
                self.stage = "recent"

        def wait(self, condition, **kwargs):
            if self.closing_menu:
                result = condition(self.snapshot())
                if result:
                    return result
                self.closing_menu = False
                self.stage = "closed"
            return super().wait(condition, **kwargs)

    ui = ClosingMenuUI()
    _clear_recent_folders(ui)
    assert ui.empty and ui.stage == "recent"
