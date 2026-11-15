"""Immutable decoded-image references, independent of target implementation."""
import hashlib
import fnmatch
import json
from pathlib import Path
import numpy as np

from .validators import read_image


class Baseline:
    def __init__(self, directory, *, record=False, mean_limit=None, peak_limit=None):
        self.directory = Path(directory)
        self.record = record
        self.mean_limit = mean_limit
        self.peak_limit = peak_limit
        self.manifest = {"schema_version": 1, "cases": {}, "case_suites": {}, "contracts": {}}
        if record:
            if self.directory.exists() and any(self.directory.iterdir()):
                raise ValueError(f"baseline already exists: {self.directory}")
            self.directory.mkdir(parents=True, exist_ok=True)
        else:
            self.manifest = json.loads((self.directory / "manifest.json").read_text())
            if self.manifest.get("schema_version") != 1:
                raise ValueError("unsupported baseline schema")

    def validate_selection(self, cases, *, suites=None, patterns=None):
        if self.record:
            return
        expected = {ident for ident in self.manifest["cases"]
                    if (not suites or self.manifest.get("case_suites", {}).get(ident, ident.split(".")[0]) in suites)
                    and (not patterns or any(fnmatch.fnmatchcase(ident, pattern) for pattern in patterns))}
        actual = {case.id for case in cases}
        if actual != expected:
            raise ValueError(f"baseline case inventory changed: missing={sorted(expected - actual)}, added={sorted(actual - expected)}")

    def check(self, case_id, outputs, *, suite=None, contract=None):
        contract = json.loads(json.dumps(contract or {}, default=str))
        if self.record:
            record = {}
            for name, path in sorted(outputs.items()):
                pixels = read_image(path)
                filename = hashlib.sha256(f"{case_id}/{name}".encode()).hexdigest() + ".npz"
                dest = self.directory / filename
                np.savez_compressed(dest, pixels=pixels)
                exposure = "exposure_fusion" in case_id or any(
                    request.get("options", {}).get("method") == "exposure_fusion"
                    for request in contract.get("requests", []))
                precise_16bit = pixels.dtype.kind == "u" and pixels.dtype.itemsize == 2 and not exposure
                mean_limit = self.mean_limit if self.mean_limit is not None else (8 / 65535 if precise_16bit else 0.5 / 255)
                peak_limit = self.peak_limit if self.peak_limit is not None else (128 / 65535 if precise_16bit else 3 / 255)
                record[name] = {"file": filename, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                                "shape": list(pixels.shape), "dtype": str(pixels.dtype),
                                "mean_limit": mean_limit, "peak_limit": peak_limit}
            self.manifest["cases"][case_id] = record
            self.manifest["case_suites"][case_id] = suite or case_id.split(".")[0]
            self.manifest["contracts"][case_id] = contract
            return
        assert case_id in self.manifest["cases"], f"baseline has no case: {case_id}"
        assert contract == self.manifest.get("contracts", {}).get(case_id, {}), f"fixture/parameter contract changed for {case_id}"
        expected = self.manifest["cases"][case_id]
        assert set(outputs) == set(expected), f"output inventory changed for {case_id}: {set(outputs)} != {set(expected)}"
        for name, path in sorted(outputs.items()):
            item = expected[name]
            stored = (self.directory / item["file"]).resolve()
            assert stored.is_relative_to(self.directory.resolve()), "invalid baseline output path"
            assert hashlib.sha256(stored.read_bytes()).hexdigest() == item["sha256"], "baseline checksum changed"
            with np.load(stored, allow_pickle=False) as archive:
                reference = archive["pixels"]
            actual = read_image(path)
            assert actual.shape == reference.shape, f"output shape changed: {actual.shape} != {reference.shape}"
            assert actual.dtype == reference.dtype, f"output dtype changed: {actual.dtype} != {reference.dtype}"
            assert np.isfinite(actual).all(), "output contains nonfinite pixels"
            scale = np.iinfo(actual.dtype).max if np.issubdtype(actual.dtype, np.integer) else 1.0
            error = np.abs(actual.astype(np.float64) - reference.astype(np.float64)) / scale
            assert error.mean() <= item["mean_limit"], f"mean pixel error {error.mean():.7f} exceeds {item['mean_limit']:.7f}"
            assert error.max(initial=0) <= item["peak_limit"], f"peak pixel error {error.max():.7f} exceeds {item['peak_limit']:.7f}"

    def save(self, provenance):
        if self.record:
            self.manifest["provenance"] = provenance
            (self.directory / "manifest.json").write_text(json.dumps(self.manifest, indent=2) + "\n")
