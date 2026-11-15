"""UI conformance through native accessibility, keyboard, pointer, and files.

No application imports, widget classes, or in-process business calls belong here.
"""
from __future__ import annotations

import json
import shutil
from types import SimpleNamespace

from ..macos_ui import find_node
from ..model import Case
from ..validators import validate_image

METHODS = ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion")
ALIGNMENTS = ("Off", "Shift only", "Shift + rotation", "Standard", "Full affine", "Focus breathing")


def _node(snapshot, identifier):
    return find_node(snapshot, identifier)


def _method_alignment(ctx):
    with ctx.open_ui() as ui:
        assert not ui.node("stack.start")["enabled"]
        assert not ui.node("export.start")["enabled"]
        for method in METHODS:
            ui.click(f"method.{method}", physical=False)
            ui.wait(lambda snap, method=method: _node(snap, f"method.{method}").get("value") == 1,
                    description=f"method {method} selected")
            snapshot = ui.snapshot()
            assert sum(_node(snapshot, f"method.{key}").get("value", 0) for key in METHODS) == 1
        for alignment in ALIGNMENTS:
            ui.select("alignment", alignment)
            ui.wait(lambda snap, alignment=alignment: _node(snap, "alignment").get("title") == alignment,
                    description=f"alignment {alignment} selected")


def _prepare(ui, method, alignment="Off"):
    ui.wait(lambda snap: _node(snap, "stack.start").get("enabled"), timeout=30, description="imported stack ready")
    ui.select("alignment", alignment)
    ui.click(f"method.{method}", physical=False)
    ui.wait(lambda snapshot: _node(snapshot, f"method.{method}").get("value") == 1,
            description=f"method {method} committed")
    if ui.node("autocrop").get("value"):
        ui.click("autocrop", physical=False)
        ui.wait(lambda snap: _node(snap, "autocrop").get("value") == 0, description="auto-crop disabled")
    if not ui.node("advanced").get("value"):
        ui.click("advanced")
    for identifier, value in (("parameter.kernel", 3), ("parameter.levels", 4), ("parameter.contrast", 0)):
        nodes = [node for node in ui.snapshot()["nodes"] if node.get("id") == identifier]
        if nodes:
            ui.edit(identifier, value)
            ui.wait(lambda snap, identifier=identifier, value=value: str(_node(snap, identifier).get("value")) == str(value), description=f"{identifier} committed")


def _stack(ui):
    ui.click("stack.start", position=(0.3, 0.5))
    ui.wait(lambda snap: _node(snap, "export.start").get("enabled"), timeout=120, description="stack result ready")


def _export(ui, path, fmt="TIFF", depth="16-bit"):
    ui.click("export.start")
    ui.wait(lambda snap: any(node.get("id") == "export.format" for node in snap["nodes"]), description="export options")
    label = {"TIFF": "TIFF (.tif)", "PNG": "PNG (.png)", "JPG": "JPEG (.jpg)", "EXR": "OpenEXR (.exr)"}[fmt]
    ui.select("export.format", label)
    if ui.node("export.depth").get("enabled"):
        ui.select("export.depth", depth)
    ui.click("export.confirm")
    return ui.save_file(path)


def _algorithm(ctx, method):
    fixture = ctx.fixture("focus" if method != "exposure_fusion" else "exposure")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, method)
        _stack(ui)
        output = _export(ui, ctx.directory / "gui.tif")
        ctx.record_output(output, "gui")
        ctx.note("gui_image", validate_image(output, shape=fixture.shape, dtype="uint16", min_range=100))
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method=method, bit_depth=16, output_format="tif")


def _has(snapshot, identifier):
    return any(node.get("id") == identifier for node in snapshot["nodes"])


def _menu(ui, title):
    ui.click({"role": "AXMenuItem", "title": title}, physical=False)


def _viewer(ui):
    return json.loads(ui.node("viewer")["description"])


def _startup(ctx):
    with ctx.open_ui() as ui:
        for identifier in ("stack.start", "export.start", "mode.compare"):
            assert not ui.node(identifier)["enabled"], identifier
        assert not _viewer(ui)["has_image"]
        ui.click("method.hybrid", physical=False)
        ui.wait(lambda snapshot: _node(snapshot, "method.hybrid").get("value") == 1,
                description="hybrid method committed")
        assert not ui.node("stack.start")["enabled"]


def _frame_rows(snapshot):
    frames = find_node(snapshot, {"id": "frames", "role": "AXList"})
    prefix = frames["path"]
    return [node for node in snapshot["nodes"] if len(node["path"]) == len(prefix) + 1 and node["path"][:len(prefix)] == prefix and node.get("role") == "AXRow"]


def _native_import(ctx):
    fixture = ctx.fixture("focus")
    inputs = ctx.directory / "import-inputs"
    inputs.mkdir()
    paths = []
    for path in fixture.paths:
        destination = inputs / path.name
        shutil.copyfile(path, destination)
        paths.append(destination)
    with ctx.open_ui() as ui:
        ui.click("import.files")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="native Open panel")
        ui.click("CancelButton")
        ui.wait(lambda snap: not _has(snap, "open-panel"), description="cancelled Open panel")
        assert not ui.node("stack.start")["enabled"]
        ui.click("import.files")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="native file import")
        ui.choose_file(paths[0])
        ui.wait(lambda snap: _has(snap, "frames") and len(_frame_rows(snap)) == 1, description="one imported frame")
        assert not ui.node("stack.start")["enabled"]
        _menu(ui, "Add Folder…")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="native folder import")
        ui.navigate_folder(inputs)
        ui.click("OKButton", physical=False)
        ui.wait(lambda snap: len(_frame_rows(snap)) == 3, description="folder import with duplicate suppression")
        assert ui.node("stack.start")["enabled"]
        ui.key("a", ("command",))
        ui.key("delete")
        ui.wait(lambda snap: not _node(snap, "stack.start")["enabled"], description="selected frames removed")


def _raw_import(ctx):
    fixture = ctx.fixture("bayer_dng")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        ui.wait(lambda snap: _viewer(ui)["has_image"], timeout=60, description="RAW source preview")
        _stack(ui)
        output = _export(ui, ctx.directory / "raw.tif")
        ctx.record_output(output, "raw-gui")
        ctx.note("image", validate_image(output, shape=(*fixture.shape[:2], 3), dtype="uint16", genuine_16bit=True))


def _formats(ctx):
    fixture = ctx.fixture("focus")
    choices = (("JPG", "8-bit", "jpg", "uint8"), ("PNG", "8-bit", "png", "uint8"),
               ("PNG", "16-bit", "png", "uint16"), ("TIFF", "8-bit", "tif", "uint8"),
               ("TIFF", "16-bit", "tif", "uint16"), ("EXR", "32-bit float", "exr", "float32"))
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        for index, (fmt, depth, extension, dtype) in enumerate(choices):
            output = _export(ui, ctx.directory / f"export-{index}.{extension}", fmt, depth)
            ctx.record_output(output, f"gui-{fmt}-{depth}")
            ctx.note(f"{fmt}-{depth}", validate_image(output, shape=fixture.shape, dtype=dtype, min_range=0.1))


def _viewer_workflow(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "hybrid")
        _stack(ui)
        ui.click("mode.compare")
        ui.wait(lambda snap: _viewer(ui)["compare"], description="comparison enabled")
        ui.drag("viewer", (0.5, 0.5), (0.7, 0.5))
        ui.wait(lambda snap: 0.65 < _viewer(ui)["split"] < 0.75, description="comparison divider moved")
        ui.click("mode.view")
        ui.click("viewer")
        ui.key("1")
        ui.wait(lambda snap: abs(_viewer(ui)["zoom"] - 1) < 1e-6, description="actual size")
        for _ in range(10):
            ui.key("=", ("command",))
        ui.wait(lambda snap: _viewer(ui)["zoom"] > 8, description="detail zoom")
        before = _viewer(ui)
        ui.drag("viewer", (0.35, 0.45), (0.6, 0.55))
        ui.wait(lambda snap: sum(abs(a-b) for a, b in zip(_viewer(ui)["center"], before["center"], strict=True)) > 1, description="panned image")
        locked = _viewer(ui)
        first_frame = _frame_rows(ui.snapshot())[0]
        ui.click({"path": first_frame["path"]})
        ui.wait(lambda snap: "frame 1 of" in str(_node(snap, "status").get("value", "")), timeout=8, description="source selected")
        after = _viewer(ui)
        assert abs(after["zoom"] - locked["zoom"]) < 1e-6
        assert max(abs(a-b) for a, b in zip(after["center"], locked["center"], strict=True)) < 1
        ui.key("right", ("command",))
        ui.wait(lambda snap: "frame 2 of" in str(_node(snap, "status").get("value", "")), timeout=8, description="keyboard image navigation")
        ui.key("0")
        ui.wait(lambda snap: _viewer(ui)["fit"], description="fit restored")


def _open_settings(ui):
    _menu(ui, "Settings…")
    ui.wait(lambda snap: _has(snap, "settings.theme"), description="settings window")


def _close_settings(ui):
    ui.click({"role": "AXButton", "title": "Close"})
    ui.wait(lambda snap: not _has(snap, "settings.theme"), description="settings closed")


def _settings(ctx):
    with ctx.open_ui(settings_id="preferences") as ui:
        _open_settings(ui)
        for title in ("Dark", "Light", "Match system", "Dark"):
            ui.select("settings.theme", title)
            ui.wait(lambda snap, title=title: _node(snap, "settings.theme").get("title") == title, description=f"theme {title}")
        for title in ("Always GPU", "Automatic (recommended)", "Always CPU"):
            ui.select("settings.device_mode", title)
            ui.wait(lambda snap, title=title: _node(snap, "settings.device_mode").get("title") == title, description=f"device {title}")
        assert _has(ui.snapshot(), "settings.lightroom.status")
        _close_settings(ui)
    with ctx.open_ui(settings_id="preferences") as ui:
        _open_settings(ui)
        assert ui.node("settings.theme")["title"] == "Dark"
        assert ui.node("settings.device_mode")["title"] == "Always CPU"
        _close_settings(ui)
    with ctx.open_ui(settings_id="fresh") as ui:
        _open_settings(ui)
        assert ui.node("settings.theme")["title"] == "Match system"
        _close_settings(ui)


def _layout(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        ui.wait(lambda snap: _has(snap, "frames"), description="frame sidebar")
        _menu(ui, "Show Sidebar")
        ui.wait(lambda snap: not _has(snap, "frames"), description="sidebar hidden")
        _menu(ui, "Show Sidebar")
        ui.wait(lambda snap: _has(snap, "frames"), description="sidebar restored")
        _menu(ui, "Show Inspector")
        ui.wait(lambda snap: not _has(snap, "method.hybrid"), description="inspector hidden")
        _menu(ui, "Show Inspector")
        ui.wait(lambda snap: _has(snap, "method.hybrid"), description="inspector restored")


def _advanced(ctx):
    with ctx.open_ui() as ui:
        ui.click("advanced")
        for method, expected, absent in (("laplacian", "parameter.contrast", "parameter.smoothing"),
                                         ("hybrid", "parameter.levels", "parameter.contrast"),
                                         ("weighted_average", "parameter.kernel", "parameter.levels"),
                                         ("depth_map", "parameter.smoothing", "parameter.kernel"),
                                         ("exposure_fusion", None, "parameter.slab")):
            ui.click(f"method.{method}", physical=False)
            ui.wait(lambda snapshot, method=method: _node(snapshot, f"method.{method}").get("value") == 1,
                    description=f"method {method} committed")
            snapshot = ui.snapshot()
            if expected:
                assert _has(snapshot, expected), (method, expected)
            assert not _has(snapshot, absent), (method, absent)


def _unsaved(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        ui.key("n", ("command",))
        ui.wait(lambda snap: any(node.get("title") == "Discard" for node in snap["nodes"]), description="unsaved result warning")
        ui.click({"role": "AXButton", "title": "Cancel"})
        assert ui.node("export.start")["enabled"]
        ui.key("n", ("command",))
        ui.wait(lambda snap: any(node.get("title") == "Discard" for node in snap["nodes"]), description="discard warning repeated")
        ui.click({"role": "AXButton", "title": "Discard"})
        ui.wait(lambda snap: not _node(snap, "stack.start")["enabled"] and not _node(snap, "export.start")["enabled"], description="new stack after explicit discard")


def _lifecycle(ctx):
    fixture = ctx.fixture("lifecycle")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "laplacian", "Focus breathing")
        ui.click("stack.start", position=(0.3, 0.5))
        ui.wait(lambda snap: _has(snap, "stack.pause"), description="running stack")
        ui.click("stack.pause")
        ui.wait(lambda snap: _node(snap, "stack.pause").get("title") == "Resume", description="paused stack")
        ui.click("stack.pause")
        ui.wait(lambda snap: _node(snap, "stack.pause").get("title") == "Pause", description="resumed stack")
        ui.click("stack.stop")
        ui.wait(lambda snap: not _has(snap, "stack.pause") and _node(snap, "stack.start")["enabled"], timeout=120, description="cancelled stack settled")
        assert not ui.node("export.start")["enabled"]
        _stack(ui)
        assert ui.node("export.start")["enabled"]


def _gpu(ctx):
    from .devices import require_backend
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _open_settings(ui)
        ui.select("settings.device_mode", "Always GPU")
        _close_settings(ui)
        _prepare(ui, "hybrid")
        _stack(ui)
        events = [json.loads(line) for line in (ui.directory / "events.jsonl").read_text().splitlines() if line.strip()]
        result = SimpleNamespace(returncode=0, stderr="", diagnostics={"events": events})
        event = require_backend(result, "gpu")
        assert event["requested_backend"] == "gpu"
        ctx.note("execution", event)


def _alignment_crop(ctx):
    fixture = ctx.fixture("translation")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average", "Shift only")
        ui.click("autocrop", physical=False)
        ui.wait(lambda snap: _node(snap, "autocrop").get("value") == 1, description="auto-crop enabled")
        _stack(ui)
        output = _export(ui, ctx.directory / "aligned-gui.tif")
        ctx.record_output(output, "aligned-gui")
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method="weighted_average", align=True, alignment_mode="translation", auto_crop=True,
                          bit_depth=16, output_format="tif")


def interface_cases():
    from functools import partial
    return [Case("interface.controls.method-alignment", "interface", _method_alignment,
                 "Native controls preserve exclusive method selection and all alignment choices"),
            *[Case(f"interface.algorithm.{method}", "interface", partial(_algorithm, method=method),
                   "Native method selection, processing, 16-bit export, and CLI pixel parity") for method in METHODS],
            Case("interface.startup.empty", "interface", _startup, "Empty workspace disables operations that require images"),
            Case("interface.import.native-dialogs", "interface", _native_import, "Real native file/folder import, cancellation, duplicate suppression, and removal"),
            Case("interface.import.raw", "interface", _raw_import, "RAW preview, processing, and 16-bit native export"),
            Case("interface.export.formats", "interface", _formats, "Native export options and all supported formats and bit depths"),
            Case("interface.viewer.navigation-comparison", "interface", _viewer_workflow, "Native comparison divider, zoom, pan, and fixed-view source navigation"),
            Case("interface.layout.panels", "interface", _layout, "Sidebar and inspector visibility through native menu actions"),
            Case("interface.controls.advanced-visibility", "interface", _advanced, "Method-specific advanced controls follow selected algorithm"),
            Case("interface.workflow.unsaved-discard", "interface", _unsaved, "Unsaved work can be kept or explicitly discarded"),
            Case("interface.lifecycle.pause-cancel", "interface", _lifecycle, "Real worker pause/resume/cancel and successful reuse"),
            Case("interface.compute.gpu", "interface", _gpu, "GUI GPU preference reaches actual GPU completion", ("physical_gpu",)),
            Case("interface.alignment.crop", "interface", _alignment_crop, "GUI alignment and crop agree with CLI pixels")]
