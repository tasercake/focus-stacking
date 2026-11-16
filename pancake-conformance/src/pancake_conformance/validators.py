"""Independent decoded-pixel and structural oracles, always using RGB order."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import tifffile


def read_image(path: str | Path) -> np.ndarray:
    path = Path(path)
    assert path.is_file() and path.stat().st_size > 0, f"Missing or empty image: {path}"
    if path.suffix.lower() == ".npy":
        return np.load(path, allow_pickle=False)
    if path.suffix.lower() in (".tif", ".tiff"):
        return tifffile.imread(path)
    if path.suffix.lower() == ".png":
        import png
        width, height, rows, info = png.Reader(filename=str(path)).asDirect()
        dtype = np.uint16 if info["bitdepth"] == 16 else np.uint8
        data = np.vstack([np.asarray(row, dtype=dtype) for row in rows])
        if info["planes"] == 1:
            return data.reshape(height, width)
        return data.reshape(height, width, info["planes"])
    if path.suffix.lower() == ".exr":
        import OpenEXR
        with OpenEXR.File(str(path)) as image:
            channels = image.channels()
            if "RGB" in channels:
                return channels["RGB"].pixels.copy()
            if "RGBA" in channels:
                return channels["RGBA"].pixels.copy()
            return np.stack([channels[c].pixels for c in ("R", "G", "B")], axis=-1)
    with Image.open(path) as image:
        return np.asarray(image).copy()


def validate_image(path: str | Path, *, shape=None, dtype=None, min_range=0,
                   genuine_16bit=False, finite=True) -> dict:
    path = Path(path)
    storage_precision = None
    if path.suffix.lower() == ".exr" and dtype == "float32":
        import OpenEXR
        assert path.is_file() and path.stat().st_size > 0, f"Missing or empty image: {path}"
        # Inspect file channel declarations before decoding/coalescing RGB.
        # InputFile.header reports stored types without converting pixel data.
        header_file = OpenEXR.InputFile(str(path))
        try:
            storage_precision = {name: str(channel.type)
                                 for name, channel in header_file.header()["channels"].items()}
        finally:
            header_file.close()
        assert all(storage_precision.get(name) == "FLOAT" for name in "RGB"), f"EXR storage precision must be FLOAT32 RGB: {storage_precision}"
    image = read_image(path)
    if shape is not None:
        assert image.shape == tuple(shape), f"Image shape {image.shape}, expected {tuple(shape)}"
    if dtype is not None:
        assert str(image.dtype) == dtype, f"Image dtype {image.dtype}, expected {dtype}"
    if finite:
        assert np.isfinite(image).all(), "Image contains NaN or infinity"
    dynamic_range = float(np.max(image).astype(float) - np.min(image).astype(float))
    assert dynamic_range >= min_range, f"Image dynamic range {dynamic_range} < {min_range}"
    if genuine_16bit:
        assert image.dtype == np.uint16, "16-bit precision requires uint16 output"
        assert np.unique(image).size > 256 and np.any(image % 257 != 0), "Image lost 16-bit precision"
    metadata = {"shape": list(image.shape), "dtype": str(image.dtype), "range": dynamic_range,
                "mean": float(image.mean()), "sharpness": sharpness(image)}
    if storage_precision is not None:
        metadata["storage_precision"] = storage_precision
    return metadata


def pixel_metrics(actual: np.ndarray, expected: np.ndarray, *, region=None,
                  threshold=2.0) -> dict[str, float]:
    assert actual.shape == expected.shape, f"Pixel shape differs: {actual.shape} != {expected.shape}"
    if region is not None:
        top, bottom, left, right = region
        actual, expected = actual[top:bottom, left:right], expected[top:bottom, left:right]
    assert actual.size, "Pixel region is empty"
    diff = np.abs(actual.astype(np.float64) - expected.astype(np.float64))
    assert np.isfinite(diff).all(), "Pixel difference contains NaN or infinity"
    pixels = diff.max(axis=2) if diff.ndim == 3 else diff
    return {"mean_absolute_error": float(diff.mean()), "max_absolute_error": float(diff.max()),
            "p99_absolute_error": float(np.percentile(diff, 99)),
            "fraction_above_threshold": float((pixels > threshold).mean())}


def assert_pixels_close(actual: str | Path | np.ndarray, expected: str | Path | np.ndarray,
                        *, mean_limit: float, max_limit: float | None = None,
                        region=None, fraction_limit: float | None = None,
                        threshold=2.0) -> dict[str, float]:
    actual_array = read_image(actual) if isinstance(actual, (str, Path)) else actual
    expected_array = read_image(expected) if isinstance(expected, (str, Path)) else expected
    metrics = pixel_metrics(actual_array, expected_array, region=region, threshold=threshold)
    assert metrics["mean_absolute_error"] <= mean_limit, f"Mean pixel error {metrics['mean_absolute_error']} > {mean_limit}"
    if max_limit is not None:
        assert metrics["max_absolute_error"] <= max_limit, f"Max pixel error {metrics['max_absolute_error']} > {max_limit}"
    if fraction_limit is not None:
        assert metrics["fraction_above_threshold"] <= fraction_limit, f"Pixel error fraction {metrics['fraction_above_threshold']} > {fraction_limit}"
    return metrics


def sharpness(image: np.ndarray, region=None) -> float:
    if region is not None:
        top, bottom, left, right = region
        image = image[top:bottom, left:right]
    gray = image.astype(np.float64)
    if gray.ndim == 3:
        gray = gray[..., :3].mean(axis=2)
    if min(gray.shape[:2]) < 3:
        return 0.0
    laplacian = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2]
                 + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1])
    return float(laplacian.var())


def assert_incomplete(result, input_path, *, retained=None):
    """An undecodable requested input fails the whole job, without publication."""
    assert result.returncode != 0, "Corrupt input produced a successful partial job"
    assert str(input_path) in result.stderr or str(input_path.name) in result.stderr, "Diagnostic does not identify rejected input"
    if retained is None:
        assert not result.output.exists(), "Failed job published a partial output"
    else:
        assert result.output.read_bytes() == retained, "Failed job damaged existing output"
    events = result.diagnostics.get("events", [])
    assert not any(e.get("event") == "stack_complete" and e.get("completed") for e in events), "Incomplete job reported completion"
    assert not any(e.get("event") == "backend_fallback" for e in events), "Input corruption treated as backend failure"
