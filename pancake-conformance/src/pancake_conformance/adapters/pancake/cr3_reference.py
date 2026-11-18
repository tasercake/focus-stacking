"""R50 reference ingest using the camera's CR3 crop and calibrated RGB16."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rawpy

POLICY = "camera-recommended-cr3-srgb-v1"
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_SENSOR_PIXELS = 50_000_000
MAX_SENSOR_AXIS = 32768


@dataclass(frozen=True)
class CameraCrop:
    """Recommended rectangle relative to LibRaw's unrotated visible raster."""

    rows: slice
    columns: slice
    flip: int

    @property
    def shape(self):
        """Return the oriented raster's HWC shape."""
        height = self.rows.stop - self.rows.start
        width = self.columns.stop - self.columns.start
        return (width, height, 3) if self.flip & 4 else (height, width, 3)


def camera_crop(sizes):
    """Validate that the camera rectangle lies entirely in the decoded sensor area."""
    if (
        not 0 < sizes.raw_width <= MAX_SENSOR_AXIS
        or not 0 < sizes.raw_height <= MAX_SENSOR_AXIS
        or sizes.raw_width * sizes.raw_height > MAX_SENSOR_PIXELS
        or not 0 <= sizes.left_margin < sizes.raw_width
        or not 0 <= sizes.top_margin < sizes.raw_height
        or not 0 < sizes.width <= sizes.raw_width - sizes.left_margin
        or not 0 < sizes.height <= sizes.raw_height - sizes.top_margin
        or not 0 <= sizes.flip <= 7
    ):
        raise ValueError("invalid CR3 sensor or orientation metadata")
    x = sizes.crop_left_margin - sizes.left_margin
    y = sizes.crop_top_margin - sizes.top_margin
    width, height = sizes.crop_width, sizes.crop_height
    if (
        x < 0
        or y < 0
        or not 0 < width <= sizes.width - x
        or not 0 < height <= sizes.height - y
    ):
        raise ValueError("camera-recommended CR3 crop is outside the decoded sensor")
    return CameraCrop(slice(y, y + height), slice(x, x + width), sizes.flip)


def camera_saturation(raw):
    """Get the camera white point in post-black units used by LibRaw's user_sat."""
    white = raw.camera_white_level_per_channel
    black = raw.black_level_per_channel
    if (
        not white
        or len(white) != 4
        or len(black) != 4
        or len(set(white)) != 1
        or len(set(black)) != 1
        or not 0 <= black[0] < white[0] <= 65535
    ):
        raise ValueError(
            "CR3 reference requires a common camera saturation and black level"
        )
    wb = raw.camera_whitebalance
    matrix = np.asarray(raw.rgb_xyz_matrix)
    if (
        len(wb) != 4
        or not all(np.isfinite(gain) and gain > 0 for gain in wb[:3])
        or matrix.shape != (4, 3)
        or not np.isfinite(matrix).all()
        or np.linalg.matrix_rank(matrix) != 3
    ):
        raise ValueError("CR3 reference requires camera white balance and calibration")
    return white[0] - black[0]


def orient(samples, flip):
    """Apply LibRaw's three sensor-orientation bits to an already cropped raster."""
    if flip & 1:
        samples = samples[:, ::-1]
    if flip & 2:
        samples = samples[::-1]
    if flip & 4:
        samples = samples.transpose(1, 0, 2)
    return samples


def open_cr3(path):
    """Open a bounded regular Canon CR3 file using the independent RawPy decoder."""
    size = path.stat().st_size
    if not path.is_file() or not 12 <= size <= MAX_SOURCE_BYTES:
        raise ValueError("invalid CR3 source extent")
    with path.open("rb") as stream:
        if stream.read(12)[4:] != b"ftypcrx ":
            raise ValueError("missing Canon CR3 file brand")
    return rawpy.imread(str(path))


def geometry(path):
    """Read the oriented camera geometry and calibration without preparing image input."""
    path = Path(path)
    try:
        with open_cr3(path) as raw:
            sizes = raw.sizes
            crop = camera_crop(sizes)
            return {
                "policy": POLICY,
                "sensor_shape_hw": [sizes.raw_height, sizes.raw_width],
                "camera_crop_xywh": [
                    sizes.crop_left_margin,
                    sizes.crop_top_margin,
                    sizes.crop_width,
                    sizes.crop_height,
                ],
                "oriented_shape_hwc": list(crop.shape),
                "orientation": crop.flip,
                "camera_saturation_after_black": camera_saturation(raw),
            }
    except (OSError, ValueError, rawpy.LibRawError) as error:
        raise ValueError(f"CR3 metadata failed for {path}: {error}") from error


def decode(path):
    """Develop every requested original as calibrated RGB16, then crop and orient."""
    path = Path(path)
    try:
        with open_cr3(path) as raw:
            sizes = raw.sizes
            crop = camera_crop(sizes)
            pixels = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                adjust_maximum_thr=0,
                user_sat=camera_saturation(raw),
                output_bps=16,
                output_color=rawpy.ColorSpace.sRGB,
                gamma=(2.4, 12.92),
                user_flip=0,
            )
        if pixels.shape != (sizes.height, sizes.width, 3) or pixels.dtype != np.uint16:
            raise ValueError("unexpected CR3 RGB16 shape or storage from LibRaw")
        return orient(pixels[crop.rows, crop.columns], crop.flip)
    except (OSError, ValueError, rawpy.LibRawError) as error:
        raise ValueError(f"CR3 decode failed for {path}: {error}") from error


def main():
    """Run the pinned reference CLI with camera-metadata CR3 ingest."""
    if len(sys.argv) == 3 and sys.argv[1] == "--cr3-geometry":
        print(json.dumps(geometry(sys.argv[2])))
        return
    # The benchmark launcher has the pinned ChimpStackr checkout as its cwd.
    sys.path.insert(0, str(Path.cwd()))
    from src.cli import main as reference_main
    from src.ImageLoadingHandler import ImageDecodeError, ImageLoadingHandler

    original = ImageLoadingHandler._load_raw_float32

    def load_raw_float32(loader, path):
        if Path(path).suffix.lower() != ".cr3":
            return original(loader, path)
        try:
            rgb = decode(path)
        except ValueError as error:
            raise ImageDecodeError(str(error)) from error
        return loader._to_float32_bgr(rgb[:, :, ::-1])

    ImageLoadingHandler._load_raw_float32 = load_raw_float32
    try:
        reference_main()
    finally:
        ImageLoadingHandler._load_raw_float32 = original


if __name__ == "__main__":
    main()
