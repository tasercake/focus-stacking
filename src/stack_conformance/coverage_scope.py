"""Audited coverage scope, separate from unchanged raw runtime measurements."""
import ast
from pathlib import Path

from .coverage import source_provenance


def scoped_summary(report, source_root, profile):
    source_root = Path(source_root).resolve()
    if profile.get("schema_version") != 1 or not profile.get("name"):
        raise ValueError("invalid coverage scope schema")
    if profile.get("source_sha256") != source_provenance(source_root)["source_sha256"]:
        raise ValueError("coverage scope source fingerprint changed; review exclusions")
    files = {}
    for name, data in report["files"].items():
        path = Path(name)
        # coverage.py uses paths relative to the run's current directory where possible.
        absolute = path.resolve()
        if absolute.is_relative_to(source_root):
            relative = absolute.relative_to(source_root).as_posix()
        elif not path.is_absolute() and (source_root / path).is_file():
            relative = path.as_posix()
        else:
            raise ValueError(f"coverage scope file outside source inventory: {name}")
        if relative in files:
            raise ValueError(f"duplicate coverage scope source: {relative}")
        files[relative] = data
    if set(files) != set(source_provenance(source_root)["files"]):
        raise ValueError("coverage scope source inventory differs from raw report")
    excluded = {name: set() for name in files}
    ledger = []
    for rule in profile.get("exclusions", []):
        name = rule.get("file")
        if name not in files or rule.get("category") not in ("unused", "unreachable", "dead"):
            raise ValueError("coverage scope requires known file and reviewed exclusion category")
        if not rule.get("reason") or not rule.get("evidence"):
            raise ValueError("coverage scope requires reason and evidence")
        lines = set()
        maximum = len((source_root / name).read_text().splitlines())
        for interval in rule.get("ranges", []):
            if (not isinstance(interval, list) or len(interval) != 2 or
                    any(type(n) is not int for n in interval) or not 1 <= interval[0] <= interval[1] <= maximum):
                raise ValueError("invalid coverage scope source range")
            lines.update(range(interval[0], interval[1] + 1))
        if not lines:
            raise ValueError("coverage scope rule has no source ranges")
        executed = lines & set(files[name]["executed_lines"])
        allowed_definitions = set()
        if rule["category"] == "unused":
            for node in ast.walk(ast.parse((source_root / name).read_text())):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    allowed_definitions.add(node.lineno)
                    for decorator in node.decorator_list:
                        allowed_definitions.update(range(decorator.lineno, decorator.end_lineno + 1))
                if isinstance(node, ast.ClassDef):
                    for statement in node.body:
                        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                            allowed_definitions.update(range(statement.lineno, statement.end_lineno + 1))
        if executed - allowed_definitions:
            raise ValueError(f"coverage scope excludes executed lines in {name}: {sorted(executed)}")
        excluded[name].update(lines)
        ledger.append({**rule, "excluded_executable_lines": sorted(lines & (set(files[name]["missing_lines"]) |
                                                                          set(files[name]["executed_lines"]))),
                       "executed_definition_lines": sorted(executed)})
    covered_lines = total_lines = covered_branches = total_branches = omitted_lines = omitted_branches = 0
    missing = {}
    for name, data in files.items():
        executed, absent = set(data["executed_lines"]), set(data["missing_lines"])
        omitted_lines += len((executed | absent) & excluded[name])
        executed -= excluded[name]
        absent -= excluded[name]
        covered_lines += len(executed)
        total_lines += len(executed | absent)
        good = {tuple(arc) for arc in data.get("executed_branches", [])}
        bad = {tuple(arc) for arc in data.get("missing_branches", [])}
        omit = {arc for arc in good | bad if arc[0] in excluded[name] or arc[1] in excluded[name]}
        if omit & good:
            raise ValueError(f"coverage scope excludes executed branch exits in {name}")
        good -= omit
        bad -= omit
        omitted_branches += len(omit)
        covered_branches += len(good)
        total_branches += len(good | bad)
        if absent or bad:
            missing[name] = {"lines": sorted(absent), "branches": sorted(map(list, bad))}
    return {"name": profile["name"], "source_sha256": profile["source_sha256"],
            "line_covered": covered_lines, "line_total": total_lines,
            "line_percent": 100 * covered_lines / total_lines if total_lines else 100.0,
            "branch_covered": covered_branches, "branch_total": total_branches,
            "branch_percent": 100 * covered_branches / total_branches if total_branches else 100.0,
            "excluded_lines": omitted_lines, "excluded_branches": omitted_branches,
            "exclusions": ledger, "missing": missing}
