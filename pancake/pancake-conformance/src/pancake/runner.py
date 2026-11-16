"""Run independent cases, retain evidence, and emit machine-readable reports."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import time
import traceback
from xml.etree import ElementTree as ET

from .context import CaseContext
from .model import CaseResult


def _validate_cases(cases):
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")
    if any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", ident) for ident in ids):
        raise ValueError("case ids must be safe path components")


def run_cases(cases, *, target, output, environment=None, progress=None, baseline=None, fail_fast=False):
    if not __debug__:
        raise RuntimeError("Python optimization disables conformance assertions")
    _validate_cases(cases)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    try:
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
            context.note("artifact_directory", str(context.directory.resolve()))
            status = "failed" if error else "pending" if context.notes.get("host_verification_pending") else "passed"
            result = CaseResult(case.id, case.suite, status,
                                time.monotonic() - start, error, context.notes,
                                {name: str(Path(path).resolve().relative_to(context.directory.resolve()))
                                 for name, path in context.outputs.items()})
            results.append(result)
            (context.directory / "result.json").write_text(json.dumps(asdict(result), indent=2, default=str))
            write_reports(results, output, target=target, complete=False, selected_count=len(cases), status="running")
            if progress:
                progress(index, len(cases), result)
            if error and fail_fast:
                break
    except BaseException:
        write_reports(results, output, target=target, complete=False, selected_count=len(cases), status="interrupted")
        raise
    write_reports(results, output, target=target, complete=len(results) == len(cases), selected_count=len(cases))
    return results


def verify_guest_parity(result, *, target, artifacts, environment=None):
    """Resolve a provisional GUI result using real host CLI processes."""
    from .validators import assert_pixels_close
    from .vm_results import baseline_artifacts
    case_dir = Path(artifacts).resolve() / "cases" / result.id
    context = CaseContext(target, case_dir / "host-parity", environment=environment)
    start = time.monotonic()
    try:
        requests = result.notes.get("host_parity_requests", [])
        assert requests, "Guest verdict pending without host comparison requests"
        for request in requests:
            files = {"gui": request["gui_output"],
                     **{f"input-{index}": item["path"] for index, item in enumerate(request["inputs"])}}
            evidence = CaseResult(result.id, result.suite, "pending", 0, outputs=files)
            paths = baseline_artifacts(evidence, artifacts)
            assert hashlib.sha256(paths["gui"].read_bytes()).hexdigest() == request["gui_sha256"], "Fetched GUI export checksum differs"
            inputs = []
            for index, item in enumerate(request["inputs"]):
                path = paths[f"input-{index}"]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], "Fetched GUI input checksum differs"
                inputs.append(path)
            cli = context.stack(inputs, **request["options"])
            assert cli.returncode == 0, cli.stderr
            name = request["cli_output_name"]
            assert name not in result.outputs, f"Duplicate host parity output: {name}"
            result.outputs[name] = cli.output.resolve().relative_to(case_dir).as_posix()
            result.notes[request["note"]] = assert_pixels_close(paths["gui"], cli.output,
                mean_limit=request["mean_limit"], max_limit=request["max_limit"])
        result.status = "passed"
    except Exception:
        result.status, result.error = "failed", traceback.format_exc()
        (context.directory / "failure.txt").write_text(result.error)
    finally:
        result.duration += time.monotonic() - start
        result.notes.setdefault("requests", []).extend(context.notes.get("requests", []))
        result.notes["host_verification_pending"] = False
        result.notes["cli_execution_environment"] = "host"
        (case_dir / "host-result.json").write_text(json.dumps(asdict(result), indent=2, default=str))


def validate_execution_provenance(expected, actual):
    """Bind guest verdicts to the same frozen suite, descriptor and target."""
    for key in ("suite_source_sha256", "target_descriptor_sha256", "target_commit"):
        if expected.get(key) and actual.get(key) != expected[key]:
            raise ValueError(f"Guest {key} differs from host run provenance")


def run_vm_cases(cases, *, target, output, workspace, environment=None, progress=None,
                 baseline=None, coverage=None, visible=False, persist=False, fail_fast=False,
                 provenance=None, vm_factory=None, cli_command=None, gui_command=None, project=None):
    """Run only interface cases in one configured VM; never fall back to the host."""
    from .coverage import validate_source_provenance
    from .vm_results import baseline_artifacts, merge_case_results
    _validate_cases(cases)
    if not any(case.suite == "interface" for case in cases):
        return run_cases(cases, target=target, output=output, environment=environment,
                         progress=progress, baseline=baseline, fail_fast=fail_fast)
    if vm_factory is None:
        from .gui_vm import TartGuiVM
        vm_factory = TartGuiVM
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    indices = [index for index, case in enumerate(cases) if case.suite == "interface"]
    first, last = indices[0], indices[-1]
    if indices != list(range(first, last + 1)):
        raise ValueError("interface cases must form one execution group")
    project_options = {"project": project} if project is not None else {}
    vm = vm_factory(target.gui_vm, Path(workspace), output / "vm-transport", visible=visible, persist=persist,
                    **project_options)
    results = []
    complete = False
    def checkpoint(status="running"):
        write_reports(results, output, target=target, complete=False,
                      selected_count=len(cases), status=status)
    def notify(result):
        results.append(result)
        checkpoint()
        if progress:
            progress(len(results), len(cases), result)
    def host_batch(batch, directory):
        return run_cases(batch, target=target, output=output / directory, environment=environment,
                         progress=lambda index, total, result: notify(result), baseline=baseline,
                         fail_fast=fail_fast)
    try:
        checkpoint()
        vm.prepare()  # Preflight before any expensive host work or target launch.
        host_batch(cases[:first], "host-before")
        if fail_fast and any(result.status == "failed" for result in results):
            return results
        supported = []
        unsupported = {}
        for case in cases[first:last + 1]:
            missing = set(case.required_capabilities) - {"cpu", "native_gui"}
            if missing:
                reason = "macOS VM lacks capability: " + ", ".join(sorted(missing))
                unsupported[case.id] = CaseResult(case.id, case.suite, "unsupported", 0,
                                                   execution_environment="vm", reason=reason)
                if baseline:
                    baseline.note_unsupported(case.id, reason, suite=case.suite)
            else:
                supported.append(case)
        guest_results = []
        if supported:
            overrides = {key: value for key, value in (("cli_command", cli_command), ("gui_command", gui_command)) if value is not None}
            remote = vm.run_cases([case.id for case in supported], target_path=target.descriptor,
                                  coverage=coverage is not None, fail_fast=fail_fast, **overrides)
            if provenance:
                guest_provenance = json.loads((Path(remote.artifacts) / "provenance.json").read_text())
                validate_execution_provenance(provenance, guest_provenance)
                provenance["guest"] = guest_provenance
                (output / "provenance.json").write_text(json.dumps(provenance, indent=2))
            if target.adapter == "chimpstackr-python":
                validate_source_provenance(target.root / "src", remote.source_provenance,
                                           (provenance or {}).get("target_commit"))
            actual_ids = [record["id"] for record in remote.report["cases"]]
            expected_ids = [case.id for case in supported]
            if not remote.report.get("complete", True):
                if not fail_fast or not remote.returncode or actual_ids != expected_ids[:len(actual_ids)]:
                    raise RuntimeError("Guest run incomplete; see VM artifacts")
                expected_ids = actual_ids
            artifact_map = {remote.guest_output: str(remote.artifacts)} if getattr(remote, "guest_output", None) else {}
            guest_results = merge_case_results([], remote.report["cases"], expected_ids,
                artifact_path_map=artifact_map,
                source_provenance=remote.source_provenance)
            for result in guest_results:
                result.notes["artifact_directory"] = str((Path(remote.artifacts) / "cases" / result.id).resolve())
            if remote.returncode not in (0, 1):
                raise RuntimeError(f"Guest runner infrastructure error (exit {remote.returncode}); inspect {remote.artifacts}")
            if remote.returncode and not any(result.status == "failed" for result in guest_results):
                raise RuntimeError(f"Guest runner exited {remote.returncode}; no successful conformance verdict")
            if coverage:
                data_paths = [path for path in (Path(remote.artifacts) / "coverage").glob(".coverage*")
                              if path.name == ".coverage" or path.name.startswith(".coverage.")]
                coverage.import_data(data_paths, source_root=remote.guest_source_root,
                                     provenance=remote.source_provenance,
                                     expected_target_commit=(provenance or {}).get("target_commit"))
            for result in guest_results:
                if result.status == "pending":
                    verify_guest_parity(result, target=target, artifacts=remote.artifacts, environment=environment)
                if fail_fast and result.status == "failed":
                    break
            if baseline:
                for result in guest_results:
                    if result.status != "passed":
                        continue
                    try:
                        baseline.check(result.id, baseline_artifacts(result, remote.artifacts), suite=result.suite,
                                       contract={key: result.notes[key] for key in ("fixtures", "requests") if key in result.notes})
                    except Exception:
                        result.status, result.error = "failed", traceback.format_exc()
        by_id = {result.id: result for result in guest_results}
        for case in cases[first:last + 1]:
            result = unsupported.get(case.id) or by_id.get(case.id)
            if result is None:
                break
            notify(result)
            if fail_fast and result.status == "failed":
                break
        if len(guest_results) < len(supported) or (fail_fast and any(result.status == "failed" for result in results)):
            return results
        host_batch(cases[last + 1:], "host-after")
        complete = len(results) == len(cases)
        return results
    except BaseException:
        checkpoint("interrupted")
        raise
    finally:
        try:
            vm.close()
        finally:
            write_reports(results, output, target=target, complete=complete, selected_count=len(cases))


def write_reports(results, output, *, target=None, complete=True, selected_count=None, status=None):
    from .vm_results import result_counts, result_status
    counts = result_counts(results)
    data = {"schema_version": 1, "target": target.name if target else None,
            "status": status or result_status(results, complete=complete),
            "complete": complete, "selected_count": selected_count if selected_count is not None else len(results),
            "completed_count": len(results),
            "counts": counts, "cases": [asdict(r) for r in results]}
    (output / "report.json").write_text(json.dumps(data, indent=2, default=str))
    root = ET.Element("testsuite", name="pancake", tests=str(len(results)),
                      failures=str(counts["failed"]), skipped=str(counts["unsupported"] + counts.get("pending", 0)),
                      time=str(sum(r.duration for r in results)))
    for result in results:
        node = ET.SubElement(root, "testcase", name=result.id, classname=result.suite,
                             time=f"{result.duration:.4f}")
        if result.status == "failed":
            error = result.error or "Conformance case failed"
            ET.SubElement(node, "failure", message=error.splitlines()[-1]).text = error
        if result.status == "unsupported":
            ET.SubElement(node, "skipped", message=result.reason or "Guest capability unavailable")
        elif result.status == "pending":
            ET.SubElement(node, "skipped", message="Native phase complete; host CLI comparison pending")
    if not complete and status != "running":
        root.set("errors", "1")
        root.set("tests", str(len(results) + 1))
        node = ET.SubElement(root, "testcase", name="harness.incomplete", classname="harness", time="0")
        ET.SubElement(node, "error", message=f"Run stopped after {len(results)} of {selected_count} selected cases")
    ET.ElementTree(root).write(output / "junit.xml", encoding="unicode", xml_declaration=True)


def record_coverage(output, summary, *, line_minimum=0, branch_minimum=0):
    """Make coverage gate results visible to both CLI and report consumers."""
    output = Path(output)
    basis = summary.get("scope", summary)
    passed = basis["line_percent"] >= line_minimum and basis["branch_percent"] >= branch_minimum
    report = json.loads((output / "report.json").read_text())
    report["coverage"] = {key: value for key, value in summary.items() if key != "missing"}
    report["coverage_gate"] = {"line_minimum": line_minimum, "branch_minimum": branch_minimum,
                               "passed": passed, "basis": basis.get("name", "raw")}
    report["status"] = ("failed" if report["counts"]["failed"] or not passed else
                        "incomplete" if not report.get("complete", True) else
                        "pending-host-verification" if report["counts"].get("pending") else
                        "partial" if report["counts"].get("unsupported") else "passed")
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if line_minimum or branch_minimum:
        tree = ET.parse(output / "junit.xml")
        root = tree.getroot()
        root.set("tests", str(int(root.get("tests", 0)) + 1))
        node = ET.SubElement(root, "testcase", name="coverage.thresholds", classname="coverage", time="0")
        if not passed:
            root.set("failures", str(int(root.get("failures", 0)) + 1))
            ET.SubElement(node, "failure", message="Coverage threshold failed").text = (
                f"Line coverage {basis['line_percent']:.2f}% requires {line_minimum:.2f}%; "
                f"branch coverage {basis['branch_percent']:.2f}% requires {branch_minimum:.2f}%")
        tree.write(output / "junit.xml", encoding="unicode", xml_declaration=True)
    return passed
