"""Exercise the independent visible-pixel observer on real XWD bytes."""

import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from framebuffer import Patch, XwdScreen, observe_transition
from protocol import merge_latency_samples, verify_frames


def make_xwd(path):
    # X.Org XWDFile.h layout. Two pixels and four bytes of padding per row.
    header = (
        104,
        7,
        2,
        24,
        2,
        2,
        0,
        0,
        32,
        0,
        32,
        32,
        12,
        4,
        0xFF0000,
        0x00FF00,
        0x0000FF,
        8,
        0,
        0,
        2,
        2,
        0,
        0,
        0,
    )
    path.write_bytes(
        struct.pack(">25I", *header)
        + b"Xv\0\0"
        + struct.pack("<6I", 0x334455, 0x667788, 0, 0x112233, 0x445566, 0)
    )


class ScreenContracts(unittest.TestCase):
    def test_truecolor_and_row_stride(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "screen.xwd"
            make_xwd(path)
            with XwdScreen(path) as screen:
                np.testing.assert_array_equal(
                    screen.rgb(0, 1, 2, 1), [[[17, 34, 51], [68, 85, 102]]]
                )
                with self.assertRaisesRegex(ValueError, "outside the screen"):
                    screen.rgb(1, 0, 2, 1)

    def test_before_and_after_frame_must_be_distinguishable_before_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "screen.xwd"
            make_xwd(path)
            patch = Patch(0, 1, np.array([[[17, 34, 51]]], dtype=np.uint8), 0)
            with XwdScreen(path) as screen:

                def invalid_dispatch():
                    self.fail("ambiguous oracle must fail before dispatch")

                with self.assertRaisesRegex(ValueError, "already displayed"):
                    observe_transition(
                        screen, invalid_dispatch, [patch], [patch], timeout=1
                    )


class CaptureEvidenceContracts(unittest.TestCase):
    def test_native_completion_requires_matching_actual_build(self):
        receipt = {
            "status": "captured",
            "inputs_unchanged": True,
            "candidate": {
                "commit": "one",
                "binary_sha256": "binary",
                "descriptor_sha256": "descriptor",
                "lock_sha256": "lock",
            },
            "performance_targets_sha256": "targets",
            "workload": "T50",
            "viewer": [],
            "lifecycle": [],
        }
        changed = dict(receipt, candidate=dict(receipt["candidate"], commit="two"))
        with self.assertRaisesRegex(ValueError, "build provenance"):
            merge_latency_samples([receipt, changed])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            merge_latency_samples([dict(receipt, status="fail")])

    def test_lifecycle_fixture_uses_unique_paths_to_shared_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "frame_00.png").write_bytes(b"unique fixture image")
            (root / "frame_01.png").hardlink_to(root / "frame_00.png")
            expected = hashlib.sha256(b"unique fixture image").hexdigest()
            records = [
                {"path": name, "sha256": expected, "bytes": 20}
                for name in ("frame_00.png", "frame_01.png")
            ]
            with self.assertRaisesRegex(ValueError, "distinct"):
                verify_frames(root, records, 2)
            self.assertEqual(
                len(verify_frames(root, records, 2, distinct_content=False)), 2
            )
