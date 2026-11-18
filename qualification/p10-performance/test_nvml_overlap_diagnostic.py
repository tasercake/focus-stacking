"""Synthetic contracts for E9 NVML overlap evidence without a device."""

import fcntl
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import tifffile
from nvml_overlap_diagnostic import (
    DEVICE,
    PCI,
    PairDevice,
    PairLane,
    capture_pair,
    classify_arms,
    describe_arm,
    due_slot,
    main,
    measure_arm,
    run_arm,
)
from protocol import verify_output
from resources import _DeviceProcess

MS = 1_000_000


def pair(lane, slot, begin, compute_end, end, *, value=12, issues=()):
    return {
        "lane": lane,
        "slot": slot,
        "scheduled_ns": begin * MS,
        "calls": [
            {
                "kind": "compute",
                "started_ns": begin * MS,
                "finished_ns": compute_end * MS,
            },
            {
                "kind": "graphics",
                "started_ns": compute_end * MS,
                "finished_ns": end * MS,
            },
        ],
        "finished_ns": end * MS,
        "bytes": value,
        "issues": list(issues),
    }


class CaptureContracts(unittest.TestCase):
    def test_own_process_records_are_deduplicated_after_both_timed_calls(self):
        pending = {
            "compute": [(11, 100), (99, 500)],
            "graphics": [(11, 120), (12, 25)],
        }
        ids = {11: (7, 1), 12: (7, 2), 99: (99, 3)}
        clock = iter(range(1, 12)).__next__
        row = capture_pair(1, 4, 0, 7, pending.__getitem__, ids.get, clock)
        self.assertEqual(row["bytes"], 145)
        self.assertEqual(row["attributed_pids"], [11, 12])
        self.assertEqual(
            [part["kind"] for part in row["calls"]], ["compute", "graphics"]
        )
        self.assertGreater(row["finished_ns"], row["calls"][1]["finished_ns"])
        self.assertEqual(row["calls"][0]["records"][0]["identity"], [7, 1])
        self.assertFalse(row["issues"])

    def test_lifetime_reuse_and_unavailable_bytes_invalidate_without_partial_filling(
        self,
    ):
        pending = {"compute": [(11, 12)], "graphics": [(11, 30), (12, None)]}
        ids = iter([(7, 1), (7, 3), (7, 2)])
        row = capture_pair(
            0, 0, 0, 7, pending.__getitem__, lambda _: next(ids), lambda: 1
        )
        self.assertIsNone(row["bytes"])
        self.assertEqual(row["issues"], ["pid-reuse:11", "unavailable:12"])

    def test_driver_error_is_retained_and_both_calls_attempted(self):
        def read(kind):
            if kind == "compute":
                raise ValueError("driver refused")
            return [(11, 120)]

        row = capture_pair(0, 0, 0, 7, read, lambda _: (7, 1), lambda: 1)
        self.assertIsNone(row["bytes"])
        self.assertEqual(row["calls"][0]["error"], "driver refused")
        self.assertEqual(row["calls"][1]["records"][0]["pid"], 11)

    def test_absolute_slots_skip_delays_instead_of_queueing_catchup(self):
        self.assertIsNone(due_slot(100 * MS, 101 * MS, 1))
        self.assertEqual(due_slot(100 * MS, 110 * MS, 1), (1, 108 * MS))
        self.assertEqual(due_slot(100 * MS, 131 * MS, 1), (3, 124 * MS))

    def test_only_free_lane_accepts_dispatch_and_blocked_lane_does_not_stop_peer(self):
        entered = threading.Event()
        release = threading.Event()

        def slow(*_):
            entered.set()
            if not release.wait(2):
                raise RuntimeError("synthetic gate did not release")
            return {"sample": "slow"}

        first, second = PairLane(slow), PairLane(lambda *_: {"sample": "fast"})
        try:
            self.assertTrue(first.ready.wait(2) and second.ready.wait(2))
            self.assertTrue(first.submit((0,)))
            self.assertTrue(entered.wait(2))
            self.assertFalse(first.submit((1,)))
            self.assertTrue(second.submit((1,)))
            self.assertTrue(second.ready.wait(2))
            self.assertEqual(second.receipts, [{"sample": "fast"}])
            self.assertFalse(first.ready.is_set())
        finally:
            release.set()
            for lane in (first, second):
                lane.ready.wait(2)
                lane.close()
                lane.thread.join(2)
        self.assertEqual(first.receipts, [{"sample": "slow"}])

    def test_buffers_are_distinct_and_copied_before_reuse(self):
        provider = SimpleNamespace(
            lib=object(), handle=object(), rows=(_DeviceProcess * 2)()
        )
        first, second = PairDevice(provider), PairDevice(provider)
        first.rows[0].pid = 11
        self.assertIs(first.handle, second.handle)
        self.assertEqual(second.rows[0].pid, 0)
        self.assertEqual(provider.rows[0].pid, 0)
        first.lib = SimpleNamespace(nvmlDeviceGetComputeRunningProcesses_v3=object())
        with patch.object(first, "_query", return_value=first.rows):
            rows = first.read("compute")
        first.rows[0].pid = 99
        self.assertEqual(rows[0][0], 11)


class IntervalContracts(unittest.TestCase):
    def test_fresh_bypass_strictly_inside_a_peer_stall_and_the_job(self):
        rows = [pair(0, 1, 8, 39, 40), pair(1, 2, 16, 17, 18)]
        result = describe_arm(rows, 0, 35 * MS)
        self.assertEqual(result["bypass_slots"], [[1, 2]])
        self.assertEqual(result["after_exit_slots"], [1])
        self.assertEqual(result["completion_gap_ns"], 18 * MS)
        self.assertEqual(result["conservative_window_gap_ns"], 19 * MS)

    def test_slow_stale_completion_does_not_bridge_or_supply_a_peak(self):
        rows = [
            pair(0, 0, 7, 7, 8),
            pair(1, 1, 10, 41, 42, value=999),
            pair(0, 2, 23, 23, 24),
        ]
        result = describe_arm(rows, 0, 58 * MS)
        self.assertEqual(result["completion_gap_ns"], 34 * MS)
        self.assertEqual(result["maximum_bounded_pair_bytes"], 12)
        self.assertEqual(result["raw_complete_in_job_maximum_bytes"], 999)

    def test_without_reproduced_stalls_the_outcome_is_inconclusive(self):
        empty = describe_arm([], 0, 35 * MS)
        shared = describe_arm([pair(0, 1, 8, 39, 40)], 0, 35 * MS)
        bypass = describe_arm(
            [pair(0, 1, 8, 39, 40), pair(1, 2, 16, 17, 18)], 0, 35 * MS
        )
        self.assertEqual(classify_arms(empty, bypass), "inconclusive-no-serial-stall")
        self.assertEqual(classify_arms(shared, empty), "inconclusive-no-overlap-stall")
        self.assertEqual(
            classify_arms(shared, shared), "no-independent-return-observed"
        )
        self.assertEqual(
            classify_arms(shared, bypass), "independent-complete-return-observed"
        )

    def test_preflight_does_not_open_the_device_or_acquire_gpu_lease(self):
        with (
            patch(
                "nvml_overlap_diagnostic.prepare", return_value={"inputs": ["verified"]}
            ) as verify,
            patch("nvml_overlap_diagnostic.NvidiaMemory") as device,
            patch("nvml_overlap_diagnostic._campaign_lock") as lock,
            patch("builtins.print") as output,
        ):
            self.assertEqual(
                main(
                    [
                        "--input-root",
                        "/sources",
                        "--vulkan-cli",
                        "/vulkan",
                        "--cuda-cli",
                        "/cuda",
                    ]
                ),
                0,
            )
            verify.assert_called_once()
            output.assert_called_once()
            device.assert_not_called()
            lock.assert_not_called()

    def test_real_wait_and_drain_with_a_fake_nvml_device(self):
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            marker = directory / "pid"

            def fake_read(_kind):
                try:
                    return [(int(marker.read_text()), 12345)]
                except (FileNotFoundError, ValueError):
                    return []

            code = "import os, time; from pathlib import Path; Path('pid').write_text(str(os.getpid())); time.sleep(0.12)"
            with patch(
                "nvml_overlap_diagnostic.PairDevice",
                return_value=SimpleNamespace(read=fake_read),
            ):
                result = measure_arm(
                    [sys.executable, "-c", code],
                    os.environ.copy(),
                    directory,
                    object(),
                    2,
                )
            self.assertTrue(result["drained"])
            self.assertEqual(result["returncode"], 0)
            self.assertFalse(result["deadline_hit"])
            self.assertGreater(result["exit_observed_ns"], result["launch_ns"])
            self.assertEqual(result["initial_job_identity"][0], result["job_pid"])
            self.assertEqual(
                result["analysis"]["raw_complete_in_job_maximum_bytes"], 12345
            )

    def test_job_watchdog_reaps_its_synthetic_child_and_drains_lanes(self):
        with (
            tempfile.TemporaryDirectory() as scratch,
            patch(
                "nvml_overlap_diagnostic.PairDevice",
                return_value=SimpleNamespace(read=lambda _: []),
            ),
            patch("nvml_overlap_diagnostic.JOB_LIMIT", 0.05),
        ):
            result = measure_arm(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                os.environ.copy(),
                Path(scratch),
                object(),
                1,
            )
        self.assertTrue(result["deadline_hit"] and result["drained"])
        self.assertEqual(result["returncode"], -9)
        self.assertNotIn("unexpected_session_members_after_exit", result)

    def test_arm_requires_independent_decoded_pixels_and_exact_physical_identity(self):
        pixels = np.arange(5 * 4 * 3, dtype=np.uint16).reshape((5, 4, 3)) * 1000
        observed_pci = PCI

        def measured(_argv, _env, directory, _provider, _workers):
            tifffile.imwrite(directory / "complete.tif", pixels, photometric="rgb")
            event = {
                "event": "stack_complete",
                "completed": True,
                "actual_backend": "gpu",
                "runtime": "cuda",
                "device": DEVICE,
                "device_pci_address": observed_pci,
                "physical_gpu": True,
                "fallback_reason": None,
            }
            (directory / "events.jsonl").write_text(json.dumps(event) + "\n")
            return {
                "drained": True,
                "returncode": 0,
                "deadline_hit": False,
                "analysis": {"raw_complete_in_job_maximum_bytes": 150},
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            correct = root / "expected.tif"
            tifffile.imwrite(correct, pixels, photometric="rgb")
            archived = verify_output(correct, [339, 512, 3])
            prepared = {
                "frames": ["synthetic"],
                "plans": {
                    "cuda": {
                        "binary": "/unused",
                        "archived_environment": {},
                        "argv_suffix": [],
                        "archived_output": archived,
                    }
                },
            }
            with patch("nvml_overlap_diagnostic.measure_arm", side_effect=measured):
                accepted = run_arm("cuda", 2, prepared, root / "accepted", object())
                self.assertTrue(accepted["diagnostic_image_and_device_verified"])
                archived["pixel_sha256"] = "unmatched"
                rejected = run_arm("cuda", 2, prepared, root / "rejected", object())
                self.assertFalse(rejected["diagnostic_image_and_device_verified"])
                self.assertIn("pixel_sha256", rejected["failure"])
                archived.update(verify_output(correct, [339, 512, 3]))
                observed_pci = "0000:02:00.0"
                mismatched = run_arm(
                    "cuda", 2, prepared, root / "wrong-device", object()
                )
                self.assertFalse(mismatched["diagnostic_image_and_device_verified"])
                self.assertIn("PCI address", mismatched["failure"])

    def test_undrained_subprocess_keeps_fatal_receipt_without_explicit_device_close(
        self,
    ):
        code = """
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import nvml_overlap_diagnostic as probe

directory = Path(sys.argv[1])
@contextmanager
def fake_lock():
    with (directory / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
        (directory / "explicit-unlock").touch()

probe._campaign_lock = fake_lock
probe._gpu_state = lambda _: {"name": probe.DEVICE, "pci.bus_id": probe.PCI, "driver_version": probe.DRIVER}
probe.NvidiaMemory = lambda _: SimpleNamespace(close=lambda: (directory / "explicit-close").touch())
probe.run_arm = lambda runtime, workers, prepared, arm, provider: {"drained": False, "scratch": str(arm)}
prepared = {"plans": {"cuda": {"archived_affinity": sorted(os.sched_getaffinity(0))}}}
raise SystemExit(probe.execute(prepared, directory / "receipt.json"))
"""
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            completed = subprocess.run(
                [sys.executable, "-c", code, str(directory)],
                cwd=Path(__file__).parent,
                check=False,
                timeout=5,
            )
            self.assertEqual(completed.returncode, 2)
            result = json.loads((directory / "receipt.json").read_text())
            self.assertEqual(result["status"], "aborted-native-call-still-inflight")
            self.assertFalse(result["lease_released"])
            self.assertFalse((directory / "explicit-close").exists())
            self.assertFalse((directory / "explicit-unlock").exists())
            with (directory / "lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Fatal exit intentionally preserves only its task-owned arm directory.
            arm = Path(result["arms"]["cuda"]["serial"]["scratch"])
            arm.rmdir()
