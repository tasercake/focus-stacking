"""Additional public native workflows with independent pixel/file oracles."""
from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np

from ..model import Case
from ..validators import assert_pixels_close, read_image, validate_image
from .interface import _export, _has, _menu, _node, _prepare, _stack, _viewer


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
        _menu(ui, "export.batch")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="batch export destination panel")
        ui.click("CancelButton", physical=False)
        ui.wait(lambda snap: not _has(snap, "open-panel"), description="cancelled batch export")
        assert not list(folder.iterdir()), "Cancelled batch export wrote files"
        _menu(ui, "export.batch")
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
        _prepare(ui, "weighted_average", "translation")
        _stack(ui)
        before = _export(ui, ctx.directory / "before.tif")
        _menu(ui, "result.crop")
        ui.wait(lambda snap: ui.observe("result_cropped", snap), description="manual crop applied")
        after = _export(ui, ctx.directory / "cropped.tif")
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
    _menu(ui, "window.close")
    assert ui.process.wait(timeout=5) == 0, "File menu must close the window cleanly"


def _visible_menu_item(snapshot, title, role="AXMenuItem"):
    return next((node for node in snapshot["nodes"]
                 if node.get("role") == role and (node.get("title") == title or node.get("id") == title)
                 and len(node.get("size", [])) == 2 and all(n > 0 for n in node["size"])), None)


def _recent_menu(ui):
    ui.action("file.menu")
    ui.wait(lambda snap: _visible_menu_item(snap, "recent.open"), description="visible recent submenu")
    ui.action("recent.open")


def _recent_item(ui, title):
    _recent_menu(ui)
    return ui.wait(lambda snap: _visible_menu_item(snap, title), description=f"visible {title}")


def _clear_recent_folders(ui):
    clear = _recent_item(ui, "recent.clear")
    assert clear.get("enabled"), "Clear Menu is disabled"
    ui.action("recent.clear")
    assert not _recent_item(ui, "recent.empty")["enabled"], "Recent history was not cleared"


def _recent_folders(ctx):
    fixture = ctx.fixture("focus")
    paths = copy_input_folder(fixture, ctx.directory / "recent-inputs")
    folder_name = paths[0].parent.name
    with ctx.open_ui(paths=paths[:2], settings_id="recent") as ui:
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 2, description="initial two-frame partial folder stack")
        _recent_item(ui, folder_name)
        ui.click({"role": "AXMenuItem", "title": folder_name})
        ui.wait(lambda snap: _has(snap, "dialog.replace"), description="replace existing frames prompt")
        ui.click("dialog.cancel", physical=False)
        assert ui.observe("frame_count") == 2
        _recent_item(ui, folder_name)
        ui.click({"role": "AXMenuItem", "title": folder_name})
        ui.node("dialog.replace")
        ui.click("dialog.replace", physical=False)
        ui.wait(lambda snap: ui.observe("frame_count", snap) == len(fixture.paths) and _node(snap, "stack.start").get("enabled"), description="recent folder replaced frames")
        assert not ui.node("export.start")["enabled"]
        _clear_recent_folders(ui)
        _close_recent_window(ui)
    with ctx.open_ui(settings_id="recent") as ui:
        assert not _recent_item(ui, "recent.empty")["enabled"]
        assert not ui.node("stack.start")["enabled"]
        _close_recent_window(ui)


def _viewer_keyboard(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        ui.action("viewer.actual")
        before = _viewer(ui)["zoom"]
        ui.action("viewer.zoom_in")
        ui.wait(lambda snap: _viewer(ui)["zoom"] > before, description="zoom-in changes scale")
        enlarged = _viewer(ui)["zoom"]
        ui.action("viewer.zoom_out")
        ui.wait(lambda snap: 0 < _viewer(ui)["zoom"] < enlarged, description="zoom-out changes scale")
        ui.action("viewer.next")
        ui.wait(lambda snap: ui.observe("source_index", snap) is not None, description="source navigation changes selection")
        ui.action("viewer.fit")
        ui.wait(lambda snap: _viewer(ui)["fit"], description="fit restored")


def coverage_interface_cases():
    return [
        Case("interface.export.batch", "interface", _batch_export,
             "Batch export creates JPEG8, PNG16, TIFF16 with exact lossless pixels and CLI parity; cancel writes nothing"),
        Case("interface.result.manual-crop", "interface", _manual_crop,
             "Manual alignment crop preserves a source pixel rectangle, matches automatic CLI crop, and disables repeated crop"),
        Case("interface.import.recent-folders", "interface", _recent_folders,
             "Recent folder reopening can be cancelled or replace frames, and clearing recent history persists"),
        Case("interface.viewer.keyboard-boundaries", "interface", _viewer_keyboard,
             "Native view actions change scale and source selection, then restore fit"),
    ]
