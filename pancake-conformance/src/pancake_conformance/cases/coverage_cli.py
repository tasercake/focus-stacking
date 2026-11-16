"""Public CLI contracts for unusual real inputs and disposable application state.

These cases exercise files and commands, without importing target code or
constructing implementation-specific cache records.
"""
from functools import partial
import os
import shutil
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image

from ..model import Case
from ..validators import assert_pixels_close, read_image, validate_image
from .devices import require_backend


def assert_rejected(result):
    assert result.returncode != 0, "Invalid stack unexpectedly succeeded"
    assert result.stderr.strip(), "Rejected stack has no error diagnostic"
    assert not result.output.exists(), "Rejected stack published output"


def constant_pair(directory, shape):
    """Two distinct input names, one tiny compressed constant-color payload."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    first, second = (directory / f"constant-{index}.png" for index in range(2))
    height, width = shape
    Image.new("RGB", (width, height), (61, 127, 193)).save(first, compress_level=9)
    os.link(first, second)
    return first, second




def oversized_png_pair(directory):
    """CRC-valid PNG headers with a tiny, deliberately incomplete raster.

    A 65536-square header exceeds normal decoder pixel limits. No large image
    is generated, decompressed or allocated by the fixture generator.
    """
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    header = struct.pack(">IIBBBBB", 65536, 65536, 8, 2, 0, 0, 0)
    payload = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
               + chunk(b"IDAT", zlib.compress(b"\x00\x01\x02\x03")) + chunk(b"IEND", b""))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = tuple(directory / f"oversize-{index}.png" for index in range(2))
    for path in paths:
        path.write_bytes(payload)
    return paths


def _oversized_png(ctx):
    paths = oversized_png_pair(ctx.directory / "oversized-headers")
    for options in ({"device": "cpu"}, {"device": "gpu"},
                    {"device": "cpu", "align": True, "alignment_mode": "breathing",
                     "alignment_reference": "previous"}):
        result = ctx.stack(paths, method="weighted_average", auto=True, quality_report=True, **options)
        assert_rejected(result)


def _constant_auto(ctx, shape, device="cpu"):
    paths = constant_pair(ctx.directory / "large-inputs", shape)
    result = ctx.stack(paths, method="depth_map", device=device, auto=True)
    event = require_backend(result)
    image = read_image(result.output)
    assert image.shape == (*shape, 3), f"Large image shape changed: {image.shape}"
    assert image.dtype == np.uint8
    for channel, value in enumerate((61, 127, 193)):
        assert image[..., channel].min() >= value - 1 and image[..., channel].max() <= value + 1, "Auto settings changed constant RGB input"
    ctx.note("auto_input", {"shape": list(image.shape), "megapixels": shape[0] * shape[1] / 1e6})
    ctx.note("execution", event)


def _malformed_pair(ctx, suffix):
    paths = [ctx.directory / f"000-invalid-{index}.{suffix}" for index in range(2)]
    for path in paths:
        path.write_bytes(b"not a valid encoded image\x00\xff")
    return paths


def _reject_malformed(ctx, suffix):
    result = ctx.stack(_malformed_pair(ctx, suffix), method="weighted_average", auto=True, quality_report=True)
    assert_rejected(result)


def _partial_malformed(ctx, suffix):
    fixture = ctx.fixture("focus")
    reference = ctx.stack(fixture, method="weighted_average")
    require_backend(reference)
    bad = _malformed_pair(ctx, suffix)[0]
    result = ctx.stack([bad, *fixture.paths], method="weighted_average", auto=True, quality_report=True)
    if result.returncode:
        assert_rejected(result)
        return
    require_backend(result)
    ctx.note("valid_frame_parity", assert_pixels_close(result.output, reference.output, mean_limit=0, max_limit=0))
    assert bad.name not in [line.strip().split(":")[0] for line in result.stdout.splitlines() if "sharpness" not in line.lower()], "Undecodable input received a sharpness value"


def _directory_inputs(ctx):
    paths = [ctx.directory / f"directory-{index}.png" for index in range(2)]
    for path in paths:
        path.mkdir()
    assert_rejected(ctx.stack(paths, method="weighted_average", auto=True, quality_report=True))


def _literal_glob(ctx):
    fixture = ctx.fixture("focus")
    paths = []
    for index, source in enumerate(fixture.paths):
        path = ctx.directory / f"frame[{index}].png"
        shutil.copyfile(source, path)
        paths.append(path)
    ordinary = ctx.stack(fixture, method="weighted_average")
    literal = ctx.stack(paths, method="weighted_average")
    require_backend(ordinary)
    require_backend(literal)
    ctx.note("literal_path_parity", assert_pixels_close(literal.output, ordinary.output, mean_limit=0, max_limit=0))


def _npy_input(ctx):
    # Identical textured frames isolate decode equivalence from alignment's
    # sensitivity to float-versus-byte luma rounding on differing focus planes.
    fixture = ctx.fixture("identity")
    npy_paths, png_paths = [], []
    for index, source in enumerate(fixture.paths):
        # Equal channels avoid an ambiguous RGB/BGR convention in array files.
        gray = np.rint(read_image(source).mean(axis=2)).astype(np.uint8)
        image = np.repeat(gray[..., None], 3, axis=2)
        npy = ctx.directory / f"array-{index}.npy"
        png = ctx.directory / f"array-{index}.png"
        np.save(npy, image, allow_pickle=False)
        Image.fromarray(image).save(png)
        npy_paths.append(npy)
        png_paths.append(png)
    options = {"method": "weighted_average", "align": True, "alignment_mode": "breathing",
               "alignment_reference": "previous", "auto": True, "quality_report": True}
    actual, reference = ctx.stack(npy_paths, **options), ctx.stack(png_paths, **options)
    require_backend(actual)
    require_backend(reference)
    ctx.note("array_file_parity", assert_pixels_close(actual.output, reference.output, mean_limit=0, max_limit=0))
    ctx.note("image", validate_image(actual.output, shape=fixture.shape, dtype="uint8", min_range=20))


def _raw_legacy_alignment(ctx):
    fixture = ctx.fixture("bayer_dng")
    options = {"method": "weighted_average", "bit_depth": 16, "output_format": "tif"}
    reference = ctx.stack(fixture, **options)
    actual = ctx.stack(fixture, **options, auto=True, quality_report=True, align=True,
                       alignment_mode="breathing", alignment_reference="previous")
    require_backend(reference)
    require_backend(actual)
    ctx.note("image", validate_image(actual.output, shape=fixture.metadata["reference_shape"],
                                     dtype="uint16", min_range=10000, genuine_16bit=True))
    ctx.note("identity_raw_alignment", assert_pixels_close(actual.output, reference.output, mean_limit=0, max_limit=0))


def coverage_cli_cases():
    cases = [
        Case("cli.coverage.auto.medium", "cli", partial(_constant_auto, shape=(3000, 3001)), "Auto settings preserve RGB at nine megapixels"),
        Case("cli.coverage.auto.large", "cli", partial(_constant_auto, shape=(4600, 4600)), "Auto settings preserve RGB above twenty megapixels"),
        Case("cli.coverage.auto.unmeasured", "cli", partial(_constant_auto, shape=(1000, 1100), device="auto"), "Automatic execution handles large images without prescribing a strategy"),
        Case("cli.coverage.raw.legacy-alignment", "cli", _raw_legacy_alignment, "RAW auto detection, quality reporting and sequential alignment preserve identity"),
        Case("cli.coverage.input.npy", "cli", _npy_input, "Real NumPy image files agree with equivalent PNG inputs"),
        Case("cli.coverage.input.literal-glob", "cli", _literal_glob, "Existing filenames with glob characters remain literal inputs"),
        Case("cli.coverage.input.directories", "cli", _directory_inputs, "Directories fail image decoding without publishing output"),
        Case("cli.coverage.reject.oversize-png", "cli", _oversized_png, "Oversized PNG headers fail safely through CPU, GPU and alignment decoders"),
    ]
    for suffix in ("png", "dng", "npy", "unknown"):
        cases.extend([
            Case(f"cli.coverage.reject.{suffix}", "cli", partial(_reject_malformed, suffix=suffix), "Malformed files fail with diagnostics and no partial output"),
            Case(f"cli.coverage.partial.{suffix}", "cli", partial(_partial_malformed, suffix=suffix), "Unreadable inputs fail cleanly or preserve the valid-frame result"),
        ])
    return cases
