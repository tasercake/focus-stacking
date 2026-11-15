"""Generated corpus must be portable, deterministic, and independent of target code."""
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image


def test_focus_fixture_is_deterministic_and_contains_complementary_planes(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    left = generate_fixture("focus", tmp_path / "left")
    right = generate_fixture("focus", tmp_path / "right")
    assert len(left.paths) == 3
    assert left.shape == (129, 193, 3)
    assert left.truth_path.is_file()
    for a, b in zip(left.paths, right.paths, strict=True):
        assert a.read_bytes() == b.read_bytes()
    assert not np.array_equal(np.array(Image.open(left.paths[0])), np.array(Image.open(left.paths[1])))
    assert left.metadata["regions"]


def test_16bit_fixture_has_real_precision(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture("precision16", tmp_path)
    image = tifffile.imread(fixture.paths[0])
    assert image.dtype == np.uint16
    assert image.shape == fixture.shape
    assert np.unique(image).size > 256
    assert np.any(image % 257 != 0)


@pytest.mark.parametrize("kind", ["translation", "rotation", "similarity", "affine", "breathing"])
def test_geometry_fixture_records_ground_truth(tmp_path, kind):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture(kind, tmp_path)
    assert len(fixture.paths) == 4
    assert len(fixture.metadata["source_transforms"]) == len(fixture.paths)
    assert fixture.shape == (257, 321, 3)
    assert fixture.truth_path.is_file()
    assert all(Path(path).is_file() for path in fixture.paths)


@pytest.mark.parametrize("kind", ["flat", "odd", "exposure", "grayscale", "rgba", "formats", "unicode"])
def test_fixture_families_exist(tmp_path, kind):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture(kind, tmp_path)
    assert len(fixture.paths) >= 2
    assert all(path.is_file() for path in fixture.paths)


def test_unknown_fixture_is_rejected(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    with pytest.raises(ValueError, match="Unknown fixture"):
        generate_fixture("not-real", tmp_path)


@pytest.mark.parametrize("kind,count", [("deep", 9), ("identity", 4)])
def test_deep_and_identical_geometry_controls(tmp_path, kind, count):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture(kind, tmp_path)
    assert len(fixture.paths) == count
    if kind == "identity":
        assert all(np.array_equal(np.array(Image.open(path)), tifffile.imread(fixture.truth_path)) for path in fixture.paths)


@pytest.mark.parametrize("kind", ["float01", "float255", "exr", "grayscale16", *[f"orientation{i}" for i in range(2, 9)]])
def test_extended_format_corpus_is_generated_without_target(tmp_path, kind):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture(kind, tmp_path)
    assert len(fixture.paths) == 3
    assert all(path.is_file() for path in fixture.paths)
    if kind.startswith("orientation"):
        assert Image.open(fixture.paths[0]).getexif()[274] == int(kind[-1])


def test_generated_bayer_dng_is_small_and_has_standard_cfa_metadata(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture("bayer_dng", tmp_path)
    assert len(fixture.paths) == 3
    assert all(path.suffix == ".dng" and path.stat().st_size < 60000 for path in fixture.paths)
    with tifffile.TiffFile(fixture.paths[0]) as file:
        page = file.pages[0]
        assert page.photometric == 32803
        assert tuple(page.tags[50706].value) == (1, 4, 0, 0)
        assert tuple(page.tags[33421].value) == (2, 2)
        assert tuple(page.tags[33422].value) == (0, 1, 1, 2)
        assert page.asarray().dtype == np.uint16


def test_mixed_dimensions_fixture_records_reference_shape(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture("mixed_dimensions", tmp_path)
    assert len({Image.open(path).size for path in fixture.paths}) > 1
    assert fixture.metadata["reference_shape"] == [129, 193, 3]


def test_lifecycle_workload_uses_unique_paths_with_shared_generated_pixels(tmp_path):
    from stack_conformance.fixtures import generate_fixture
    fixture = generate_fixture("lifecycle", tmp_path)
    assert fixture.shape == (1024, 1536, 3)
    assert len(fixture.paths) == 64
    assert len(set(fixture.paths)) == 64
    assert all(path.is_file() for path in fixture.paths)
    assert len({path.stat().st_ino for path in fixture.paths}) == 1
    assert np.array_equal(np.array(Image.open(fixture.paths[0])), np.array(Image.open(fixture.truth_path)))
    assert len(fixture.metadata["source_transforms"]) == 64
