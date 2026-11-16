"""Additional externally reachable numerical and failure-path conformance.

Only generated files, canonical CLI settings, exported pixels and language-neutral
execution events are used. Missing uncalled library helpers are not invoked here.
"""
from __future__ import annotations

from functools import partial

import numpy as np
from PIL import Image
import tifffile

from ..model import Case
from ..validators import assert_incomplete, assert_pixels_close, read_image, validate_image
from .devices import require_backend


def _images(ctx, name, arrays, extension="png"):
    directory = ctx.directory / "generated" / name
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, array in enumerate(arrays):
        path = directory / f"frame_{index:02d}.{extension}"
        if extension == "npy":
            np.save(path, array)
        elif extension == "tif":
            tifffile.imwrite(path, array, metadata=None)
        else:
            Image.fromarray(array).save(path)
        paths.append(path)
    return paths


def _successful(result, backend="cpu"):
    return require_backend(result, backend)


def _precision(ctx, mode):
    fixture = ctx.fixture("rotation" if mode == "euclidean" else mode)
    result = ctx.stack(fixture, method="hybrid", align=True, alignment_mode=mode,
                       alignment_reference="previous", max_precision=True)
    event = _successful(result)
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=50))
    matrices = np.asarray(event["sequential_transforms"], dtype=float)
    assert matrices.shape == (len(fixture.paths), 2, 3) and np.isfinite(matrices).all()
    ctx.note("alignment_scales", np.sqrt(np.abs(np.linalg.det(matrices[:, :, :2]))).tolist())


def _scale_clamp(ctx):
    fixture = ctx.fixture("translation")
    base = Image.open(fixture.paths[0])
    width, height = base.size
    arrays = []
    for scale in (1.0, 1.18, 1.34):
        inverse = (1 / scale, 0, width * (1 - 1 / scale) / 2,
                   0, 1 / scale, height * (1 - 1 / scale) / 2)
        arrays.append(np.asarray(base.transform(base.size, Image.Transform.AFFINE, inverse, Image.Resampling.BILINEAR)))
    paths = _images(ctx, "scale-clamp", arrays)
    result = ctx.stack(paths, method="hybrid", align=True, alignment_mode="breathing", max_scale_step=0.01)
    event = _successful(result)
    validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=30)
    matrices = np.asarray(event["sequential_transforms"], dtype=float)
    scales = np.sqrt(np.abs(np.linalg.det(matrices[:, :, :2])))
    assert np.isfinite(scales).all() and np.all((scales >= 0.97) & (scales <= 1.03)), f"Implausible scale was not rejected: {scales}"
    ctx.note("clamped_cumulative_scales", scales.tolist())


def _featureless(ctx, mode):
    fixture = ctx.fixture("flat")
    result = ctx.stack(fixture, method="depth_map", align=True, alignment_mode=mode,
                       alignment_reference="previous", max_precision=True, auto_crop=True)
    event = _successful(result)
    image = read_image(result.output)
    assert image.ndim == 3 and image.shape[2] == 3
    assert all(0 < size <= original for size, original in zip(image.shape[:2], fixture.shape[:2], strict=True))
    expected = np.empty_like(image)
    expected[:] = (83, 127, 173)
    # A featureless image has no uniquely defined transform. It must still
    # retain constant source color rather than crash or invent image structure.
    ctx.note("flat_alignment_error", assert_pixels_close(image, expected, mean_limit=1, max_limit=1))
    matrices = np.asarray(event["sequential_transforms"], dtype=float)
    assert np.isfinite(matrices).all()


def _implausible_transform(ctx, kind):
    fixture = ctx.fixture("translation")
    base = Image.open(fixture.paths[0])
    width, height = base.size
    if kind == "rotation":
        altered = base.rotate(24, Image.Resampling.BILINEAR)
        mode = "similarity"
    elif kind == "anisotropy":
        altered = base.transform(base.size, Image.Transform.AFFINE, (0.75, 0.15, 20, 0, 1.3, -20), Image.Resampling.BILINEAR)
        mode = "affine"
    else:
        altered = base.transform(base.size, Image.Transform.AFFINE,
                                 (1 / 1.6, 0, width * (1 - 1 / 1.6) / 2,
                                  0, 1 / 1.6, height * (1 - 1 / 1.6) / 2), Image.Resampling.BILINEAR)
        mode = "similarity"
    paths = _images(ctx, kind, [np.asarray(base), np.asarray(altered)])
    result = ctx.stack(paths, method="hybrid", align=True, alignment_mode=mode)
    event = _successful(result)
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=30))
    assert len(event["alignment_transforms"]) == len(paths)
    for matrix in event["alignment_transforms"].values():
        assert matrix is None or np.isfinite(np.asarray(matrix)).all()
    ctx.note("input_condition", f"Large {kind}; fallback may discard an implausible coarse feature match")


def _large_dimension_difference(ctx):
    fixture = ctx.fixture("focus")
    base = Image.open(fixture.paths[0])
    arrays = [np.asarray(base), np.asarray(base.resize((48, 32), Image.Resampling.BILINEAR)),
              np.asarray(base.resize((600, 400), Image.Resampling.BILINEAR))]
    paths = _images(ctx, "large-dimension-difference", arrays)
    result = ctx.stack(paths, method="depth_map", align=True, alignment_mode="euclidean")
    _successful(result)
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=50))


def _mixed_precision(ctx, reference_bits, align):
    fixture = ctx.fixture("precision16")
    source = read_image(fixture.paths[0])
    directory = ctx.directory / "mixed-precision"
    directory.mkdir()
    paths = []
    for index in range(3):
        bits = reference_bits if index == 0 else (8 if reference_bits == 16 else 16)
        image = source if bits == 16 else np.rint(source.astype(float) / 257).astype(np.uint8)
        path = directory / f"frame_{index:02d}.tif"
        tifffile.imwrite(path, image, photometric="rgb", metadata=None)
        paths.append(path)
    options = {"method": "weighted_average", "align": align, "alignment_mode": "translation"}
    cpu = ctx.stack(paths, device="cpu", **options)
    gpu = ctx.stack(paths, device="gpu", **options)
    _successful(cpu)
    _successful(gpu, "gpu")
    validate_image(gpu.output, shape=source.shape, dtype="uint8", min_range=50)
    ctx.note("parity", assert_pixels_close(gpu.output, cpu.output, mean_limit=0.8, max_limit=3))
    ctx.note("reference_input_bits", reference_bits)


def _hdr_multibatch(ctx, device):
    fixture = ctx.fixture("exposure")
    originals = [np.asarray(Image.open(path)) for path in fixture.paths]
    paths = _images(ctx, "nine-exposures", [originals[index % len(originals)] for index in range(9)])
    result = ctx.stack(paths, method="exposure_fusion", device=device)
    _successful(result, device)
    ctx.note("image", validate_image(result.output, shape=fixture.shape, dtype="uint8", min_range=80))
    ctx.note("batch_input_count", len(paths))


def _partial_corrupt(ctx, method, align=False, mode="similarity", device="cpu"):
    fixture = ctx.fixture("focus")
    corrupt = ctx.directory / "frame_99-corrupt.png"
    corrupt.write_bytes(b"not a valid image")
    paths = [*fixture.paths, corrupt]
    # A valid existing export must survive even a late failure after a slab.
    output = ctx.directory / "retained.png"
    retained = fixture.paths[0].read_bytes()
    output.write_bytes(retained)
    result = ctx.stack(paths, method=method, align=align, alignment_mode=mode,
                       device=device, output_path=output, slab_size=2, slab_overlap=0)
    assert_incomplete(result, corrupt, retained=retained)


def _no_decodable_frames(ctx, method, align=False):
    paths = []
    for index in range(3):
        path = ctx.directory / f"unreadable-{index}.png"
        path.write_bytes(b"not a PNG")
        paths.append(path)
    result = ctx.stack(paths, method=method, align=align, alignment_mode="breathing")
    assert result.returncode != 0 and not result.output.exists()
    events = result.diagnostics.get("events", [])
    started = [event for event in events if event.get("event") == "stack_start"]
    assert started and started[-1].get("algorithm") == method, "Invalid data did not reach requested stack operation"
    completed = [event for event in events if event.get("event") == "stack_complete"]
    assert completed and completed[-1].get("completed") is False, "Empty decode stream reported successful image"
    assert result.stderr.strip()


def _gray_array(ctx, method, device):
    fixture = ctx.fixture("focus")
    arrays = [np.asarray(Image.open(path)).astype(np.float32).mean(axis=2) for path in fixture.paths]
    paths = _images(ctx, "gray-arrays", arrays, extension="npy")
    result = ctx.stack(paths, method=method, device=device)
    _successful(result, device)
    ctx.note("image", validate_image(result.output, shape=fixture.shape[:2], dtype="uint8", min_range=50))
    ctx.note("array_format", "NPY v1 float32 grayscale, as accepted by the public CLI input path")
    if device == "gpu":
        cpu = ctx.stack(paths, method=method, device="cpu")
        _successful(cpu)
        ctx.note("parity", assert_pixels_close(result.output, cpu.output, mean_limit=0.3, max_limit=2))


def coverage_algorithm_cases():
    cases = []
    def add(name, function, **kwargs):
        cases.append(Case("algorithms.coverage." + name, "algorithms", partial(function, **kwargs),
                          "Generated public-boundary numerical and fallback coverage"))
    for mode in ("euclidean", "affine"):
        add(f"precision.{mode}", _precision, mode=mode)
    add("scale_clamp", _scale_clamp)
    for mode in ("similarity", "affine"):
        add(f"featureless.{mode}", _featureless, mode=mode)
    for kind in ("rotation", "anisotropy", "scale"):
        add(f"implausible.{kind}", _implausible_transform, kind=kind)
    add("dimensions_resize_over_twofold", _large_dimension_difference)
    for bits in (8, 16):
        for align in (False, True):
            add(f"mixed_precision.ref{bits}.{'aligned' if align else 'stack'}", _mixed_precision, reference_bits=bits, align=align)
    for device in ("cpu", "gpu"):
        add(f"hdr_multibatch.{device}", _hdr_multibatch, device=device)
    for method in ("laplacian", "hybrid", "weighted_average", "depth_map", "exposure_fusion"):
        for mode in ("stack", "translation", "euclidean", "similarity", "affine", "breathing"):
            add(f"partial_corrupt.{method}.{mode}", _partial_corrupt, method=method,
                align=mode != "stack", mode="translation" if mode == "stack" else mode)
    for method in ("weighted_average", "depth_map", "exposure_fusion"):
        add(f"no_decodable_frames.{method}", _no_decodable_frames, method=method)
    add("no_decodable_frames.sequential", _no_decodable_frames, method="weighted_average", align=True)
    for method in ("hybrid", "weighted_average", "depth_map"):
        for device in ("cpu", "gpu"):
            add(f"gray_array.{method}.{device}", _gray_array, method=method, device=device)
    return cases
