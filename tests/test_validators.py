"""Oracles must reject representative broken outputs without target imports."""
import numpy as np
import pytest
import tifffile
from PIL import Image


def test_decode_rgb_preserves_channel_order_and_bit_depth(tmp_path):
    from stack_conformance.validators import read_image
    expected = np.zeros((7, 11, 3), np.uint16)
    expected[..., 0] = 12345
    expected[..., 1] = 34567
    expected[..., 2] = 54321
    path = tmp_path / "image.tif"
    tifffile.imwrite(path, expected, photometric="rgb")
    image = read_image(path)
    assert np.array_equal(image, expected)


def test_image_contract_rejects_wrong_shape_dtype_and_flat_output(tmp_path):
    from stack_conformance.validators import validate_image
    path = tmp_path / "image.png"
    Image.fromarray(np.full((13, 17, 3), 127, np.uint8)).save(path)
    with pytest.raises(AssertionError, match="shape"):
        validate_image(path, shape=(13, 16, 3))
    with pytest.raises(AssertionError, match="dtype"):
        validate_image(path, dtype="uint16")
    with pytest.raises(AssertionError, match="dynamic range"):
        validate_image(path, min_range=5)


def test_precision_validator_rejects_8bit_values_in_16bit_container(tmp_path):
    from stack_conformance.validators import validate_image
    data = (np.arange(600).reshape(20, 30) % 256).astype(np.uint16) * 257
    path = tmp_path / "fake16.tif"
    tifffile.imwrite(path, data)
    with pytest.raises(AssertionError, match="precision"):
        validate_image(path, genuine_16bit=True)


def test_pixel_metrics_reject_shape_mismatch_and_measure_region_damage():
    from stack_conformance.validators import pixel_metrics
    expected = np.zeros((20, 30, 3), np.uint8)
    actual = expected.copy()
    actual[:2, :2] = 100
    whole = pixel_metrics(actual, expected)
    region = pixel_metrics(actual, expected, region=(0, 2, 0, 2))
    assert whole["mean_absolute_error"] == pytest.approx(2 / 3)
    assert region["mean_absolute_error"] == 100
    assert region["max_absolute_error"] == 100
    with pytest.raises(AssertionError, match="shape"):
        pixel_metrics(actual, expected[:19])


def test_sharpness_separates_blur_from_texture():
    from stack_conformance.validators import sharpness
    sharp = ((np.indices((32, 40)).sum(axis=0) % 2) * 200).astype(np.uint8)
    flat = np.full_like(sharp, 100)
    assert sharpness(sharp) > 100
    assert sharpness(flat) == 0


def test_image_comparison_uses_decoded_pixels_not_file_bytes(tmp_path):
    from stack_conformance.validators import assert_pixels_close
    data = np.random.default_rng(3).integers(20, 200, (23, 31, 3), dtype=np.uint8)
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.fromarray(data).save(a, compress_level=0)
    Image.fromarray(data).save(b, compress_level=9)
    assert a.read_bytes() != b.read_bytes()
    assert_pixels_close(a, b, mean_limit=0, max_limit=0)
    wrong = data.copy()
    wrong[4:8, 4:8] = 0
    Image.fromarray(wrong).save(b)
    with pytest.raises(AssertionError, match="pixel"):
        assert_pixels_close(a, b, mean_limit=0.01, max_limit=0)


def test_decode_16bit_rgb_png_retains_more_than_eight_bits(tmp_path):
    import png
    from stack_conformance.validators import read_image
    expected = (np.arange(7 * 11 * 3).reshape(7, 11, 3) * 197).astype(np.uint16)
    path = tmp_path / "precise.png"
    with path.open("wb") as stream:
        png.Writer(width=11, height=7, bitdepth=16, greyscale=False).write(stream, expected.reshape(7, -1))
    assert np.array_equal(read_image(path), expected)


def test_decode_float_exr_retains_channel_order_and_range(tmp_path):
    import OpenEXR
    from stack_conformance.validators import read_image
    expected = np.random.default_rng(13).uniform(-0.2, 2, (7, 11, 3)).astype(np.float32)
    path = tmp_path / "float.exr"
    OpenEXR.File({}, {channel: np.ascontiguousarray(expected[..., index]) for index, channel in enumerate("RGB")}).write(str(path))
    assert np.array_equal(read_image(path), expected)


@pytest.mark.parametrize("storage", ["half", "mixed"])
def test_float32_exr_contract_rejects_lower_precision_channel_storage(tmp_path, storage):
    import OpenEXR
    from stack_conformance.validators import validate_image
    path = tmp_path / f"{storage}.exr"
    pixels = np.linspace(0, 1, 7 * 11).reshape(7, 11)
    channels = {channel: pixels.astype(np.float16) for channel in "RGB"}
    if storage == "mixed":
        channels["R"] = pixels.astype(np.float32)
    OpenEXR.File({}, channels).write(str(path))
    with pytest.raises(AssertionError, match="EXR storage precision"):
        validate_image(path, dtype="float32")


def test_float32_exr_contract_reports_native_storage_precision(tmp_path):
    import OpenEXR
    from stack_conformance.validators import validate_image
    path = tmp_path / "float32.exr"
    pixels = np.linspace(0, 1, 7 * 11).reshape(7, 11).astype(np.float32)
    OpenEXR.File({}, {channel: pixels for channel in "RGB"}).write(str(path))
    metadata = validate_image(path, shape=(7, 11, 3), dtype="float32")
    assert metadata["storage_precision"] == {"B": "FLOAT", "G": "FLOAT", "R": "FLOAT"}
