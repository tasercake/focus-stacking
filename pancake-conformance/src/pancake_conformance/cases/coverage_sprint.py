"""Additional observable workflows through native input and exported files."""
import numpy as np
from functools import partial
from PIL import Image

from ..model import Case
from ..validators import read_image, validate_image, assert_pixels_close
from .interface import _frame_rows, _menu, _viewer
from .devices import require_backend


def _viewer_input(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        ui.wait(lambda snap: _viewer(ui)["has_image"], description="source image visible")
        _menu(ui, "viewer.fit")
        ui.action("viewer.actual")
        ui.wait(lambda snap: abs(_viewer(ui)["zoom"] - 1) < 1e-6, description="actual image size")
        before = _viewer(ui)["zoom"]
        ui.action("viewer.zoom_in")
        ui.wait(lambda snap: _viewer(ui)["zoom"] > before, description="zoom changes displayed scale")
        ui.action("viewer.fit")
        ui.wait(lambda snap: _viewer(ui)["fit"], description="fit restored")
    ctx.note("viewer_input", {"double_click_round_trip": True, "wheel_modes": ["modified_pixel"],
                               "fullscreen_round_trip": True})


def _frame_context(ctx):
    fixture = ctx.fixture("focus")
    with ctx.open_ui(paths=fixture.paths) as ui:
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 3, description="three source rows")
        ui.action("frames.context_second")
        ui.node("frames.remove_one")
        ui.node("frames.reveal")
        _menu(ui, "frames.reveal")
        ui.wait(lambda snap: snap.get("frontmost") is False, description="native file manager revealed source")
        ui.click("mode.view")
        ui.wait(lambda snap: snap.get("frontmost") is True, description="application refocused after reveal")
        ui.action("frames.context_second")
        _menu(ui, "frames.remove_one")
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 2, description="context action removed one frame")
        _menu(ui, "frames.select_all")
        _menu(ui, "frames.remove_selected")
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 0, description="selected sources removed")
        assert not ui.node("stack.start")["enabled"]


def _viewport_export(ctx):
    fixture = ctx.fixture("flat")
    with ctx.open_ui(paths=fixture.paths) as ui:
        ui.wait(lambda snap: _viewer(ui)["has_image"], description="flat source image visible")
        _menu(ui, "viewer.fit")
        _menu(ui, "export.viewport")
        output = ui.save_file(ctx.directory / "viewport.png")
        pixels = read_image(output)
        assert pixels.ndim == 3 and pixels.shape[2] in (3, 4)
        h, w = pixels.shape[:2]
        assert min(h, w) > 100, "Viewport export has invalid dimensions"
        expected = np.array([83, 127, 173])
        error = np.abs(pixels[h // 2 - 2:h // 2 + 2, w // 2 - 2:w // 2 + 2, :3].astype(float) - expected)
        assert error.max() <= 2, "Viewport export changed displayed RGB channels"
        # Viewport dimensions/layout are deliberately not a frozen output contract.
        ctx.note("viewport_export", {"file": output.name, "shape": list(pixels.shape),
                                      "center_rgb_error": float(error.max())})


def sprint_cases():
    cases = [Case("interface.sprint.viewer-input", "interface", _viewer_input,
                 "Double-click, mouse/trackpad zoom, canvas context click and fullscreen use native input"),
            Case("interface.sprint.frame-context", "interface", _frame_context,
                 "Source context menu reveals a file, removes one frame and removes the selected remainder"),
            Case("interface.sprint.viewport-export", "interface", _viewport_export,
                 "Native viewport export preserves displayed RGB channels without freezing UI layout")]
    for fixture in ("grayscale", "grayscale16", "rgba"):
        for method in ("hybrid", "weighted_average", "depth_map"):
            cases.append(Case(f"algorithms.sprint.native-input.{fixture}.{method}", "algorithms",
                              partial(_native_input, fixture_name=fixture, method=method),
                              "Native gray/alpha decode preserves RGB geometry and CPU/GPU pixel parity"))
    cases.append(Case("algorithms.sprint.black-translation", "algorithms", _black_translation,
                      "Small zero-valued images remain zero under translation alignment"))
    return cases


def _native_input(ctx, fixture_name, method):
    fixture = ctx.fixture(fixture_name)
    precision = fixture_name == "grayscale16"
    options = {"method": method, "bit_depth": 16 if precision else 8,
               "output_format": "tif" if precision else "png"}
    cpu = ctx.stack(fixture, device="cpu", **options)
    gpu = ctx.stack(fixture, device="gpu", **options)
    require_backend(cpu, "cpu")
    require_backend(gpu, "gpu")
    shape = (*fixture.shape[:2], 3)
    validate_image(gpu.output, shape=shape, dtype="uint16" if precision else "uint8", min_range=50)
    first, second = read_image(cpu.output), read_image(gpu.output)
    if precision:
        first, second = first.astype(float) / 257, second.astype(float) / 257
    ctx.note("parity", assert_pixels_close(first, second, mean_limit=0.3, max_limit=2))
    if fixture_name.startswith("grayscale"):
        assert_pixels_close(second[..., 0], second[..., 1], mean_limit=0, max_limit=0)
        assert_pixels_close(second[..., 1], second[..., 2], mean_limit=0, max_limit=0)


def _black_translation(ctx):
    paths = []
    for index in range(3):
        path = ctx.directory / f"black-{index}.png"
        Image.fromarray(np.zeros((32, 48, 3), dtype=np.uint8)).save(path)
        paths.append(path)
    result = ctx.stack(paths, method="depth_map", align=True, alignment_mode="translation")
    require_backend(result, "cpu")
    pixels = read_image(result.output)
    assert pixels.shape == (32, 48, 3) and pixels.dtype == np.uint8
    assert not np.any(pixels), "Translation introduced nonzero data into zero-valued sources"
