"""Negative checks for the portable external-error and generated-file contracts."""
import importlib.util
from types import SimpleNamespace

import numpy as np
import pytest


def module():
    assert importlib.util.find_spec("stack_conformance.cases.coverage_cli") is not None, "coverage CLI cases missing"
    from stack_conformance.cases import coverage_cli
    return coverage_cli


def test_rejected_stack_requires_error_diagnostic_and_no_output(tmp_path):
    check = module().assert_rejected
    output = tmp_path / "output.png"
    valid = SimpleNamespace(returncode=1, stdout="", stderr="Cannot decode input", output=output)
    check(valid)
    with pytest.raises(AssertionError, match="succeeded"):
        check(SimpleNamespace(**{**vars(valid), "returncode": 0}))
    with pytest.raises(AssertionError, match="diagnostic"):
        check(SimpleNamespace(**{**vars(valid), "stderr": ""}))
    with pytest.raises(AssertionError, match="diagnostic"):
        check(SimpleNamespace(**{**vars(valid), "stdout": "Application banner", "stderr": ""}))
    output.write_bytes(b"partial output")
    with pytest.raises(AssertionError, match="published"):
        check(valid)


def test_constant_pair_is_small_rgb_png_with_distinct_input_names(tmp_path):
    from PIL import Image
    paths = module().constant_pair(tmp_path, (193, 257))
    assert len(paths) == 2 and len(set(paths)) == 2
    for path in paths:
        with Image.open(path) as image:
            data = np.asarray(image)
        assert data.shape == (193, 257, 3) and data.dtype == np.uint8
        np.testing.assert_array_equal(data[0, 0], (61, 127, 193))
        assert np.all(data == data[0, 0])
        assert path.stat().st_size < 3000


def test_cache_damage_requires_real_owned_files_and_rejects_symlinks(tmp_path):
    damage = module().corrupt_regular_files
    cache = tmp_path / "cache"
    cache.mkdir()
    with pytest.raises(AssertionError, match="No cache files"):
        damage(cache)
    nested = cache / "nested"
    nested.mkdir()
    entry = nested / "opaque-cache-entry"
    entry.write_bytes(b"real prior state")
    assert damage(cache) == [entry]
    assert entry.read_bytes() != b"real prior state"
    outside = tmp_path / "outside"
    outside.write_bytes(b"must stay intact")
    (cache / "link").symlink_to(outside)
    with pytest.raises(AssertionError, match="symlink"):
        damage(cache)
    assert outside.read_bytes() == b"must stay intact"


def test_cli_coverage_catalog_has_public_input_and_state_contracts():
    cases = module().coverage_cli_cases()
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids))
    assert all(case.suite == "cli" for case in cases)
    for name in ("auto.medium", "auto.large", "auto.unmeasured", "raw.legacy-alignment",
                 "input.npy", "input.literal-glob", "input.directories", "cache.recovery"):
        assert f"cli.coverage.{name}" in ids
    for suffix in ("png", "dng", "npy", "unknown"):
        assert f"cli.coverage.reject.{suffix}" in ids
        assert f"cli.coverage.partial.{suffix}" in ids


def test_oversized_png_declares_large_frame_without_large_payload(tmp_path):
    import struct
    from PIL import Image
    assert hasattr(module(), "oversized_png_pair"), "Oversized PNG fixture missing"
    paths = module().oversized_png_pair(tmp_path)
    assert len(paths) == len(set(paths)) == 2
    for path in paths:
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == (65536, 65536)
        assert len(data) < 128
        with pytest.raises(Image.DecompressionBombError):
            Image.open(path)
    assert "cli.coverage.reject.oversize-png" in {case.id for case in module().coverage_cli_cases()}
