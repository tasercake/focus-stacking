"""Portable numerical conformance through external application processes.

No scenario imports or calls application implementation code. Reference-specific
argument syntax belongs to the target manifest, not these recipes. Image quality
checks and explicit legacy compatibility cases are kept distinct in identifiers.
"""
from __future__ import annotations

from functools import partial

import numpy as np
from scipy.ndimage import gaussian_filter

from ..model import Case
from ..validators import assert_pixels_close, pixel_metrics, read_image, sharpness, validate_image

METHODS = ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion")
FOCUS_METHODS = METHODS[:-1]
MODES = ("translation", "euclidean", "similarity", "affine", "breathing")


def _success(result):
    assert result.returncode == 0, f"Target exited {result.returncode}: {result.stderr}\n{result.stdout}"
    return result


def _run_stack(ctx, *, fixture_name="focus", options=None, quality=True):
    fixture = ctx.fixture(fixture_name)
    options = dict(options or {})
    result = _success(ctx.stack(fixture, **options))
    shape = (*fixture.shape[:2], 3)
    is_float = options.get("output_format") == "exr"
    dtype = "float32" if is_float else ("uint16" if options.get("bit_depth") == 16 else "uint8")
    metrics = validate_image(result.output, shape=shape, dtype=dtype,
                             min_range=0.1 if is_float else 30)
    ctx.note("image", metrics)
    if quality and fixture_name in ("focus", "odd", "unicode", "deep"):
        actual, truth = read_image(result.output), read_image(fixture.truth_path)
        if dtype == "uint16":
            actual = actual.astype(float) / 257
        elif is_float:
            actual = actual * 255
        # Local focus regions ensure output did not select only one source plane.
        ratios = [sharpness(actual, region) / sharpness(truth, region)
                  for region in fixture.metadata["regions"]]
        ctx.note("focus_recovery_ratios", ratios)
        assert min(ratios) >= 0.65, f"Lost focus plane detail: {ratios}"
        ctx.note("truth_error", assert_pixels_close(actual, truth, mean_limit=15))
    return result


def _flat(ctx, method):
    fixture = ctx.fixture("flat")
    result = _success(ctx.stack(fixture, method=method))
    actual, truth = read_image(result.output), read_image(fixture.truth_path)
    validate_image(result.output, shape=fixture.shape, dtype="uint8")
    if method == "weighted_average":
        # Capture, do not silently repair, current zero-weight division behavior.
        assert not actual.any(), "Reference zero-contrast compatibility behavior changed"
        ctx.note("known_reference_defect", "Weighted average returns black for zero-contrast inputs")
    else:
        limit = 8 if method == "laplacian" else 0
        ctx.note("constant_color_error", assert_pixels_close(actual, truth, mean_limit=limit, max_limit=limit))
        assert all(np.ptp(actual[..., channel]) == 0 for channel in range(3)), "Flat input gained spatial texture"


def _precision(ctx, method, output_format):
    fixture = ctx.fixture("precision16")
    result = _success(ctx.stack(fixture, method=method, bit_depth=16, output_format=output_format))
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint16", genuine_16bit=True))
    if method in ("weighted_average", "depth_map"):
        ctx.note("roundtrip", assert_pixels_close(result.output, fixture.truth_path, mean_limit=1, max_limit=1))
    elif method == "hybrid":
        ctx.note("roundtrip", assert_pixels_close(result.output, fixture.truth_path, mean_limit=120))


def _hdr_precision_compatibility(ctx):
    fixture = ctx.fixture("precision16")
    result = _success(ctx.stack(fixture, method="exposure_fusion", bit_depth=16))
    validate_image(result.output, shape=fixture.shape, dtype="uint16", min_range=40000)
    unique = int(np.unique(read_image(result.output)).size)
    assert unique <= 256, f"Reference exposure-fusion quantization changed: {unique} levels"
    ctx.note("known_reference_limit", "Exposure fusion quantizes source data through 8-bit Mertens input")
    ctx.note("unique_output_levels", unique)


def _deterministic(ctx, method):
    fixture = ctx.fixture("focus" if method != "exposure_fusion" else "exposure")
    first = _success(ctx.stack(fixture, method=method))
    second = _success(ctx.stack(fixture, method=method))
    # Mertens parallel floating-point reductions can move isolated values across
    # one rounding boundary. Require all other methods to repeat pixel-exactly.
    limits = {"mean_limit": 0.001, "max_limit": 1, "fraction_limit": 0.001, "threshold": 0} if method == "exposure_fusion" else {"mean_limit": 0, "max_limit": 0}
    ctx.note("repeat_error", assert_pixels_close(first.output, second.output, **limits))


def _cross_export(ctx, method):
    fixture = ctx.fixture("precision16")
    png = _success(ctx.stack(fixture, method=method, bit_depth=16, output_format="png"))
    tiff = _success(ctx.stack(fixture, method=method, bit_depth=16, output_format="tif"))
    ctx.note("format_error", assert_pixels_close(png.output, tiff.output, mean_limit=0, max_limit=0))


def _aligned_geometry(ctx, method, mode, reference="first"):
    fixture_name = "rotation" if mode == "euclidean" else mode
    fixture = ctx.fixture(fixture_name)
    result = _success(ctx.stack(fixture, method=method, align=True,
                                alignment_mode=mode, alignment_reference=reference))
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=50))
    if method == "weighted_average" and reference == "first":
        output = gaussian_filter(read_image(result.output).astype(float), (2, 2, 0))
        truth = gaussian_filter(read_image(fixture.truth_path).astype(float), (2, 2, 0))
        # Independent known geometry, evaluated away from resampling borders.
        metrics = assert_pixels_close(output, truth, region=fixture.metadata["interior"], mean_limit=3)
        ctx.note("alignment_interior_error", metrics)


def _slabs(ctx, method, size, overlap, align):
    fixture = ctx.fixture("breathing" if align else "deep")
    if align:
        size, overlap = 3, 1
    result = _success(ctx.stack(fixture, method=method, slab_size=size, slab_overlap=overlap,
                                align=align, alignment_mode="breathing"))
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=30))
    truth = read_image(fixture.truth_path)
    ctx.note("truth_error", assert_pixels_close(result.output, truth, mean_limit=20))


def _input_format(ctx, name):
    fixture = ctx.fixture(name)
    result = _success(ctx.stack(fixture, method="weighted_average"))
    shape = (*fixture.shape[:2], 3)
    validate_image(result.output, shape=shape, dtype="uint8", min_range=50)
    output = read_image(result.output)
    if name == "grayscale":
        assert np.array_equal(output[..., 0], output[..., 1])
        assert np.array_equal(output[..., 1], output[..., 2]), "Grayscale input gained false color"
    elif name in ("rgba", "unicode"):
        ctx.note("truth_error", assert_pixels_close(output, read_image(fixture.truth_path), mean_limit=1))
    elif name == "formats":
        ctx.note("truth_error", assert_pixels_close(output, read_image(fixture.truth_path), mean_limit=5))


def _raw_input(ctx, method):
    fixture = ctx.fixture("bayer_dng")
    bit_depth = 8 if method == "exposure_fusion" else 16
    result = _success(ctx.stack(fixture, method=method, bit_depth=bit_depth, output_format="tif"))
    ctx.note("image", validate_image(result.output, shape=fixture.metadata["reference_shape"],
                                     dtype="uint16" if bit_depth == 16 else "uint8",
                                     min_range=10000 if bit_depth == 16 else 50,
                                     genuine_16bit=bit_depth == 16))
    ctx.note("raw_contract", "Synthetic uncompressed RGGB DNG; no embedded thumbnail; complete Bayer decode required")


def _mixed_dimensions(ctx, method):
    fixture = ctx.fixture("mixed_dimensions")
    result = _success(ctx.stack(fixture, method=method, align=True, alignment_mode="euclidean"))
    ctx.note("image", validate_image(result.output, shape=fixture.metadata["reference_shape"], dtype="uint8", min_range=50))
    actual, truth = read_image(result.output), read_image(fixture.truth_path)
    ctx.note("resampled_pixel_error", pixel_metrics(actual, truth))
    # Different source dimensions necessarily resample fine checker structure.
    # Compare geometry at a shared low-frequency scale; baseline still retains
    # the full-resolution output without registration or resampling.
    actual_low = gaussian_filter(actual.astype(float), (2, 2, 0))
    truth_low = gaussian_filter(truth.astype(float), (2, 2, 0))
    limits = {"mean_limit": 10, "max_limit": 40} if method == "laplacian" else {"mean_limit": 3, "max_limit": 30}
    ctx.note("resized_alignment_error", assert_pixels_close(actual_low, truth_low,
                                                          region=(16, 113, 16, 177), **limits))


def _extended_input(ctx, name):
    fixture = ctx.fixture(name)
    result = _success(ctx.stack(fixture, method="weighted_average"))
    truth = read_image(fixture.truth_path)
    validate_image(result.output, shape=truth.shape, dtype="uint8", min_range=50)
    if name in ("orientation5", "orientation7"):
        # Reference maps the EXIF transpose/transverse cases in reverse. Keep
        # this incompatibility explicit while retaining standards-correct truth.
        truth = np.rot90(truth, 2)
        ctx.note("known_reference_defect", "EXIF orientations 5 and 7 are interchanged")
    ctx.note("normalized_input_error", assert_pixels_close(result.output, truth, mean_limit=1, max_limit=1))


def _translation_overcrop_compatibility(ctx):
    fixture = ctx.fixture("translation")
    result = _success(ctx.stack(fixture, method="weighted_average", align=True,
                                alignment_mode="translation", auto_crop=True))
    output = read_image(result.output)
    height, width = fixture.shape[:2]
    assert output.shape[0] < height - 50 and output.shape[1] < width - 100, "Known reference DFT overcrop behavior changed"
    validate_image(result.output, dtype="uint8", min_range=50)
    ctx.note("known_reference_defect", "DFT translation can severely overcrop this small texture despite only 3px true drift")
    ctx.note("cropped_shape", list(output.shape))


def _ambiguous_slabs_compatibility(ctx, method):
    fixture = ctx.fixture("deep")
    result = _success(ctx.stack(fixture, method=method, slab_size=4, slab_overlap=1,
                                align=True, alignment_mode="breathing"))
    validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=30)
    ctx.note("known_reference_gap", "Small repeated checker patterns are ambiguous for breathing alignment; quality is measured, not asserted as correct")
    ctx.note("truth_error", pixel_metrics(read_image(result.output), read_image(fixture.truth_path)))


def _auto_crop(ctx):
    fixture = ctx.fixture("translation")
    result = _success(ctx.stack(fixture, method="weighted_average", align=True,
                                alignment_mode="euclidean", auto_crop=True))
    output = read_image(result.output)
    height, width = fixture.shape[:2]
    assert 0 < output.shape[0] < height and 0 < output.shape[1] < width, "Auto crop did not remove shifted borders"
    assert height - output.shape[0] <= 20 and width - output.shape[1] <= 20, "Auto crop removed excessive image area"
    assert (height - output.shape[0]) % 2 == 0 and (width - output.shape[1]) % 2 == 0, "Reference symmetric crop changed"
    ctx.note("cropped_shape", list(output.shape))


def algorithm_cases() -> list[Case]:
    cases = []
    def add(identifier, function, description="", **kwargs):
        cases.append(Case("algorithms." + identifier, "algorithms", partial(function, **kwargs), description))

    for method in METHODS:
        add(f"stack.{method}", _run_stack,
            "Recover all focus planes through command-line interface", options={"method": method})
        add(f"odd_dimensions.{method}", _run_stack, fixture_name="odd", options={"method": method})
        add(f"compatibility.flat.{method}", _flat, method=method,
            description="Explicit constant-input reference behavior; weighted average has known zero-weight defect")
        add(f"deterministic.{method}", _deterministic, method=method)
        add(f"automatic_parameters.{method}", _run_stack, options={"method": method, "auto": True})
        for mode in MODES:
            add(f"alignment.{mode}.{method}", _aligned_geometry, method=method, mode=mode)
        add(f"quality_report.{method}", _run_stack, options={"method": method, "quality_report": True})
        add(f"input.bayer_dng.{method}", _raw_input, method=method,
            description="Decode a generated Bayer DNG without an embedded thumbnail")
        add(f"alignment.mixed_dimensions.{method}", _mixed_dimensions, method=method,
            description="Align different input dimensions into first-frame coordinates")

    for method in FOCUS_METHODS:
        for output_format in ("png", "tif"):
            add(f"precision16.{output_format}.{method}", _precision, method=method, output_format=output_format)
        add(f"cross_export.{method}", _cross_export, method=method)
        for size, overlap in ((2, 0), (3, 1), (4, 2), (9, 0)):
            add(f"slabs.{size}.{overlap}.{method}", _slabs, method=method, size=size, overlap=overlap, align=False)
        add(f"slabs.breathing.{method}", _slabs, method=method, size=4, overlap=1, align=True)
        add(f"compatibility.ambiguous_breathing_slabs.{method}", _ambiguous_slabs_compatibility, method=method)

    for mode in MODES:
        for reference in ("middle", "previous"):
            add(f"alignment.{mode}.reference_{reference}", _aligned_geometry,
                method="hybrid", mode=mode, reference=reference)
    for name in ("grayscale", "rgba", "formats", "unicode"):
        add(f"input.{name}", _input_format, name=name)
    for name in ("float01", "float255", "exr", "grayscale16", *[f"orientation{i}" for i in range(2, 9)]):
        prefix = "compatibility.input" if name in ("orientation5", "orientation7") else "input"
        add(f"{prefix}.{name}", _extended_input, name=name)
    for output_format in ("jpg", "tif", "exr"):
        add(f"export.{output_format}", _run_stack, options={"method": "hybrid", "output_format": output_format})
    for levels in (2, 6):
        add(f"parameters.pyramid_levels_{levels}", _run_stack, options={"method": "laplacian", "pyramid_levels": levels})
    for kernel in (2, 6, 11):
        add(f"parameters.kernel_{kernel}", _run_stack, options={"method": "hybrid", "kernel_size": kernel})
    add("alignment.breathing.max_precision", _run_stack, fixture_name="breathing", quality=False,
        options={"method": "hybrid", "align": True, "alignment_mode": "breathing", "max_precision": True})
    add("alignment.legacy_rotation_scale", _run_stack, fixture_name="similarity", quality=False,
        options={"method": "weighted_average", "align": True, "rotation_scale": True})
    add("alignment.auto_crop", _auto_crop)
    add("compatibility.translation_overcrop", _translation_overcrop_compatibility)
    add("exposure_brackets", _run_stack, fixture_name="exposure", quality=False, options={"method": "exposure_fusion"})
    add("compatibility.exposure_fusion_8bit_internal_precision", _hdr_precision_compatibility)
    return cases
