"""Launch-boundary contracts for pure timing runs and diagnostic proof."""

import json
import tempfile
import unittest
from pathlib import Path

from p10 import ADAPTERS, _assert_completion, _environment
from pancake_conformance.target import TargetSpec

REFERENCE = ADAPTERS / "chimpstackr_reference/chimpstackr.toml"


class LaunchContracts(unittest.TestCase):
    def test_reference_profiler_is_absent_from_timed_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = TargetSpec.load(REFERENCE)
            plain = _environment(target, root / "warm", root, 8, None, None, False)
            diagnostic = _environment(
                target, root / "diagnostic", root, 8, None, None, True
            )
            self.assertNotIn("CHIMPSTACKR_CONFORMANCE_EVENTS", plain)
            self.assertNotIn("COVERAGE_PROCESS_START", plain)
            self.assertEqual(
                diagnostic["CHIMPSTACKR_CONFORMANCE_EVENTS"], str(root / "events.jsonl")
            )
            self.assertEqual(plain["NUMBA_NUM_THREADS"], "8")
            self.assertNotEqual(plain["NUMBA_CACHE_DIR"], diagnostic["NUMBA_CACHE_DIR"])

    def test_matching_model_cannot_substitute_for_the_correct_physical_card(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            completion = {
                "event": "stack_complete",
                "completed": True,
                "actual_backend": "gpu",
                "runtime": "wgpu-vulkan",
                "device": "NVIDIA GeForce RTX 3090",
                "device_pci_address": "0000:01:00.0",
            }
            events.write_text(json.dumps(completion) + "\n")
            self.assertEqual(
                _assert_completion(
                    events,
                    "gpu",
                    "wgpu-vulkan",
                    "NVIDIA GeForce RTX 3090",
                    "00000000:01:00.0",
                ),
                completion,
            )
            with self.assertRaisesRegex(ValueError, "physical PCI"):
                _assert_completion(
                    events,
                    "gpu",
                    "wgpu-vulkan",
                    "NVIDIA GeForce RTX 3090",
                    "00000000:02:00.0",
                )

    def test_backend_proof_rejects_fallback_wrong_runtime_and_wrong_device(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            completion = {
                "event": "stack_complete",
                "completed": True,
                "actual_backend": "gpu",
                "runtime": "cuda",
                "device": "NVIDIA GeForce RTX 3090",
            }
            events.write_text(json.dumps(completion) + "\n")
            self.assertEqual(
                _assert_completion(events, "gpu", "cuda", "NVIDIA GeForce RTX 3090"),
                completion,
            )
            with self.assertRaisesRegex(ValueError, "completed runtime"):
                _assert_completion(
                    events, "gpu", "wgpu-vulkan", "NVIDIA GeForce RTX 3090"
                )
            with self.assertRaisesRegex(ValueError, "physical GPU"):
                _assert_completion(events, "gpu", "cuda", "NVIDIA GeForce RTX 4090")
            with events.open("a") as stream:
                stream.write('{"event":"backend_fallback"}\n')
            with self.assertRaisesRegex(ValueError, "backend fallback"):
                _assert_completion(events, "gpu", "cuda", "NVIDIA GeForce RTX 3090")
