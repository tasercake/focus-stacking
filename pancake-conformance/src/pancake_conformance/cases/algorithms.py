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


def _zero_regions(ctx, device="cpu"):
    from .devices import require_backend
    fixture = ctx.fixture("zero_regions")
    result = _success(ctx.stack(fixture, method="weighted_average", device=device))
    require_backend(result, device)
    validate_image(result.output, shape=fixture.shape, dtype="uint8")
    ctx.note("identity", assert_pixels_close(result.output, fixture.truth_path, mean_limit=0, max_limit=0))


def _flat(ctx, method):
    fixture = ctx.fixture("flat")
    result = _success(ctx.stack(fixture, method=method))
    actual, truth = read_image(result.output), read_image(fixture.truth_path)
    validate_image(result.output, shape=fixture.shape, dtype="uint8")
    limit = 8 if method == "laplacian" else 0
    ctx.note("constant_color_error", assert_pixels_close(actual, truth, mean_limit=limit, max_limit=limit))
    assert all(np.ptp(actual[..., channel]) == 0 for channel in range(3)), "Flat input gained spatial texture"


def _precision(ctx, method, output_format):
    fixture = ctx.fixture("precision16")
    result = _success(ctx.stack(fixture, method=method, bit_depth=16, output_format=output_format))
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint16", genuine_16bit=True))
    if method in ("weighted_average", "depth_map", "exposure_fusion"):
        ctx.note("roundtrip", assert_pixels_close(result.output, fixture.truth_path, mean_limit=1, max_limit=1))
    elif method == "hybrid":
        ctx.note("roundtrip", assert_pixels_close(result.output, fixture.truth_path, mean_limit=120))


def _exposure_precision(ctx, count=9, output_format="tif"):
    fixture = ctx.fixture("precision16")
    paths = [fixture.paths[i % len(fixture.paths)] for i in range(count)]
    result = _success(ctx.stack(paths, method="exposure_fusion", bit_depth=16, output_format=output_format))
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint16", genuine_16bit=True))
    ctx.note("identity", assert_pixels_close(result.output, fixture.truth_path, mean_limit=1, max_limit=1))


def _exposure_constant_mix(ctx, count=9, device="cpu"):
    import tifffile
    from .devices import require_backend
    arrays = [np.full((33, 49, 3), (10001+31*i, 23003+47*i, 37007+61*i), np.uint16) for i in range(count)]
    paths = []
    for i, image in enumerate(arrays):
        path = ctx.directory / f"constant-{i}.tif"
        tifffile.imwrite(path, image, metadata=None)
        paths.append(path)
    # Zero spatial contrast gives equal weights. The documented batch tree
    # gives equal weights to batches, including a final one-frame remainder.
    expected = np.rint(np.mean([np.mean(arrays[i:i+4], axis=0) for i in range(0, count, 4)], axis=0)).astype(np.uint16)
    result = ctx.stack(paths, method="exposure_fusion", device=device, bit_depth=16, output_format="tif")
    require_backend(result, device)
    ctx.note("analytic_fusion_error", assert_pixels_close(result.output, expected, mean_limit=1, max_limit=1))


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
    from .devices import require_backend
    event = require_backend(result, "cpu")
    expected = np.asarray(fixture.metadata["source_transforms"], float)
    r = len(fixture.paths)//2 if reference == "middle" else 0
    ref_inverse = np.linalg.inv(np.vstack((expected[r], [0, 0, 1])))
    expected = np.asarray([(np.vstack((m, [0, 0, 1])) @ ref_inverse)[:2] for m in expected])
    actual = np.asarray([event["alignment_transforms"][str(path)] for path in fixture.paths], float)
    h, w = fixture.shape[:2]
    points = np.array([[0, 0, 1], [w-1, 0, 1], [0, h-1, 1], [w-1, h-1, 1], [w/2, h/2, 1]], float).T
    error = float(np.max(np.abs((actual-expected) @ points)))
    assert error <= 1., f"Known-transform geometry error {error}px"
    ctx.note("geometry_max_error", error)
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
    bit_depth = 16
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
    ctx.note("normalized_input_error", assert_pixels_close(result.output, truth, mean_limit=1, max_limit=1))


def _translation_bounded_crop(ctx):
    from .devices import require_backend
    fixture = ctx.fixture("translation")
    result = _success(ctx.stack(fixture, method="weighted_average", align=True,
                                alignment_mode="translation", auto_crop=True))
    event = require_backend(result, "cpu")
    actual = np.asarray([event["alignment_transforms"][str(path)] for path in fixture.paths], float)
    expected = np.asarray(fixture.metadata["source_transforms"], float)
    assert np.max(np.abs(actual - expected)) <= .3, f"Translation estimation error: {actual - expected}"
    output = read_image(result.output)
    height, width = fixture.shape[:2]
    dy, dx = (height-output.shape[0])//2, (width-output.shape[1])//2
    # Symmetric ceil(max displacement)+1 policy: 3px x / 1.5px y,
    # with at most one extra pixel per side for subpixel estimation error.
    assert 2 <= dy <= 4 and 4 <= dx <= 5, f"Unjustified border removal: {dy}, {dx}"
    assert output.shape[:2] == (height-2*dy, width-2*dx)
    truth = read_image(fixture.truth_path)[dy:height-dy, dx:width-dx]
    ctx.note("truth_error", assert_pixels_close(output, truth, mean_limit=3))
    ctx.note("transform_max_error", float(np.max(np.abs(actual-expected))))


def _ambiguous_slabs(ctx, method, fixture_name="deep"):
    from .devices import require_backend
    fixture = ctx.fixture(fixture_name)
    result = _success(ctx.stack(fixture, method=method, slab_size=4, slab_overlap=1,
                                align=True, alignment_mode="breathing"))
    event = require_backend(result, "cpu")
    validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=30)
    transforms = np.asarray(event["sequential_transforms"], float)
    # These fixtures have focus changes but no camera motion. Assert geometry
    # independently of pixel quality; a sharp but shifted result must fail.
    corners = np.array([[0, 0, 1], [98, 0, 1], [0, 64, 1], [98, 64, 1]], float).T
    drift = np.max(np.abs((transforms - np.eye(2, 3)) @ corners))
    assert drift < .3, f"Unsupported motion on focus-only stack: {drift}px"
    output, truth = read_image(result.output), read_image(fixture.truth_path)
    ratios = [sharpness(output, r) / sharpness(truth, r) for r in fixture.metadata["regions"]]
    assert min(ratios) >= .65, f"Focus detail lost: {ratios}"
    ctx.note("focus_recovery_ratios", ratios)
    ctx.note("truth_error", assert_pixels_close(output, truth, mean_limit=20))
    ctx.note("geometry_drift", float(drift))


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
        add(f"flat.{method}", _flat, method=method,
            description="Constant input retains source color")
        add(f"deterministic.{method}", _deterministic, method=method)
        add(f"automatic_parameters.{method}", _run_stack, options={"method": method, "auto": True})
        for mode in MODES:
            add(f"alignment.{mode}.{method}", _aligned_geometry, method=method, mode=mode)
        add(f"quality_report.{method}", _run_stack, options={"method": method, "quality_report": True})
        add(f"input.bayer_dng.{method}", _raw_input, method=method,
            description="Decode a generated Bayer DNG without an embedded thumbnail")
        add(f"alignment.mixed_dimensions.{method}", _mixed_dimensions, method=method,
            description="Align different input dimensions into first-frame coordinates")

    for method in METHODS:
        for output_format in ("png", "tif"):
            add(f"precision16.{output_format}.{method}", _precision, method=method, output_format=output_format)
        add(f"cross_export.{method}", _cross_export, method=method)
        if method == "exposure_fusion":
            continue
        for size, overlap in ((2, 0), (3, 1), (4, 2), (9, 0)):
            add(f"slabs.{size}.{overlap}.{method}", _slabs, method=method, size=size, overlap=overlap, align=False)
        add(f"slabs.breathing.{method}", _slabs, method=method, size=4, overlap=1, align=True)
        add(f"alignment.repeated_breathing_slabs.{method}", _ambiguous_slabs, method=method)
        add(f"alignment.nonrepeating_slabs.{method}", _ambiguous_slabs, method=method, fixture_name="deep_nonrepeating")

    for mode in MODES:
        for reference in ("middle", "previous"):
            add(f"alignment.{mode}.reference_{reference}", _aligned_geometry,
                method="hybrid", mode=mode, reference=reference)
    for name in ("grayscale", "rgba", "formats", "unicode"):
        add(f"input.{name}", _input_format, name=name)
    for name in ("float01", "float255", "exr", "grayscale16", *[f"orientation{i}" for i in range(1, 9)]):
        add(f"input.{name}", _extended_input, name=name)
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
    for count in (4, 9):
        add(f"exposure_constant_mix.{count}", _exposure_constant_mix, count=count)
    add("weighted.zero_regions", _zero_regions)
    add("alignment.auto_crop", _auto_crop)
    add("alignment.translation_bounded_crop", _translation_bounded_crop)
    add("exposure_brackets", _run_stack, fixture_name="exposure", quality=False, options={"method": "exposure_fusion"})
    for count in (2, 4, 9):
        for fmt in ("png", "tif"):
            add(f"exposure_precision.{count}.{fmt}", _exposure_precision, count=count, output_format=fmt)
    return cases
