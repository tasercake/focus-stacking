"""Additional public native workflows with independent pixel/file oracles."""
from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np

from ..model import Case
from ..validators import assert_pixels_close, read_image, validate_image
from .interface import _export, _frame_rows, _has, _menu, _node, _prepare, _stack, _viewer


def validate_batch_exports(directory, shape):
    paths = sorted(Path(directory).iterdir())
    assert len(paths) == 3 and {path.suffix for path in paths} == {".jpg", ".png", ".tif"}, "Expected three batch export formats"
    assert len({path.stem for path in paths}) == 1, "Batch exports must name the same result"
    by_format = {path.suffix: path for path in paths}
    for extension, dtype in ((".jpg", "uint8"), (".png", "uint16"), (".tif", "uint16")):
        validate_image(by_format[extension], shape=shape, dtype=dtype, min_range=100)
    assert_pixels_close(by_format[".png"], by_format[".tif"], mean_limit=0, max_limit=0)
    return paths


def validate_manual_crop(before, after, repeated, shape):
    validate_image(before, shape=shape, dtype="uint16", min_range=100)
    validate_image(after, dtype="uint16", min_range=100)
    source, cropped = read_image(before), read_image(after)
    assert cropped.ndim == 3 and cropped.shape[2] == source.shape[2], "Crop changed image channels"
    h, w = cropped.shape[:2]
    assert 0 < h < source.shape[0] and 0 < w < source.shape[1], "Manual crop must reduce both image dimensions"
    candidates = np.argwhere(np.all(source[:source.shape[0] - h + 1, :source.shape[1] - w + 1] == cropped[0, 0], axis=2))
    assert any(np.array_equal(source[y:y + h, x:x + w], cropped) for y, x in candidates), "Crop must preserve one rectangular subset of source pixels"
    assert_pixels_close(repeated, after, mean_limit=0, max_limit=0)
    return {"source_shape": list(source.shape), "cropped_shape": list(cropped.shape)}


def _batch_export(ctx):
    fixture = ctx.fixture("focus")
    folder = ctx.directory / "batch"
    folder.mkdir()
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        _menu(ui, "Export JPEG, PNG and TIFF…")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="batch export destination panel")
        ui.click("CancelButton", physical=False)
        ui.wait(lambda snap: not _has(snap, "open-panel"), description="cancelled batch export")
        assert not list(folder.iterdir()), "Cancelled batch export wrote files"
        _menu(ui, "Export JPEG, PNG and TIFF…")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="batch export folder")
        ui.navigate_folder(folder)
        ui.click("OKButton", physical=False)
        ui.wait(lambda snap: len(list(folder.iterdir())) == 3 and not _has(snap, "open-panel"), description="three batch exports written")
        outputs = validate_batch_exports(folder, fixture.shape)
        for path in outputs:
            ctx.record_output(path, f"batch-{path.suffix[1:]}")
    for path in outputs:
        depth = 8 if path.suffix == ".jpg" else 16
        ctx.assert_cli_parity(path, fixture, mean_limit=1, max_limit=257 if depth == 16 else 2,
                              note=f"batch_{path.suffix[1:]}", method="weighted_average", bit_depth=depth,
                              quality=95, output_format=path.suffix[1:])


def _manual_crop(ctx):
    fixture = ctx.fixture("translation")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average", "Shift only")
        _stack(ui)
        before = _export(ui, ctx.directory / "before.tif")
        _menu(ui, "Auto-Crop Result")
        ui.wait(lambda snap: "Cropped the empty borders" in str(_node(snap, "status").get("value", "")), description="manual crop applied")
        after = _export(ui, ctx.directory / "cropped.tif")
        assert not ui.node({"role": "AXMenuItem", "title": "Auto-Crop Result"})["enabled"], "Repeated crop must be disabled after applying crop"
        repeated = _export(ui, ctx.directory / "cropped-again.tif")
        ctx.note("manual_crop", validate_manual_crop(before, after, repeated, fixture.shape))
        for name, path in (("uncropped", before), ("cropped", after), ("cropped-again", repeated)):
            ctx.record_output(path, name)
    ctx.assert_cli_parity(after, fixture, mean_limit=1, max_limit=257, method="weighted_average",
                          align=True, alignment_mode="translation", auto_crop=True, bit_depth=16, output_format="tif")


def copy_input_folder(fixture, directory):
    directory = Path(directory)
    directory.mkdir()
    paths = tuple(directory / path.name for path in fixture.paths)
    for source, destination in zip(fixture.paths, paths, strict=True):
        shutil.copyfile(source, destination)
    return paths


def _close_recent_window(ui):
    _menu(ui, "Close Window")
    assert ui.process.wait(timeout=5) == 0, "File menu must close the window cleanly"


def _visible_menu_item(snapshot, title, role="AXMenuItem"):
    return next((node for node in snapshot["nodes"]
                 if node.get("role") == role and node.get("title") == title
                 and len(node.get("size", [])) == 2 and all(n > 0 for n in node["size"])), None)


def _recent_menu(ui):
    # Cached submenu entries can accept AXPress without dispatching their action.
    def ready(snapshot):
        file_menu = _visible_menu_item(snapshot, "File", "AXMenuBarItem")
        return (file_menu and not file_menu.get("selected", False)
                and not any(node.get("subrole") == "AXDialog" for node in snapshot["nodes"])
                and _visible_menu_item(snapshot, "Open Recent") is None)

    ui.wait(ready, description="File menu ready after confirmation and previous menu close")
    ui.click({"role": "AXMenuBarItem", "title": "File"})
    recent = ui.wait(lambda snap: _visible_menu_item(snap, "Open Recent"),
                     description="visible Open Recent submenu")
    assert recent.get("enabled", True), "Open Recent is disabled"
    ui.click({"role": "AXMenuItem", "title": "Open Recent"})


def _recent_item(ui, title):
    _recent_menu(ui)
    return ui.wait(lambda snap: _visible_menu_item(snap, title), description=f"visible {title}")


def _clear_recent_folders(ui):
    clear = _recent_item(ui, "Clear Menu")
    assert clear.get("enabled"), "Clear Menu is disabled"
    ui.click({"role": "AXMenuItem", "title": "Clear Menu"})
    assert not _recent_item(ui, "No Recent Folders")["enabled"], "Recent history was not cleared"


def _recent_folders(ctx):
    fixture = ctx.fixture("focus")
    paths = copy_input_folder(fixture, ctx.directory / "recent-inputs")
    folder_name = paths[0].parent.name
    with ctx.open_ui(paths=paths[:2], settings_id="recent") as ui:
        ui.wait(lambda snap: len(_frame_rows(snap)) == 2, description="initial two-frame partial folder stack")
        _recent_item(ui, folder_name)
        ui.click({"role": "AXMenuItem", "title": folder_name})
        ui.wait(lambda snap: any(node.get("role") == "AXButton" and node.get("title") == "Replace" for node in snap["nodes"]), description="replace existing frames prompt")
        ui.click({"role": "AXButton", "title": "Cancel"}, physical=False)
        assert len(_frame_rows(ui.snapshot())) == 2
        _recent_item(ui, folder_name)
        ui.click({"role": "AXMenuItem", "title": folder_name})
        ui.node({"role": "AXButton", "title": "Replace"})
        ui.click({"role": "AXButton", "title": "Replace"}, physical=False)
        ui.wait(lambda snap: len(_frame_rows(snap)) == len(fixture.paths) and _node(snap, "stack.start").get("enabled"), description="recent folder replaced frames")
        assert not ui.node("export.start")["enabled"]
        _clear_recent_folders(ui)
        _close_recent_window(ui)
    with ctx.open_ui(settings_id="recent") as ui:
        assert not _recent_item(ui, "No Recent Folders")["enabled"]
        assert not ui.node("stack.start")["enabled"]
        _close_recent_window(ui)


def _viewer_keyboard(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        ui.click("mode.compare")
        ui.wait(lambda snap: _viewer(ui)["compare"], description="comparison before keyboard input")
        ui.focus("viewer")
        ui.wait(lambda snap: _node(snap, "viewer").get("focused"), description="viewer keyboard focus")
        for _ in range(12):
            ui.key("left", ("shift",))
        ui.wait(lambda snap: abs(_viewer(ui)["split"]) < 1e-6, description="comparison divider left limit")
        for _ in range(22):
            ui.key("right", ("shift",))
        ui.wait(lambda snap: abs(_viewer(ui)["split"] - 1) < 1e-6, description="comparison divider right limit")
        for _ in range(10):
            ui.key("left", ("shift",))
        ui.wait(lambda snap: abs(_viewer(ui)["split"] - 0.5) < 1e-6, description="comparison keyboard midpoint")
        ui.click("mode.view")
        ui.focus("viewer")
        ui.key("right", ("command",))
        ui.wait(lambda snap: "frame 1 of" in str(_node(snap, "status").get("value", "")), description="Next Image shortcut wraps from result to first source")
        ui.key("left", ("command",))
        ui.wait(lambda snap: "Weighted Average result" in str(_node(snap, "status").get("value", "")), description="Previous Image shortcut wraps back to result")
        _menu(ui, "Actual Size (100 %)")
        for _ in range(12):
            _menu(ui, "Zoom In")
        ui.wait(lambda snap: _viewer(ui)["zoom"] > 8, description="scrollable detail zoom")
        before = _viewer(ui)
        ui.scroll("viewer", 120)
        ui.wait(lambda snap: abs(_viewer(ui)["center"][1] - before["center"][1]) > 1, description="pixel wheel pans detail view")
        for _ in range(45):
            _menu(ui, "Zoom Out")
        minimum = _viewer(ui)["zoom"]
        assert minimum > 0, "Zoom must stay positive"
        _menu(ui, "Zoom Out")
        assert abs(_viewer(ui)["zoom"] - minimum) < 1e-9, "Zoom must stop at its lower limit"
        _menu(ui, "Zoom to Fit")
        ui.wait(lambda snap: _viewer(ui)["fit"], description="fit restored after keyboard and wheel navigation")


def coverage_interface_cases():
    return [
        Case("interface.export.batch", "interface", _batch_export,
             "Batch export creates JPEG8, PNG16, TIFF16 with exact lossless pixels and CLI parity; cancel writes nothing"),
        Case("interface.result.manual-crop", "interface", _manual_crop,
             "Manual alignment crop preserves a source pixel rectangle, matches automatic CLI crop, and disables repeated crop"),
        Case("interface.import.recent-folders", "interface", _recent_folders,
             "Recent folder reopening can be cancelled or replace frames, and clearing recent history persists"),
        Case("interface.viewer.keyboard-boundaries", "interface", _viewer_keyboard,
             "Native shortcut source wrapping, comparison limits, pixel wheel panning, and zoom bounds preserve a usable viewer"),
    ]
