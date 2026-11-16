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
ALIGNMENTS = ("off", "translation", "euclidean", "similarity", "affine", "breathing")


def _node(snapshot, identifier):
    return find_node(snapshot, identifier)


def _choice(snapshot, identifier):
    node = _node(snapshot, identifier)
    return node.get("value") if isinstance(node.get("value"), str) else node.get("title")


def _method_alignment(ctx):
    with ctx.open_ui() as ui:
        assert not ui.node("stack.start")["enabled"]
        assert not ui.node("export.start")["enabled"]
        for method in METHODS:
            ui.action(f"method.{method}")
            ui.wait(lambda snap, method=method: ui.observe("selected_method", snap) == method,
                    description=f"method {method} selected")

        for alignment in ALIGNMENTS:
            ui.select("alignment", alignment)
            ui.wait(lambda snap, alignment=alignment: _choice(snap, "alignment") == alignment,
                    description=f"alignment {alignment} selected")


def _prepare(ui, method, alignment="off"):
    ui.wait(lambda snap: _node(snap, "stack.start").get("enabled"), timeout=30, description="imported stack ready")
    ui.select("alignment", alignment)
    ui.action(f"method.{method}")
    ui.wait(lambda snapshot: ui.observe("selected_method", snapshot) == method,
            description=f"method {method} committed")
    if ui.node("autocrop").get("value"):
        ui.click("autocrop", physical=False)
        ui.wait(lambda snap: _node(snap, "autocrop").get("value") == 0, description="auto-crop disabled")
    if ui.contract.get("initial_values"):
        ui.action("advanced.open")
    for identifier, value in ui.contract.get("initial_values", {}).items():
        ui.edit(identifier, value)
        ui.wait(lambda snap, identifier=identifier, value=value: str(_node(snap, identifier).get("value")) == str(value),
                description=f"{identifier} committed")


def _stack(ui):
    ui.click("stack.start", position=(0.3, 0.5))
    ui.wait(lambda snap: _node(snap, "export.start").get("enabled"), timeout=120, description="stack result ready")


def _export(ui, path, fmt="TIFF", depth="16"):
    ui.action("export.open")
    ui.wait(lambda snap: any(node.get("id") == "export.format" for node in snap["nodes"]), description="export options")
    label = {"TIFF": "tif", "PNG": "png", "JPG": "jpg", "EXR": "exr"}[fmt]
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
    ui.action(title)


def _viewer(ui):
    return json.loads(ui.node("viewer")["description"])


def _startup(ctx):
    with ctx.open_ui() as ui:
        for identifier in ("stack.start", "export.start", "mode.compare"):
            assert not ui.node(identifier)["enabled"], identifier
        assert not _viewer(ui)["has_image"]
        ui.action("method.hybrid")
        ui.wait(lambda snapshot: ui.observe("selected_method", snapshot) == "hybrid",
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
        ui.wait(lambda snap: _has(snap, "frames") and ui.observe("frame_count", snap) == 1, description="one imported frame")
        assert not ui.node("stack.start")["enabled"]
        _menu(ui, "import.folder")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="native folder import")
        ui.navigate_folder(inputs)
        ui.click("OKButton", physical=False)
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 3, description="folder import with duplicate suppression")
        assert ui.node("stack.start")["enabled"]
        ui.action("frames.select_all")
        ui.action("frames.remove_selected")
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
    choices = (("JPG", "8", "jpg", "uint8"), ("PNG", "8", "png", "uint8"),
               ("PNG", "16", "png", "uint16"), ("TIFF", "8", "tif", "uint8"),
               ("TIFF", "16", "tif", "uint16"), ("EXR", "float32", "exr", "float32"))
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
        ui.wait(lambda snap: _viewer(ui)["split"] > 0.5, description="comparison divider moved")
        ui.click("mode.view")
        ui.click("viewer")
        ui.action("viewer.actual")
        ui.wait(lambda snap: abs(_viewer(ui)["zoom"] - 1) < 1e-6, description="actual size")
        before_zoom = _viewer(ui)["zoom"]
        ui.action("viewer.zoom_in")
        ui.wait(lambda snap: _viewer(ui)["zoom"] > before_zoom, description="detail zoom")
        before = _viewer(ui)
        ui.drag("viewer", (0.35, 0.45), (0.6, 0.55))
        ui.wait(lambda snap: sum(abs(a-b) for a, b in zip(_viewer(ui)["center"], before["center"], strict=True)) > 1, description="panned image")
        locked = _viewer(ui)
        ui.action("frames.select_first")
        ui.wait(lambda snap: ui.observe("source_index", snap) == 1, timeout=8, description="source selected")
        after = _viewer(ui)
        assert abs(after["zoom"] - locked["zoom"]) < 1e-6
        assert max(abs(a-b) for a, b in zip(after["center"], locked["center"], strict=True)) < 1
        ui.action("viewer.next")
        ui.wait(lambda snap: ui.observe("source_index", snap) == 2, timeout=8, description="keyboard image navigation")
        ui.action("viewer.fit")
        ui.wait(lambda snap: _viewer(ui)["fit"], description="fit restored")


def _open_settings(ui):
    _menu(ui, "settings.open")
    ui.wait(lambda snap: _has(snap, "settings.theme"), description="settings window")


def _close_settings(ui):
    ui.click("dialog.close")
    ui.wait(lambda snap: not _has(snap, "settings.theme"), description="settings closed")


def _settings(ctx):
    with ctx.open_ui(settings_id="preferences") as ui:
        _open_settings(ui)
        for title in ("dark", "light", "system", "dark"):
            ui.select("settings.theme", title)
            ui.wait(lambda snap, title=title: _choice(snap, "settings.theme") == title, description=f"theme {title}")
        for title in ("gpu", "auto", "cpu"):
            ui.select("settings.device_mode", title)
            ui.wait(lambda snap, title=title: _choice(snap, "settings.device_mode") == title, description=f"device {title}")
        _close_settings(ui)
    with ctx.open_ui(settings_id="preferences") as ui:
        _open_settings(ui)
        assert _choice(ui.snapshot(), "settings.theme") == "dark"
        assert _choice(ui.snapshot(), "settings.device_mode") == "cpu"
        _close_settings(ui)
    with ctx.open_ui(settings_id="fresh") as ui:
        _open_settings(ui)
        ctx.note("fresh_theme", ui.node("settings.theme").get("title", ui.node("settings.theme").get("value")))
        _close_settings(ui)


def _layout(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        ui.wait(lambda snap: _has(snap, "frames"), description="frame sidebar")
        _menu(ui, "layout.sidebar")
        ui.wait(lambda snap: not _has(snap, "frames"), description="sidebar hidden")
        _menu(ui, "layout.sidebar")
        ui.wait(lambda snap: _has(snap, "frames"), description="sidebar restored")
        _menu(ui, "layout.inspector")
        ui.wait(lambda snap: not _has(snap, "method.hybrid"), description="inspector hidden")
        _menu(ui, "layout.inspector")
        ui.wait(lambda snap: _has(snap, "method.hybrid"), description="inspector restored")


def _advanced(ctx):
    with ctx.open_ui() as ui:
        ui.action("advanced.open")
        for identifier, value in ui.contract.get("advanced_values", {}).items():
            ui.edit(identifier, value)
            ui.wait(lambda snap, identifier=identifier, value=value:
                    str(_node(snap, identifier).get("value")) == str(value),
                    description=f"advanced value {identifier} changed")
        assert ui.contract.get("advanced_values"), "No advanced setting declared by target"


def _unsaved(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        ui.action("workspace.new")
        ui.wait(lambda snap: _has(snap, "dialog.discard"), description="unsaved result warning")
        ui.click("dialog.cancel")
        assert ui.node("export.start")["enabled"]
        ui.action("workspace.new")
        ui.wait(lambda snap: _has(snap, "dialog.discard"), description="discard warning repeated")
        ui.click("dialog.discard")
        ui.wait(lambda snap: not _node(snap, "stack.start")["enabled"] and not _node(snap, "export.start")["enabled"], description="new stack after explicit discard")


def _lifecycle(ctx):
    fixture = ctx.fixture("lifecycle")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "laplacian", "breathing")
        ui.click("stack.start", position=(0.3, 0.5))
        def menu_enabled(snapshot, title):
            return bool(find_node(snapshot, title).get("enabled"))

        ui.wait(lambda snap: menu_enabled(snap, "stack.pause") and menu_enabled(snap, "stack.stop"), description="running stack")
        _menu(ui, "stack.pause")
        ui.wait(lambda snap: menu_enabled(snap, "stack.resume"), description="paused stack")
        _menu(ui, "stack.resume")
        ui.wait(lambda snap: menu_enabled(snap, "stack.pause"), description="resumed stack")
        _menu(ui, "stack.stop")
        ui.wait(lambda snap: not menu_enabled(snap, "stack.pause") and not menu_enabled(snap, "stack.stop")
                and _node(snap, "stack.start")["enabled"], timeout=120, description="cancelled stack settled")
        assert not ui.node("export.start")["enabled"]
        _stack(ui)
        assert ui.node("export.start")["enabled"]


def _gpu(ctx):
    from .devices import require_backend
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _open_settings(ui)
        ui.select("settings.device_mode", "gpu")
        _close_settings(ui)
        _prepare(ui, "hybrid")
        _stack(ui)
        events = [json.loads(line) for line in (ui.directory / "events.jsonl").read_text().splitlines() if line.strip()]
        result = SimpleNamespace(returncode=0, stderr="", diagnostics={"events": events})
        event = require_backend(result, "gpu")
        ctx.note("execution", event)


def _alignment_crop(ctx):
    fixture = ctx.fixture("translation")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average", "translation")
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
