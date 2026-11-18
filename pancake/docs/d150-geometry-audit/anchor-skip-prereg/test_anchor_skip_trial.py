"""Generated red/green controls for the preregistered D150 diagnostic."""

from pathlib import Path
import runpy
import unittest

import cv2
import numpy as np

from anchor_skip_trial import PLAN, load_plan, proposal_screen


AUDIT = Path(__file__).resolve().parent.parent
BILATERAL = runpy.run_path(str(AUDIT / "motion-admission/bilateral.py.txt"))
TRACKER = runpy.run_path(str(AUDIT / "local-track.py.txt"))


def rendered(dx, dy):
    rng = np.random.default_rng(72)
    codes = rng.integers(24, 229, size=(541, 760), dtype=np.uint8)
    before = cv2.GaussianBlur(codes, (5, 5), 1.1)
    motion = BILATERAL["homogeneous"]([[1.000_22, 0, dx], [0, 1.000_22, dy]])
    after = cv2.warpAffine(
        before, motion[:2], before.shape[::-1], flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )
    return before, cv2.convertScaleAbs(after, alpha=0.97, beta=4), motion


class TrialWitnesses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1)
        cv2.ocl.setUseOpenCL(False)
        cls.plan = load_plan(PLAN)

    def screen(self, before, after, proposals):
        evidence = BILATERAL["bilateral"](TRACKER, before, after, proposals)
        return evidence, proposal_screen(
            self.plan, before.shape, proposals, evidence, TRACKER, BILATERAL,
        )

    def test_manifest_is_exact_and_closed(self):
        rows = self.plan["minimal_probe"]["records"]
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(row["bytes"] for row in rows), 3_582_818)
        self.assertEqual(len(self.plan["comparison_roster"]), 12)

    def test_known_two_axis_motion_survives_native_holdouts(self):
        before, after, known = rendered(3.43, -2.63)
        _, measured = self.screen(before, after, {"direct": known, "identity_baseline": np.eye(3)})
        self.assertEqual(measured["status"], "native_supported_proposal")
        self.assertEqual(measured["winner"], "direct")
        self.assertGreaterEqual(min(measured["witness_counts"]), 4)

    def test_short_margin_that_old_preference_admitted_abstains(self):
        before, after, known = rendered(3.43, -2.63)
        rival = known.copy()
        rival[0, 2] += 0.75
        proposals = {"direct": known, "inverse_reverse": rival, "identity_baseline": np.eye(3)}
        evidence, measured = self.screen(before, after, proposals)
        self.assertEqual(BILATERAL["preference"](evidence, "inverse_reverse", "direct", 0.20), "alternative")
        self.assertEqual(measured["status"], "unresolved")
        self.assertIsNone(measured["winner"])

    def test_aperture_and_identity_only_remain_unresolved(self):
        rows = np.random.default_rng(72).integers(36, 213, size=(541, 1), dtype=np.uint8)
        aperture = cv2.GaussianBlur(np.repeat(rows, 760, axis=1), (5, 5), 1.1)
        ambiguous = BILATERAL["homogeneous"]([[1, 0, 4], [0, 1, 0]])
        _, measured = self.screen(aperture, aperture, {"direct": ambiguous, "identity_baseline": np.eye(3)})
        self.assertEqual(measured["status"], "unresolved")
        before, after, _ = rendered(3.43, -2.63)
        _, identity = self.screen(before, after, {"identity_baseline": np.eye(3)})
        self.assertEqual(identity["status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
