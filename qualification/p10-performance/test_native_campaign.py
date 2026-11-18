"""Contracts for preparing complete physical GUI sample scenarios."""

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from linux_latency import _physical_execution_proof
from native_campaign import build_lifecycle, build_viewer
from PIL import Image

IDENTITY = {
    "commit": "5216ba4227e14033483a21bb5eca1c6c168ef840",
    "binary_sha256": "0" * 64,
    "gpu_uuid": "GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac",
}


class CampaignPreparation(unittest.TestCase):
    def test_exact_native_lifecycle_sequence_and_counts(self):
        fixture = build_lifecycle(IDENTITY, "lifecycle")
        real = build_lifecycle(IDENTITY, "D150")
        for scenario, method in ((fixture, "laplacian"), (real, "hybrid")):
            actions = [
                step for step in scenario["steps"] if step["kind"] == "lifecycle"
            ]
            self.assertEqual(
                Counter(step["operation"] for step in actions),
                {"pause": 30, "cancel": 30},
            )
            self.assertEqual(
                [item["operation"] for item in actions[:4]],
                ["pause", "cancel", "pause", "cancel"],
            )
            self.assertIn(
                {"kind": "click", "at": {"control": f"method.{method}"}},
                scenario["steps"][1]["inputs"],
            )
            self.assertEqual(scenario["steps"][-1]["worker_phase"], "completed")

    def test_viewer_counts_and_distinguishable_fixed_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            Image.new("RGB", (2, 2), (10, 20, 30)).save(root / "before.png")
            Image.new("RGB", (2, 2), (40, 50, 60)).save(root / "after.png")
            trial = {
                "input": {"kind": "click", "at": {"control": "test-fixture"}},
                "before": [{"point": [1, 1], "png": "before.png"}],
                "after": [{"point": [1, 1], "png": "after.png"}],
            }
            cases = ("source", "result", "pan", "zoom", "comparison")
            manifest = {
                "identity": IDENTITY,
                "renderer": "physical-wgpu-vulkan",
                "witness_provenance": {"diagnostic": "test fixture only"},
                "cohorts": {
                    condition: {"setup": [], "trials": {name: trial for name in cases}}
                    for condition in ("idle", "loaded")
                },
            }
            planned = build_viewer(manifest, root)
            samples = Counter(
                (step["condition"], step["action"])
                for step in planned["steps"]
                if step["kind"] == "viewer"
            )
            self.assertEqual(len(samples), 10)
            self.assertTrue(all(count == 40 for count in samples.values()))
            trial["after"] = trial["before"]
            with self.assertRaisesRegex(ValueError, "before.*after"):
                build_viewer(manifest, root)


class PhysicalCampaignContracts(unittest.TestCase):
    def test_actual_numerical_completion_must_use_the_same_pci_card(self):
        completion = {
            "event": "stack_complete",
            "completed": True,
            "actual_backend": "gpu",
            "runtime": "wgpu-vulkan",
            "physical_gpu": True,
            "device_pci_address": "0000:01:00.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            events.write_text(json.dumps(completion) + "\n")
            self.assertEqual(
                _physical_execution_proof(events, "00000000:01:00.0"), [completion]
            )
            with self.assertRaisesRegex(ValueError, "physical wgpu"):
                _physical_execution_proof(events, "00000000:02:00.0")
            events.write_text(json.dumps(dict(completion, actual_backend="cpu")) + "\n")
            with self.assertRaisesRegex(ValueError, "physical wgpu"):
                _physical_execution_proof(events, "00000000:01:00.0")
