"""Small generated image corpus; no target language or UI dependencies.

Coordinates use RGB channel order and top-left image origin. Geometry fixtures
record source-from-reference transforms in x/y order. Generator version is part
of metadata so a frozen conformance release can pin fixture semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import affine_transform, gaussian_filter
import tifffile

GENERATOR_VERSION = 2
GEOMETRY_FIXTURES = ("translation", "rotation", "similarity", "affine", "breathing")
FIXTURE_NAMES = ("focus", "flat", "zero_regions", "odd", "precision16", *GEOMETRY_FIXTURES,
                 "exposure", "grayscale", "rgba", "formats", "unicode", "deep", "deep_nonrepeating", "identity",
                 "float01", "float255", "exr", "grayscale16", "bayer_dng", "mixed_dimensions", "lifecycle",
                 *[f"orientation{i}" for i in range(1, 9)])


@dataclass(frozen=True)
class Fixture:
    name: str
    paths: tuple[Path, ...]
    shape: tuple[int, ...]
    truth_path: Path | None
    metadata: dict


def _texture(height: int, width: int) -> np.ndarray:
    """Seeded broadband texture plus colored marks for alignment and RGB checks."""
    rng = np.random.default_rng(731)
    grain = gaussian_filter(rng.uniform(0, 1, (height, width)), 0.7)
    gray = 30 + grain * 180
    image = np.stack((gray * 1.05, gray, gray * 0.85), axis=-1)
    yy, xx = np.mgrid[:height, :width]
    # Broad structures prevent random subpixel noise from being the sole oracle.
    image[(xx - width * 0.25) ** 2 + (yy - height * 0.35) ** 2 < (height * 0.08) ** 2] = (185, 80, 65)
    image[(xx > width * 0.58) & (xx < width * 0.8) & (yy > height * 0.55) & (yy < height * 0.66)] = (60, 170, 100)
    return np.clip(np.rint(image), 0, 255).astype(np.uint8)


def _focus(height: int, width: int) -> tuple[list[np.ndarray], np.ndarray, dict]:
    sharp = _texture(height, width)
    yy, xx = np.mgrid[:height, :width]
    checker = ((xx // 2 + yy // 2) % 2) * 85
    sharp = np.clip(sharp.astype(float) + checker[..., None] - 42, 0, 255).astype(np.uint8)
    blurred = gaussian_filter(sharp.astype(float), (2.5, 2.5, 0))
    split = width // 2
    a, b = blurred.copy(), blurred.copy()
    a[:, :split] = sharp[:, :split]
    b[:, split:] = sharp[:, split:]
    frames = [a.astype(np.uint8), b.astype(np.uint8), blurred.astype(np.uint8)]
    regions = [(16, height - 16, 16, split - 12),
               (16, height - 16, split + 12, width - 16)]
    return frames, sharp, {"regions": regions, "kind": "complementary-focus-planes"}


def _warp(image: np.ndarray, transform: np.ndarray) -> np.ndarray:
    inverse = np.linalg.inv(np.vstack((transform, (0, 0, 1))))
    # scipy addresses pixels in y/x order, while recorded transforms use x/y.
    matrix = inverse[:2, :2][::-1, ::-1]
    offset = inverse[:2, 2][::-1]
    warped = np.empty_like(image)
    for channel in range(3):
        warped[..., channel] = affine_transform(image[..., channel], matrix,
                                               offset, order=1, mode="reflect")
    return warped


def _geometry(name: str) -> tuple[list[np.ndarray], np.ndarray, dict]:
    image = _texture(257, 321)
    # Texture every region so alignment tests do not also trigger the separate
    # weighted-average zero-contrast compatibility defect.
    yy, xx = np.mgrid[:257, :321]
    image = np.clip(image.astype(int) + (((xx + yy) % 2) * 14 - 7)[..., None], 0, 255).astype(np.uint8)
    center = np.array([160.0, 128.0])
    transforms, frames = [], []
    for index in range(4):
        angle = np.deg2rad(index * 0.35 if name == "rotation" else 0)
        scale = 1 + index * 0.004 if name in ("similarity", "breathing") else 1.0
        linear = scale * np.array([[np.cos(angle), -np.sin(angle)],
                                   [np.sin(angle), np.cos(angle)]])
        if name == "affine":
            linear[0, 1] += index * 0.002
            linear[1, 0] -= index * 0.001
        shift = np.array([index * 1.0, -index * 0.5])
        transform = np.column_stack((linear, center - linear @ center + shift))
        frames.append(_warp(image, transform))
        transforms.append(transform.tolist())
    return frames, image, {"source_transforms": transforms,
                           "interior": [32, 225, 32, 289], "kind": name}


def generate_fixture(name: str, root: str | Path) -> Fixture:
    """Generate named fixture below root. Inputs never depend on target code."""
    if name not in FIXTURE_NAMES:
        raise ValueError(f"Unknown fixture: {name}")
    directory = Path(root) / name
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {"generator_version": GENERATOR_VERSION}
    if name == "lifecycle":
        # One generated image, many distinct input paths. Hardlinks keep fixture
        # storage small while the unmodified target still performs real decode,
        # alignment and fusion for every frame. No timing hooks or barriers.
        truth = _texture(1024, 1536)
        first = directory / "frame_00.png"
        Image.fromarray(truth).save(first)
        paths = [first]
        for index in range(1, 64):
            path = directory / f"frame_{index:02d}.png"
            if path.exists():
                path.unlink()
            os.link(first, path)
            paths.append(path)
        metadata.update({"kind": "real-processing-lifecycle-workload", "shape": list(truth.shape),
                         "dtype": "uint8", "input_count": len(paths), "shared_pixel_storage": "hardlinks",
                         "source_transforms": [[[1, 0, 0], [0, 1, 0]] for _ in paths]})
        (directory / "fixture.json").write_text(json.dumps(metadata, indent=2) + "\n")
        return Fixture(name, tuple(paths), tuple(truth.shape), first, metadata)
    if name in GEOMETRY_FIXTURES:
        frames, truth, details = _geometry(name)
        metadata.update(details)
    elif name == "bayer_dng":
        _, truth, _ = _focus(112, 160)
        yy, xx = np.mgrid[:112, :160]
        channels = np.array([[0, 1], [1, 2]])[yy % 2, xx % 2]
        mosaic = np.take_along_axis(truth, channels[..., None], axis=2)[..., 0].astype(np.uint32)
        mosaic = (mosaic * 211 + 2048 + (xx * 73 + yy * 137) % 257).astype(np.uint16)
        frames = [mosaic.copy() for _ in range(3)]
        metadata.update({"reference_shape": [112, 160, 3], "cfa": "RGGB", "black_level": 0,
                         "white_level": 65535, "kind": "synthetic-uncompressed-bayer-dng"})
    elif name == "mixed_dimensions":
        _, truth, details = _focus(129, 193)
        metadata.update(details)
        frames = [truth.copy(), np.asarray(Image.fromarray(truth).resize((181, 121), Image.Resampling.BILINEAR)),
                  np.asarray(Image.fromarray(truth).resize((205, 137), Image.Resampling.BILINEAR))]
        metadata["reference_shape"] = list(truth.shape)
    elif name in ("float01", "float255", "exr", "grayscale16") or name.startswith("orientation"):
        _, truth, _ = _focus(129, 193)
        source = truth.copy()
        if name in ("float01", "float255", "exr"):
            source = source.astype(np.float32)
            if name in ("float01", "exr"):
                source /= 255
        elif name == "grayscale16":
            source = np.rint(source.mean(axis=2) * 257).astype(np.uint16)
            truth = np.repeat((source / 257).astype(np.uint8)[..., None], 3, axis=2)
        elif name.startswith("orientation"):
            transform = {1: None, 2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180,
                         4: Image.Transpose.FLIP_TOP_BOTTOM, 5: Image.Transpose.TRANSPOSE,
                         6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
                         8: Image.Transpose.ROTATE_90}[int(name[-1])]
            truth = np.asarray(Image.fromarray(source).transpose(transform)) if transform is not None else source.copy()
        frames = [source.copy() for _ in range(3)]
    elif name == "identity":
        truth = _texture(257, 321)
        frames = [truth.copy() for _ in range(4)]
    elif name == "precision16":
        yy, xx = np.mgrid[:97, :131]
        base = ((xx * 347 + yy * 151) % 52000 + 6000).astype(np.uint16)
        truth = np.stack((base, (base.astype(np.uint32) * 3 // 4 + 5000).astype(np.uint16),
                          (base.astype(np.uint32) // 2 + 9000).astype(np.uint16)), axis=-1)
        frames = [truth.copy() for _ in range(3)]
    elif name == "zero_regions":
        truth = np.full((65, 99, 3), (83, 127, 173), np.uint8)
        truth[5:25, 5:25] = _texture(20, 20)
        frames = [truth.copy() for _ in range(3)]
    elif name == "flat":
        truth = np.empty((65, 99, 3), np.uint8)
        truth[:] = (83, 127, 173)
        frames = [truth.copy() for _ in range(3)]
    elif name == "exposure":
        truth = _texture(129, 193)
        gradient = np.linspace(0.2, 2.3, 193)[None, :, None]
        scene = truth.astype(float) * gradient
        frames = [np.clip(np.rint(scene * gain), 0, 255).astype(np.uint8)
                  for gain in (0.4, 0.7, 1.0, 1.5, 2.0)]
        truth = np.clip(scene, 0, 255).astype(np.uint8)
    else:
        height, width = (65, 99) if name in ("odd", "deep", "deep_nonrepeating") else (129, 193)
        frames, truth, details = _focus(height, width)
        metadata.update(details)
        if name == "deep_nonrepeating":
            truth = _texture(height, width)
            blurred = gaussian_filter(truth.astype(float), (2.5, 2.5, 0)).astype(np.uint8)
            a, b = blurred.copy(), blurred.copy()
            a[:, :width//2] = truth[:, :width//2]
            b[:, width//2:] = truth[:, width//2:]
            frames = [a, b, blurred]
        if name in ("deep", "deep_nonrepeating"):
            frames = frames * 3
        if name == "grayscale":
            frames = [np.rint(f.mean(axis=2)).astype(np.uint8) for f in frames]
            truth = np.rint(truth.mean(axis=2)).astype(np.uint8)
        elif name == "rgba":
            alpha = np.broadcast_to(np.linspace(0, 255, width).astype(np.uint8), (height, width))
            frames = [np.dstack((f, alpha)) for f in frames]
            # Current contract discards alpha, rather than compositing against black.
        elif name == "formats":
            frames = [truth.copy() for _ in range(4)]
    paths = []
    for index, frame in enumerate(frames):
        extension = ".tif" if name in ("precision16", "float01", "float255", "grayscale16") else ".png"
        if name == "exr":
            extension = ".exr"
        elif name == "bayer_dng":
            extension = ".dng"
        if name == "formats":
            extension = (".png", ".jpg", ".bmp", ".tif")[index]
        stem = f"frame_{index:02d}"
        if name == "unicode":
            stem = f"焦点 café frame {index:02d}"
        path = directory / (stem + extension)
        if extension == ".dng":
            matrix = (10000, 10000, 0, 10000, 0, 10000,
                      0, 10000, 10000, 10000, 0, 10000,
                      0, 10000, 0, 10000, 10000, 10000)
            tags = [(50706, "B", 4, (1, 4, 0, 0), False),
                    (50707, "B", 4, (1, 3, 0, 0), False),
                    (50708, "s", 0, "Conformance Synthetic Bayer", False),
                    (33421, "H", 2, (2, 2), False), (33422, "B", 4, (0, 1, 1, 2), False),
                    (50710, "B", 3, (0, 1, 2), False), (50711, "H", 1, 1, False),
                    (50714, "I", 1, 0, False), (50717, "I", 1, 65535, False),
                    (50721, "2i", 9, matrix, False),
                    (50728, "2I", 3, (1, 1, 1, 1, 1, 1), False),
                    (50778, "H", 1, 21, False),
                    (50719, "I", 2, (0, 0), False), (50720, "I", 2, (160, 112), False)]
            tifffile.imwrite(path, frame, photometric=32803, metadata=None, extratags=tags)
        elif extension == ".exr":
            import OpenEXR
            channels = {channel: np.ascontiguousarray(frame[..., index])
                        for index, channel in enumerate("RGB")}
            OpenEXR.File({}, channels).write(str(path))
        elif extension == ".tif":
            tifffile.imwrite(path, frame, photometric="rgb" if frame.ndim == 3 else "minisblack", metadata=None)
        else:
            if name.startswith("orientation"):
                exif = Image.Exif()
                exif[274] = int(name[-1])
                Image.fromarray(frame).save(path, exif=exif)
            else:
                Image.fromarray(frame).save(path)
        paths.append(path)
    truth_path = directory / "truth.tif"
    tifffile.imwrite(truth_path, truth, photometric="rgb" if truth.ndim == 3 else "minisblack", metadata=None)
    metadata.update({"shape": list(frames[0].shape), "dtype": str(frames[0].dtype),
                     "input_count": len(paths)})
    (directory / "fixture.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return Fixture(name, tuple(paths), tuple(frames[0].shape), truth_path, metadata)
