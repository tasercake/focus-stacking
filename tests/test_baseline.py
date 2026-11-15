import numpy as np
import pytest
from PIL import Image


def test_frozen_baseline_detects_changed_pixels_and_missing_outputs(tmp_path):
    from stack_conformance.baseline import Baseline
    image = tmp_path / "output.png"
    Image.fromarray(np.full((10, 12, 3), 50, np.uint8)).save(image)
    baseline = Baseline(tmp_path / "baseline", record=True)
    baseline.check("case", {"main": image})
    baseline.save({"target": "reference"})
    frozen = Baseline(tmp_path / "baseline")
    frozen.check("case", {"main": image})
    with pytest.raises(AssertionError, match="output"):
        frozen.check("case", {})
    Image.fromarray(np.full((10, 12, 3), 90, np.uint8)).save(image)
    with pytest.raises(AssertionError, match="pixel"):
        frozen.check("case", {"main": image})


def test_existing_baseline_cannot_be_overwritten(tmp_path):
    from stack_conformance.baseline import Baseline
    path = tmp_path / "frozen"
    baseline = Baseline(path, record=True)
    baseline.save({})
    with pytest.raises(ValueError, match="exists"):
        Baseline(path, record=True)


def test_baseline_rejects_undeclared_case(tmp_path):
    from stack_conformance.baseline import Baseline
    Baseline(tmp_path / "frozen", record=True).save({})
    with pytest.raises(AssertionError, match="case"):
        Baseline(tmp_path / "frozen").check("new", {})


def test_baseline_rejects_removed_case_but_accepts_explicit_subset(tmp_path):
    from stack_conformance.baseline import Baseline
    from stack_conformance.model import Case
    path = tmp_path / "frozen"
    baseline = Baseline(path, record=True)
    baseline.check("one", {}, suite="cli")
    baseline.check("two", {}, suite="algorithms")
    baseline.save({})
    frozen = Baseline(path)
    selected = [Case("one", "cli", lambda ctx: None)]
    with pytest.raises(ValueError, match="inventory"):
        frozen.validate_selection(selected)
    frozen.validate_selection(selected, suites=["cli"])


def test_baseline_freezes_fixture_and_parameter_contract(tmp_path):
    from stack_conformance.baseline import Baseline
    path = tmp_path / "frozen"
    baseline = Baseline(path, record=True)
    baseline.check("case", {}, contract={"requests": [{"method": "hybrid"}]})
    baseline.save({})
    with pytest.raises(AssertionError, match="contract"):
        Baseline(path).check("case", {}, contract={"requests": [{"method": "laplacian"}]})


def test_baseline_does_not_tolerate_16bit_to_8bit_quantization(tmp_path):
    import tifffile
    from stack_conformance.baseline import Baseline
    image = tmp_path / "precision.tif"
    pixels = ((np.arange(30 * 40 * 3, dtype=np.uint32) * 17 + 6000) % 65535).reshape(30, 40, 3).astype(np.uint16)
    tifffile.imwrite(image, pixels, photometric="rgb")
    recorded = Baseline(tmp_path / "frozen", record=True)
    recorded.check("precision", {"main": image})
    recorded.save({})
    quantized = np.rint(pixels.astype(float) / 257).astype(np.uint16) * 257
    tifffile.imwrite(image, quantized, photometric="rgb")
    with pytest.raises(AssertionError, match="pixel"):
        Baseline(tmp_path / "frozen").check("precision", {"main": image})
