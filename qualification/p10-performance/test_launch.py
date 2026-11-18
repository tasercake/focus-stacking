"""Launch-boundary contracts for pure timing runs and diagnostic proof."""

import json
import tempfile
import unittest
from pathlib import Path

from p10 import (
    ADAPTERS,
    R50_REFERENCE,
    _assert_completion,
    _cleanup_outputs,
    _environment,
    _reference_launch,
)
from pancake_conformance.target import TargetSpec
from protocol import sha256

REFERENCE = ADAPTERS / "chimpstackr_reference/chimpstackr.toml"


class LaunchContracts(unittest.TestCase):
    def test_cuda_library_path_leaves_the_reference_loader_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = TargetSpec.load(REFERENCE)
            cuda = root / "cuda-libraries"
            cuda.mkdir()
            candidate = _environment(
                target,
                root / "candidate",
                root,
                8,
                None,
                "cuda",
                False,
                cuda_library_path=cuda,
            )
            reference = _environment(
                target,
                root / "reference",
                root,
                8,
                None,
                None,
                False,
                cuda_library_path=cuda,
            )
            baseline = _environment(
                target, root / "baseline", root, 8, None, None, False
            )
            self.assertEqual(candidate["LD_LIBRARY_PATH"], str(cuda))
            self.assertEqual(
                reference.get("LD_LIBRARY_PATH"), baseline.get("LD_LIBRARY_PATH")
            )

    def test_complete_pair_remains_available_after_a_numeric_miss(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pair = [
                root / "warm-01" / name / "complete.tif"
                for name in ("reference", "candidate")
            ]
            diagnostic = root / "diagnostic-01/candidate/complete.tif"
            for path in [*pair, diagnostic]:
                path.parent.mkdir(parents=True)
                path.touch()
            report = {
                "status": "fail",
                "inputs_unchanged": True,
                "gates": {"warm_median": {"status": "fail"}},
            }
            cleanup = _cleanup_outputs(root, report, keep_review_images=True)
            self.assertTrue(cleanup["retained_review_pair"])
            self.assertTrue(all(path.is_file() for path in pair))
            self.assertFalse(diagnostic.exists())

    def test_invalid_job_or_changed_inputs_remove_the_review_outputs(self):
        for report in (
            {
                "status": "fail",
                "inputs_unchanged": True,
                "invalid_reason": "job failed",
            },
            {
                "status": "fail",
                "inputs_unchanged": False,
                "gates": {"warm_median": {"status": "fail"}},
            },
        ):
            with (
                self.subTest(report=report),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                pair = [
                    root / "warm-01" / name / "complete.tif"
                    for name in ("reference", "candidate")
                ]
                for path in pair:
                    path.parent.mkdir(parents=True)
                    path.touch()
                cleanup = _cleanup_outputs(root, report, keep_review_images=True)
                self.assertFalse(cleanup["retained_review_pair"])
                self.assertFalse(any(path.exists() for path in pair))

    def test_only_r50_selects_hash_bound_camera_metadata_launcher(self):
        target = TargetSpec.load(REFERENCE)
        python = Path("/reference/python")
        r50 = _reference_launch(target, python, "R50.hybrid.cpu")
        self.assertEqual(r50["command"], [str(python), str(R50_REFERENCE)])
        self.assertEqual(r50["raw_ingest"]["sha256"], sha256(R50_REFERENCE))
        for profile in ("T50.hybrid.cpu", "D150.hybrid.cpu", "E9.exposure_fusion.gpu"):
            with self.subTest(profile=profile):
                self.assertEqual(
                    _reference_launch(target, python, profile),
                    {"command": target.command("cli", python=python)},
                )

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
