"""Contracts for the R50 camera-metadata reference adapter."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pancake_conformance.adapters.pancake.cr3_reference import (
    camera_crop,
    camera_saturation,
    decode,
    orient,
)


def sizes(**changes):
    """A made-up camera rectangle with offsets in both raw and visible coordinates."""
    return SimpleNamespace(
        **(
            dict(
                raw_width=17,
                raw_height=13,
                left_margin=3,
                top_margin=2,
                width=11,
                height=9,
                crop_left_margin=5,
                crop_top_margin=3,
                crop_width=7,
                crop_height=4,
                flip=0,
            )
            | changes
        )
    )


def test_camera_rectangle_maps_to_uncropped_visible_raster():
    crop = camera_crop(sizes())
    assert (crop.rows, crop.columns) == (slice(1, 5), slice(2, 9))
    assert crop.shape == (4, 7, 3)
    assert camera_crop(sizes(flip=6)).shape == (7, 4, 3)


@pytest.mark.parametrize(
    "changes",
    [
        {"crop_left_margin": 2},
        {"crop_top_margin": 1},
        {"crop_width": 0},
        {"crop_height": 10},
        {"crop_width": 10},
        {"left_margin": -1},
        {"raw_width": 13},
        {"raw_height": 100_000},
        {"flip": -1},
        {"flip": 8},
    ],
)
def test_invalid_or_outside_crop_is_rejected(changes):
    with pytest.raises(ValueError):
        camera_crop(sizes(**changes))


def metadata(**changes):
    return SimpleNamespace(
        **(
            dict(
                camera_white_level_per_channel=[7100] * 4,
                black_level_per_channel=[500] * 4,
                camera_whitebalance=[2, 1, 1.6, 1],
                rgb_xyz_matrix=np.eye(4, 3),
            )
            | changes
        )
    )


def test_saturation_uses_camera_tag_after_black_subtraction():
    assert camera_saturation(metadata()) == 6600


@pytest.mark.parametrize(
    "changes",
    [
        {"camera_white_level_per_channel": None},
        {"camera_white_level_per_channel": [7000, 7100, 7000, 7100]},
        {"black_level_per_channel": [500, 501, 500, 501]},
        {"black_level_per_channel": [7200] * 4},
        {"camera_whitebalance": [np.nan, 1, 2, 1]},
        {"rgb_xyz_matrix": np.zeros((4, 3))},
    ],
)
def test_incomplete_camera_calibration_is_rejected(changes):
    with pytest.raises(ValueError):
        camera_saturation(metadata(**changes))


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        (0, [[1, 2, 3], [4, 5, 6]]),
        (1, [[3, 2, 1], [6, 5, 4]]),
        (2, [[4, 5, 6], [1, 2, 3]]),
        (3, [[6, 5, 4], [3, 2, 1]]),
        (4, [[1, 4], [2, 5], [3, 6]]),
        (5, [[3, 6], [2, 5], [1, 4]]),
        (6, [[4, 1], [5, 2], [6, 3]]),
        (7, [[6, 3], [5, 2], [4, 1]]),
    ],
)
def test_crop_is_oriented_in_sensor_order(flag, expected):
    rgb = np.repeat(np.array([[[1], [2], [3]], [[4], [5], [6]]]), 3, axis=2)
    assert orient(rgb, flag)[:, :, 0].tolist() == expected


def test_truncated_cr3_reports_its_path_without_thumbnail_fallback(tmp_path: Path):
    source = tmp_path / "truncated.CR3"
    source.write_bytes(bytes.fromhex("00000018667479706372782000000001"))
    with pytest.raises(ValueError, match="truncated.CR3"):
        decode(source)
