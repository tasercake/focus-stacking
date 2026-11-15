"""Run independent cases, retain evidence, and emit machine-readable reports."""
from dataclasses import asdict
import json
from pathlib import Path
import re
import time
import traceback
from xml.etree import ElementTree as ET

from .context import CaseContext
from .model import CaseResult


def run_cases(cases, *, target, output, environment=None, progress=None, baseline=None):
    if not __debug__:
        raise RuntimeError("Python optimization disables conformance assertions")
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")
    if any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", ident) for ident in ids):
        raise ValueError("case ids must be safe path components")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, case in enumerate(cases, 1):
        context = CaseContext(target, output / "cases" / case.id, environment=environment)
        start = time.monotonic()
        error = ""
        try:
            case.run(context)
            if baseline:
                baseline.check(case.id, context.outputs, suite=case.suite,
                               contract={key: context.notes[key] for key in ("fixtures", "requests") if key in context.notes})
        except Exception:
            error = traceback.format_exc()
            (context.directory / "failure.txt").write_text(error)
        result = CaseResult(case.id, case.suite, "failed" if error else "passed",
                            time.monotonic() - start, error, context.notes)
        results.append(result)
        (context.directory / "result.json").write_text(json.dumps(asdict(result), indent=2, default=str))
        write_reports(results, output, target=target)
        if progress:
            progress(index, len(cases), result)
    write_reports(results, output, target=target)
    return results


def write_reports(results, output, *, target=None):
    counts = {"passed": sum(r.status == "passed" for r in results),
              "failed": sum(r.status == "failed" for r in results)}
    data = {"schema_version": 1, "target": target.name if target else None,
            "status": "failed" if counts["failed"] else "passed",
            "counts": counts, "cases": [asdict(r) for r in results]}
    (output / "report.json").write_text(json.dumps(data, indent=2, default=str))
    root = ET.Element("testsuite", name="stack-conformance", tests=str(len(results)),
                      failures=str(counts["failed"]), time=str(sum(r.duration for r in results)))
    for result in results:
        node = ET.SubElement(root, "testcase", name=result.id, classname=result.suite,
                             time=f"{result.duration:.4f}")
        if result.error:
            ET.SubElement(node, "failure", message=result.error.splitlines()[-1]).text = result.error
    ET.ElementTree(root).write(output / "junit.xml", encoding="unicode", xml_declaration=True)


def record_coverage(output, summary, *, line_minimum=0, branch_minimum=0):
    """Make coverage gate results visible to both CLI and report consumers."""
    output = Path(output)
    passed = summary["line_percent"] >= line_minimum and summary["branch_percent"] >= branch_minimum
    report = json.loads((output / "report.json").read_text())
    report["coverage"] = {key: value for key, value in summary.items() if key != "missing"}
    report["coverage_gate"] = {"line_minimum": line_minimum, "branch_minimum": branch_minimum,
                               "passed": passed}
    report["status"] = "failed" if report["counts"]["failed"] or not passed else "passed"
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if line_minimum or branch_minimum:
        tree = ET.parse(output / "junit.xml")
        root = tree.getroot()
        root.set("tests", str(int(root.get("tests", 0)) + 1))
        node = ET.SubElement(root, "testcase", name="coverage.thresholds", classname="coverage", time="0")
        if not passed:
            root.set("failures", str(int(root.get("failures", 0)) + 1))
            ET.SubElement(node, "failure", message="Coverage threshold failed").text = (
                f"Line coverage {summary['line_percent']:.2f}% requires {line_minimum:.2f}%; "
                f"branch coverage {summary['branch_percent']:.2f}% requires {branch_minimum:.2f}%")
        tree.write(output / "junit.xml", encoding="unicode", xml_declaration=True)
    return passed
