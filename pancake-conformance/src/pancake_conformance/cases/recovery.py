"""Recoverable file failures through native controls and sandbox file operations."""
import json
from functools import partial

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from types import SimpleNamespace

from ..model import Case
from ..validators import assert_pixels_close, validate_image
from .coverage_interface import validate_batch_exports
from .devices import require_backend
from .interface import _close_settings, _open_settings, _export, _frame_rows, _has, _menu, _node, _prepare, _stack, _viewer


def _dialog(snapshot, title=None):
    return any(node.get("id") == "dialog.error" for node in snapshot["nodes"])


def _dismiss_error(ui, title=None):
    ui.wait(_dialog, description="recoverable error visible")
    ui.action("dialog.accept")
    ui.wait(lambda snap: not _dialog(snap), description="error dismissed")


def _missing_source(ctx):
    fixture = ctx.fixture("focus")
    original = {path: path.read_bytes() for path in fixture.paths}
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "hybrid")
        ui.wait(lambda snap: _viewer(ui)["has_image"], description="source preview loaded")
        try:
            for path in original:
                path.unlink()
            ui.click("stack.start", position=(0.3, 0.5))
            _dismiss_error(ui)
            ui.wait(lambda snap: _node(snap, "stack.start").get("enabled"),
                    description="failed worker restored processing controls")
            assert not ui.node("export.start")["enabled"], "Failed stack published an exportable result"
        finally:
            for path, data in original.items():
                path.write_bytes(data)
        _stack(ui)
        output = _export(ui, ctx.directory / "recovered.tif")
        validate_image(output, shape=fixture.shape, dtype="uint16", min_range=100)
        ctx.record_output(output, "recovered")
    ctx.assert_cli_parity(output, fixture, method="hybrid", bit_depth=16,
                          output_format="tif", mean_limit=1, max_limit=257)


def _batch_destination(ui, folder):
    _menu(ui, "export.batch")
    ui.wait(lambda snap: _has(snap, "open-panel"), description="batch destination")
    ui.navigate_folder(folder)
    ui.click("OKButton", physical=False)


def _batch_export(ctx):
    fixture = ctx.fixture("focus")
    folder = ctx.directory / "batch"
    folder.mkdir()
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        _batch_destination(ui, folder)
        ui.wait(lambda snap: len(list(folder.iterdir())) == 3 and not _has(snap, "open-panel"),
                description="initial batch export")
        paths = validate_batch_exports(folder, fixture.shape)
        original = {path: path.read_bytes() for path in paths}
        jpeg = next(path for path in paths if path.suffix == ".jpg")
        jpeg.unlink()
        jpeg.mkdir()  # Valid destination directory, but one output name cannot be a file.
        _batch_destination(ui, folder)
        _dismiss_error(ui)
        assert jpeg.is_dir(), "Failed export replaced the conflicting directory"
        for path in paths:
            if path != jpeg:
                assert path.read_bytes() == original[path], "Failed export altered an existing later output"
        assert ui.node("export.start")["enabled"], "Export failure lost the result"
        jpeg.rmdir()
        _batch_destination(ui, folder)
        ui.wait(lambda snap: jpeg.is_file() and not _has(snap, "open-panel"), description="batch export recovered")
        for path in validate_batch_exports(folder, fixture.shape):
            assert_pixels_close(path, _write_reference(ctx, path, original[path]), mean_limit=0, max_limit=0)
            ctx.record_output(path, f"recovered-{path.suffix[1:]}")


def _write_reference(ctx, path, data):
    reference = ctx.directory / ("before-" + path.name)
    reference.write_bytes(data)
    return reference


def _cancel_export(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        ui.click("export.start")
        ui.wait(lambda snap: _has(snap, "export.format"), description="export options")
        ui.click("dialog.cancel", physical=False)
        ui.wait(lambda snap: not _has(snap, "export.format"), description="cancelled export options")
        ui.click("export.start")
        ui.wait(lambda snap: _has(snap, "export.format"), description="export options reopened")
        ui.click("export.confirm")
        ui.wait(lambda snap: _has(snap, "save-panel"), description="native Save panel")
        ui.click("CancelButton", physical=False)
        ui.wait(lambda snap: not _has(snap, "save-panel"), description="cancelled Save panel")
        assert ui.node("export.start")["enabled"], "Cancellation lost the result"
        output = _export(ui, ctx.directory / "after-cancel.tif")
        validate_image(output, shape=fixture.shape, dtype="uint16", min_range=100)
        ctx.record_output(output, "after-cancel")


def _device_request(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _open_settings(ui)
        ui.select("settings.device_mode", "gpu")
        _close_settings(ui)
        _prepare(ui, "hybrid")
        _stack(ui)
        events = [json.loads(line) for line in (ui.directory / "events.jsonl").read_text().splitlines() if line.strip()]
        event = require_backend(SimpleNamespace(returncode=0, stderr="", diagnostics={"events": events}))
        output = _export(ui, ctx.directory / "device-request.tif")
        validate_image(output, shape=fixture.shape, dtype="uint16", min_range=100)
        ctx.record_output(output, "device-request")
        ctx.note("execution", event)
        ctx.note("gpu_hardware_exercised", event["actual_backend"] == "gpu")
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method="hybrid", bit_depth=16, output_format="tif")


def _folder_import(ctx):
    fixture = ctx.fixture("focus")
    folder, rejected = ctx.directory / "nested-inputs", ctx.directory / "unsupported-inputs"
    folder.mkdir()
    rejected.mkdir()
    nested = folder / "subfolder"
    nested.mkdir()
    for index, source in enumerate(fixture.paths):
        destination = (nested if index else folder) / source.name
        destination.write_bytes(source.read_bytes())
    (folder / "notes.txt").write_text("Not an image")
    (folder / ".ignored.png").write_bytes(b"ignored hidden file")
    hidden = folder / ".hidden"
    hidden.mkdir()
    (hidden / "ignored.png").write_bytes(fixture.paths[0].read_bytes())
    (rejected / "notes.txt").write_text("Not an image")
    with ctx.open_ui() as ui:
        _menu(ui, "import.folder")
        ui.wait(lambda snap: _has(snap, "open-panel"), description="folder import panel")
        ui.click("CancelButton", physical=False)
        ui.wait(lambda snap: not _has(snap, "open-panel"), description="folder import cancelled")
        assert not ui.node("stack.start")["enabled"]
        for destination in (folder, folder, rejected):
            _menu(ui, "import.folder")
            ui.wait(lambda snap: _has(snap, "open-panel"), description="folder import panel")
            ui.navigate_folder(destination)
            ui.click("OKButton", physical=False)
            ui.wait(lambda snap: not _has(snap, "open-panel"), description="folder import completed")
            assert ui.observe("frame_count") == 3, "Folder filtering changed accepted inputs"
        _prepare(ui, "weighted_average")
        _stack(ui)
        output = _export(ui, ctx.directory / "folder-result.tif")
        ctx.record_output(output, "folder-result")
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method="weighted_average", bit_depth=16, output_format="tif")


def _alignment_cascade(ctx, device):
    shape = (257, 4097, 3)
    noise = np.random.default_rng(76241).uniform(0, 255, shape).astype(np.float32)
    source = np.clip((gaussian_filter(noise, sigma=(2, 2, 0)) - 127) * 3 + 127, 0, 255).astype(np.uint8)
    shifted = np.roll(source, 2, axis=1)
    shifted[:, :2] = source[:, :1]
    paths = []
    for index, pixels in enumerate((source, shifted)):
        path = ctx.directory / f"wide-{index}.png"
        Image.fromarray(pixels).save(path)
        paths.append(path)
    result = ctx.stack(paths, method="weighted_average", device=device, align=True,
                       alignment_mode="euclidean", alignment_reference="previous", max_precision=device == "cpu")
    require_backend(result)
    shape = source.shape
    validate_image(result.output, shape=shape, dtype="uint8", min_range=100)
    ctx.note("alignment_error", assert_pixels_close(result.output, source,
             region=(16, shape[0] - 16, 16, shape[1] - 16), mean_limit=1, max_limit=3))
    ctx.note("alignment", {"source_shape": list(shape), "device": device})


def _close_unsaved(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, "weighted_average")
        _stack(ui)
        def prompt():
            ui.action("window.close")
            ui.wait(lambda snap: _has(snap, "dialog.discard_close"), description="unsaved close prompt")

        prompt()
        ui.click("dialog.cancel", physical=False)
        ui.wait(lambda snap: not _has(snap, "dialog.discard_close"),
                description="close cancelled")
        assert ui.node("export.start")["enabled"], "Cancel close lost the result"
        prompt()
        ui.click({"role": "AXButton", "title": "Export…"}, physical=False)
        ui.wait(lambda snap: _has(snap, "export.format"), description="export from close prompt")
        ui.click("dialog.cancel", physical=False)
        ui.wait(lambda snap: not _has(snap, "export.format"), description="export from close cancelled")
        assert ui.process.poll() is None and ui.node("export.start")["enabled"], "Cancelled export closed the app"
        prompt()
        ui.click("dialog.discard_close", physical=False)
        assert ui.process.wait(timeout=10) == 0, "Explicit discard did not close cleanly"
    ctx.note("unsaved_close", {"cancel_keeps_result": True, "cancel_export_keeps_app": True, "explicit_quit": True})


def recovery_cases():
    return [
        Case("interface.recovery.close-unsaved", "interface", _close_unsaved,
             "Close can be cancelled; cancelled close-export preserves the result; explicit discard exits cleanly"),
        *[Case(f"algorithms.recovery.cascade.{device}", "algorithms", partial(_alignment_cascade, device=device),
               "Large narrow frames recover known translation through multiscale CPU/GPU alignment")
          for device in ("cpu", "gpu")],
        Case("interface.recovery.folder-import", "interface", _folder_import,
             "Recursive folder import skips hidden/unsupported entries, suppresses duplicates and preserves frames after rejection"),
        Case("interface.recovery.device-request", "interface", _device_request,
             "A GPU preference completes with a reported actual device and valid pixels, including unavailable-device CPU fallback"),
        Case("interface.recovery.missing-source", "interface", _missing_source,
             "A source removed after import causes a recoverable worker error; restored inputs can be stacked"),
        Case("interface.recovery.batch-export", "interface", _batch_export,
             "A conflicting output directory reports export failure, preserves other files and permits retry"),
        Case("interface.recovery.export-cancel", "interface", _cancel_export,
             "Cancelling options or native Save preserves the result for a later successful export"),
    ]
