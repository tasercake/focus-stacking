"""Identity and failure handling for the real desktop coverage collector."""

from copy import deepcopy
import json
from pathlib import Path
import signal
import tempfile
import unittest

from scripts.gui_coverage import check_report, collect_profiles, compare_mapping


class GuiCoverageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.raw = self.output / "raw"
        self.raw.mkdir()
        self.case = "interface.about"
        self.calls = self.output / "cases" / self.case
        self.build_id = "0" * 40

    def record(self, pid, status="clean", returncode=0, forced=False):
        call = self.calls / f"call-{pid:02d}"
        call.mkdir(parents=True)
        (call / "shutdown.json").write_text(json.dumps({
            "pid": pid, "status": status, "returncode": returncode, "forced": forced,
        }))
        return call

    def profile(self, pid, content=b"real counters", build_id=None):
        profile = self.raw / f"pancake-{pid}-{build_id or self.build_id}.profraw"
        profile.write_bytes(content)
        return profile

    def test_clean_and_runner_forced_cases_keep_exact_process_identity(self):
        self.record(22)
        self.record(23, "forced", -signal.SIGTERM, True)
        self.profile(22)
        self.profile(23)
        evidence = collect_profiles(self.output, self.raw, [self.case], self.build_id)
        self.assertEqual([row["shutdown"]["status"] for row in evidence], ["clean", "forced"])
        self.assertEqual([row["shutdown"]["pid"] for row in evidence], [22, 23])

    def test_missing_or_empty_counters_are_failures(self):
        self.record(22)
        with self.assertRaisesRegex(ValueError, "missing or empty"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)
        self.profile(22, b"")
        with self.assertRaisesRegex(ValueError, "missing or empty"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)

    def test_wrong_build_id_or_unattributed_profile_is_rejected(self):
        self.record(22)
        wrong = self.profile(22, build_id="a" * 40)
        with self.assertRaisesRegex(ValueError, "missing or empty"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)
        wrong.unlink()
        self.profile(22)
        self.profile(23)
        with self.assertRaisesRegex(ValueError, "unattributed"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)

    def test_target_failure_never_supplies_counters(self):
        self.record(22, "failed", 10, False)
        self.profile(22)
        with self.assertRaisesRegex(ValueError, "failed shutdown"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)

    def test_gpu_job_is_rejected_in_cpu_scope(self):
        call = self.record(22)
        self.profile(22)
        (call / "events.jsonl").write_text('{"event":"stack_complete","actual_backend":"gpu"}\n')
        with self.assertRaisesRegex(ValueError, "non-CPU backend"):
            collect_profiles(self.output, self.raw, [self.case], self.build_id)

    def test_report_must_be_complete_and_exactly_pass_every_selected_case(self):
        report = {
            "complete": True, "completed_count": 1, "selected_count": 1,
            "cases": [{"id": self.case, "status": "passed"}],
        }
        check_report(report, [self.case])
        for status in ("failed", "unsupported", "pending"):
            report["cases"][0]["status"] = status
            with self.assertRaisesRegex(ValueError, "case did not pass"):
                check_report(report, [self.case])
        report["cases"][0]["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "selection"):
            check_report(report, ["interface.recovery.close-unsaved"])
        report["complete"] = False
        with self.assertRaisesRegex(ValueError, "incomplete"):
            check_report(report, [self.case])


class MappingIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.counts = {
            kind: {"count": 2, "covered": 1}
            for kind in ("lines", "functions", "regions", "branches")
        }
        self.standard = {"data": [{
            "totals": self.counts,
            "files": [{"filename": "/delivery.rs", "summary": self.counts}],
            "functions": [{"name": "function", "filenames": ["/delivery.rs"],
                           "regions": [[1, 1, 2, 2, 1, 0, 0, 0]], "branches": []}],
        }]}

    def test_adds_coverage_with_the_same_mapping(self):
        merged = deepcopy(self.standard)
        merged["data"][0]["totals"]["lines"]["covered"] = 2
        merged["data"][0]["functions"][0]["regions"][0][4] = 2
        compare_mapping(self.standard, merged)

    def test_adding_a_native_object_preserves_source_and_all_standard_entries(self):
        control = deepcopy(self.standard)
        function = deepcopy(control["data"][0]["functions"][0])
        function["name"] = "same_source_other_instantiation"
        function["regions"][0][4] = 0
        control["data"][0]["functions"].append(function)
        compare_mapping(self.standard, control, adding_mapping=True)

        function["regions"][0][0] = 3
        with self.assertRaisesRegex(ValueError, "source mapping"):
            compare_mapping(self.standard, control, adding_mapping=True)

    def test_adding_an_unused_native_object_cannot_add_baseline_counts(self):
        control = deepcopy(self.standard)
        control["data"][0]["totals"]["lines"]["covered"] = 2
        with self.assertRaisesRegex(ValueError, "denominator or control counts"):
            compare_mapping(self.standard, control, adding_mapping=True)

    def test_rejects_different_source_mapping_with_the_same_totals(self):
        merged = deepcopy(self.standard)
        merged["data"][0]["functions"][0]["regions"][0][0] = 3
        with self.assertRaisesRegex(ValueError, "source mapping"):
            compare_mapping(self.standard, merged)

    def test_rejects_unreported_loss_even_with_unchanged_totals(self):
        merged = deepcopy(self.standard)
        merged["data"][0]["functions"][0]["regions"][0][4] = 0
        with self.assertRaisesRegex(ValueError, "covered region"):
            compare_mapping(self.standard, merged)


if __name__ == "__main__":
    unittest.main()
