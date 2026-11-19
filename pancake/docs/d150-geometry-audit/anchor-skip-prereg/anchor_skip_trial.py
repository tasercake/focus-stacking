"""Prepare and score only the preregistered D150 diagnostic. No download is launched here."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PLAN = HERE / "plan.json"
PLAN_SHA256 = "23d8cbd8a6f38cac481516180e746b0d9486368409128dae0ba8c056fb3e65b4"
MANIFEST = ROOT / "pancake-conformance/src/pancake_conformance/adapters/pancake/performance-corpus.json"


def read_json(path):
    return json.loads(path.read_bytes())


def sha256(path):
    with path.open("rb") as content:
        return hashlib.file_digest(content, "sha256").hexdigest()


def require(condition, error):
    if not condition:
        raise ValueError(error)


def load_plan(path):
    require(sha256(path) == PLAN_SHA256, "trial plan differs from preregistration")
    plan = read_json(path)
    require(sha256(MANIFEST) == plan["minimal_probe"]["frozen_manifest_sha256"], "frozen corpus manifest differs")
    require(sha256(ROOT / "pancake/Cargo.lock") == plan["cargo_lock_sha256"], "Cargo lock differs")
    require(sha256(ROOT / "pancake/docs/performance-targets.json") == plan["performance_targets_sha256"], "performance targets differ")
    for name, expected in plan["pinned_tools"].items():
        require(sha256(ROOT / name) == expected, f"pinned diagnostic tool differs: {name}")
    return plan


def owned_stage(plan):
    stage = ROOT / plan["acquisition"]["scratch_subdirectory"]
    require(stage.resolve() == stage, "owned stage must not traverse a symlink")
    return stage


def replace_once(source, before, after):
    require(source.count(before) == 1, "unexpected structure of the pinned tool")
    return source.replace(before, after, 1)


def prepare(plan):
    stage = owned_stage(plan)
    acquire = (HERE.parent / "motion-admission/acquire-probe.py.txt").read_text()
    acquire = replace_once(acquire, "extract only the nine audit originals", "extract the eleven preregistered originals")
    acquire = replace_once(acquire, 'plan = json.loads(args.audit.read_bytes())["minimal_probe"]',
                           f'''plan_bytes = args.audit.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != "{PLAN_SHA256}":
        raise ValueError("trial plan differs from preregistration")
    if args.output.resolve() != Path({str(stage / 'materialized')!r}):
        raise ValueError("unexpected output path for this owned trial")
    plan = json.loads(plan_bytes)["minimal_probe"]''')
    acquire = replace_once(acquire, 'len({row["frame_index"] for row in records}) == 9',
                           'len({row["frame_index"] for row in records}) == 11')
    probe = (HERE.parent / "motion-admission/probe.rs.txt").read_text()
    beginning = probe.index("/// Process the anchor and both four-frame windows")
    ending = probe.index("/// Decode and thumbnail")
    probe = probe[:beginning] + (HERE / "product-main.rs.txt").read_text() + probe[ending:]
    stage.mkdir(parents=True, exist_ok=False)
    (stage / "acquire-probe-011.py").write_text(acquire)
    (stage / "d150_anchor_skip_probe.rs").write_text(probe)
    digest = {name: sha256(stage / name) for name in ("acquire-probe-011.py", "d150_anchor_skip_probe.rs")}
    (stage / "prepared-tool-sha256.json").write_text(json.dumps(digest, indent=2) + "\n")
    print(stage)


def verified_inputs(plan):
    stage = owned_stage(plan)
    acquisition = stage / "materialized/acquisition.json"
    require(acquisition.resolve() == acquisition, "unexpected path to acquisition receipt")
    receipt = read_json(acquisition)
    expected = plan["minimal_probe"]
    require(receipt["manifest_sha256"] == expected["frozen_manifest_sha256"], "corpus identity differs")
    require(receipt["original_count"] == len(expected["records"]), "original count differs")
    require(receipt["archive"] == plan["acquisition"]["archive"], "archive identity differs")
    require(receipt["archive_verified_and_removed"] is True, "archive authentication or cleanup is unrecorded")
    inputs = {}
    for row, wanted in zip(receipt["records"], expected["records"], strict=True):
        name = Path(wanted["path"]).name
        path = stage / "materialized/inputs" / name
        require(row == {**wanted, "acquired_path": str(path)}, f"original manifest differs: {name}")
        require(path.resolve() == path and path.stat().st_size == wanted["bytes"]
                and sha256(path) == wanted["sha256"], f"original bytes differ: {name}")
        inputs[name] = (path, wanted)
    return inputs


def footprint(cells):
    return any((bx - ax) * (cy - ay) != (by - ay) * (cx - ax)
               for ax, ay in cells for bx, by in cells for cx, cy in cells)


def proposal_screen(plan, shape, proposals, evidence, tracker, bilateral):
    """Apply the fixed native screen to the existing independently measured holdouts."""
    limits = plan["native_held_out_screen"]
    counts = evidence["holdout_count_forward_reverse"]
    result = {"status": "unresolved", "winner": None, "witness_counts": counts, "directions": {}}
    if not evidence["holds"]:
        return result
    np = bilateral["np"]
    grid = {tuple(point): (n % 9 // 3, n // 9 // 3)
            for n, point in enumerate(tracker["witness_points"](shape))}
    survivors = set(proposals) if min(counts) >= limits["min_witnesses_per_direction"] and len(proposals) >= 2 else set()
    for direction in ("forward", "reverse"):
        rows = evidence["holds"][direction]
        query = np.asarray([row["query"] for row in rows])
        match = np.asarray([row["match"] for row in rows])
        cells = [grid[tuple(point)] for point in query]
        occupied = set(cells)
        errors = {}
        for name, matrix in proposals.items():
            projection = matrix if direction == "forward" else np.linalg.inv(matrix)
            errors[name] = np.linalg.norm(bilateral["transfer"](projection, query) - match, axis=1)
        summary = {"macrocells": sorted(occupied), "errors_px": {k: v.tolist() for k, v in errors.items()}, "screens": []}
        result["directions"][direction] = summary
        if len(occupied) < limits["min_noncollinear_witness_macrocells"] or not footprint(occupied):
            survivors.clear()
        for omitted in [None, *sorted(occupied)]:
            selected = [i for i, cell in enumerate(cells) if cell != omitted]
            medians = {name: float(np.median(values[selected])) for name, values in errors.items()} if selected else {}
            summary["screens"].append({"omitted_macrocell": omitted, "count": len(selected), "medians_px": medians})
            if len(selected) < limits["min_remaining_matches_per_direction_and_omission"]:
                survivors.clear()
            survivors &= {name for name, error in medians.items()
                          if error <= limits["max_directional_median_residual_native_px"]
                          and all(other - error > limits["strict_min_directional_median_advantage_native_px"]
                                  for rival, other in medians.items() if rival != name)}
    if len(survivors) == 1:
        result.update(status="native_supported_proposal", winner=survivors.pop())
    return result


def product_rows(plan, paths, path):
    trace = read_json(path)
    require(trace["source_order"] == list(paths), "product frame order differs")
    require(trace["runtime"] == "cpu" and trace["scale_factor"] == 6
            and trace["max_scale_step"] == 0.05 and trace["max_precision"] is False, "product trace settings differ")
    rows = {(row["reference"], row["source"]): row for row in trace["estimates"]}
    edges = [edge["files"] for edge in plan["comparison_roster"] if edge["role"] == "fresh_bidirectional_fit"]
    expected = {tuple(pair) for before, after in edges for pair in ((before, after), (after, before))}
    require(len(rows) == len(trace["estimates"]) == len(expected) and rows.keys() == expected,
            "directed fit roster differs")
    return rows


def edge_proposals(edge, fits, archived, bilateral, scale_limit):
    np = bilateral["np"]
    before, after = edge["files"]
    fresh = edge["role"] == "fresh_bidirectional_fit"
    if fresh:
        direct = fits[(before, after)]
        reverse = fits[(after, before)]
        candidates = [("direct", direct["transform"], direct["confidence"], False),
                      ("inverse_reverse", reverse["transform"], reverse["confidence"], True)]
    else:
        previous = archived[(before, after)]
        candidates = [("direct", previous["direct_anchor_step"], None, False),
                      ("inverse_reverse", previous["reverse_anchor_step"], None, False)]
    proposals = {"identity_baseline": np.eye(3)}
    audit = {}
    lower, upper = np.float32(1 - scale_limit), np.float32(1 + scale_limit)
    for name, raw, confidence, invert in candidates:
        record = {"status": "unavailable", "input_matrix": raw, "confidence": confidence}
        audit[name] = record
        if fresh and (type(confidence) not in (int, float) or not math.isfinite(confidence) or confidence <= 0):
            continue
        try:
            matrix = bilateral["homogeneous"](raw)
            if invert:
                matrix = np.linalg.inv(matrix)
        except (AssertionError, ValueError, np.linalg.LinAlgError):
            record["status"] = "invalid_geometry"
            continue
        matrix = matrix.astype(np.float32).astype(np.float64)
        record["native_matrix"] = matrix[:2].tolist()
        scale = matrix[0, 0]
        if (not np.isfinite(matrix).all() or scale != matrix[1, 1] or matrix[0, 1] != 0
                or matrix[1, 0] != 0 or not lower <= scale <= upper):
            record["status"] = "invalid_geometry"
            continue
        if any(np.array_equal(matrix, other) for other in proposals.values()):
            record["status"] = "duplicate"
            continue
        record["status"] = "present"
        proposals[name] = matrix
    return proposals, audit


def controls(plan, results):
    limits = plan["native_held_out_screen"]
    by_edge = {tuple(row["indices"]): row["native"] for row in results}
    genuine = by_edge[(64, 65)]["winner"] in ("direct", "inverse_reverse")
    jump = by_edge[(138, 139)]["directions"]
    rejected = len(jump) == 2 and all(
        len(direction["macrocells"]) >= limits["min_noncollinear_witness_macrocells"]
        and footprint(direction["macrocells"])
        and all(screen["count"] >= (limits["min_witnesses_per_direction"] if screen["omitted_macrocell"] is None
                                    else limits["min_remaining_matches_per_direction_and_omission"])
                and screen["medians_px"].get("direct", 0) > limits["max_directional_median_residual_native_px"]
                and any(value <= limits["max_directional_median_residual_native_px"]
                        for name, value in screen["medians_px"].items() if name != "direct")
                for screen in direction["screens"])
        for direction in jump.values()
    )
    return {"genuine_nonidentity_supported": genuine, "historical_direct_jump_rejected": rejected,
            "status": "controls_reproduced" if genuine and rejected else "inconclusive"}


def score(plan, trace, output):
    import cv2

    require(cv2.__version__ == plan["native_held_out_screen"]["opencv_last_verified"], "OpenCV version differs")
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)
    stage = owned_stage(plan)
    require(trace == stage / "product-proposals.json" and trace.resolve() == trace
            and output == stage / "native-holdouts.json",
            "unexpected path to owned proposal or output receipt")
    paths = verified_inputs(plan)
    fits = product_rows(plan, paths, trace)
    tracker = runpy.run_path(str(HERE.parent / "local-track.py.txt"))
    bilateral = runpy.run_path(str(HERE.parent / "motion-admission/bilateral.py.txt"))
    prior = read_json(HERE.parent / "motion-admission/direction-replay.json")
    archived = {tuple(row["interval"]): row for row in prior["results"]}
    images = {name: tracker["image"](path, row) for name, (path, row) in paths.items()}
    results = []
    packed = []
    for edge in plan["comparison_roster"]:
        before, after = edge["files"]
        proposals, audit = edge_proposals(edge, fits, archived, bilateral, plan["candidate_limits"]["product_max_scale_step"])
        evidence = bilateral["bilateral"](tracker, images[before], images[after], proposals)
        native = proposal_screen(plan, images[before].shape, proposals, evidence, tracker, bilateral)
        with_proxy = len(proposals) == plan["candidate_limits"]["max_nominal_hypotheses_each_edge"]
        if with_proxy:
            packed.append({"interval": [before, after], "direct_anchor_step": proposals["direct"][:2].tolist(),
                           "reverse_anchor_step": proposals["inverse_reverse"][:2].tolist(),
                           "witnesses_forward_reverse": native["witness_counts"]})
        results.append({**edge, "proposals": audit, "native": native, "holdout_evidence": evidence,
                        "packed_input": "ready" if with_proxy else "unavailable"})
    require(verified_inputs(plan) == paths, "stage differs after native scoring")
    with output.open("x") as destination:
        json.dump({"plan_sha256": PLAN_SHA256, "proposal_trace_sha256": sha256(trace), "all_input_hashes_stable": True,
                   "controls": controls(plan, results), "comparisons": results}, destination, indent=2, allow_nan=False)
    with (stage / "packed-directions.json").open("x") as destination:
        json.dump({"results": packed}, destination, indent=2, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("verify-inputs")
    scoring = sub.add_parser("score")
    scoring.add_argument("--trace", type=Path, required=True)
    scoring.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = load_plan(args.plan)
    if args.command == "prepare":
        prepare(plan)
    elif args.command == "verify-inputs":
        require(len(verified_inputs(plan)) == 11, "wrong input count")
        print("Verified all 11 ordered originals.")
    else:
        score(plan, args.trace, args.output)


if __name__ == "__main__":
    main()
