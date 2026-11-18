"""Prepare fixed native scenarios from the actual release and pixel witnesses."""

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from linux_latency import _witnesses
from p10 import TARGETS_PATH
from PIL import Image
from protocol import Campaign

ACTIONS = ("source", "result", "pan", "zoom", "comparison")


def _identity(identity):
    for key, pattern in (
        ("commit", r"[0-9a-f]{40}"),
        ("binary_sha256", r"[0-9a-f]{64}"),
        ("gpu_uuid", r"GPU-[0-9a-f-]{36}"),
    ):
        if not re.fullmatch(pattern, identity.get(key, "")):
            raise ValueError(f"incomplete physical native release identity: {key}")
    return {key: identity[key] for key in ("commit", "binary_sha256", "gpu_uuid")}


def _click(control):
    return {"kind": "click", "at": {"control": control}}


def _choice(title):
    return _click({"role": "AXRow", "title": title})


def _physical_setup():
    return {
        "kind": "setup",
        "inputs": [
            _click("settings.open"),
            _click("settings.device"),
            _choice("GPU"),
            _click("dialog.close"),
        ],
    }


def _scenario(identity, workload, steps):
    return {
        "schema_version": 1,
        "physical_wgpu": _identity(identity),
        "workload": workload,
        "worker_status": {"control": "stack.status", "field": "title"},
        "steps": steps,
    }


def build_lifecycle(identity, workload):
    """One exact 64-path or real D150 cohort, with real work restarted each cycle."""
    method = {"lifecycle": "laplacian", "D150": "hybrid"}.get(workload)
    if method is None:
        raise ValueError("use the frozen 64-path lifecycle workload or real D150")
    targets = Campaign.load(TARGETS_PATH).raw["targets"]
    minimum = targets["pause_and_cancel"]["minimum_requests_per_operation"]
    steps = [
        _physical_setup(),
        {
            "kind": "setup",
            "inputs": [
                _click(f"method.{method}"),
                _click("alignment"),
                _choice("Breathing"),
            ],
        },
    ]
    for _ in range(minimum):
        steps.extend(
            (
                {
                    "kind": "setup",
                    "inputs": [_click("stack.start")],
                    "worker_phase": "running",
                },
                {
                    "kind": "lifecycle",
                    "operation": "pause",
                    "input": _click("stack.pause"),
                },
                {
                    "kind": "setup",
                    "inputs": [_click("stack.resume")],
                    "worker_phase": "running",
                },
                {
                    "kind": "lifecycle",
                    "operation": "cancel",
                    "input": _click("stack.stop"),
                },
            )
        )
    # Outside the acknowledgement samples, corroborate reusable worker and
    # completed physical compute with a genuine job on this same corpus.
    steps.append(
        {
            "kind": "setup",
            "inputs": [_click("stack.start")],
            "worker_phase": "completed",
        }
    )
    return _scenario(identity, workload, steps)


def _fixed_pixels(root, trial):
    patches = []
    for field in ("before", "after"):
        sources = trial[field]
        for record in sources:
            image_path = (root / record["png"]).resolve(strict=True)
            if not image_path.is_relative_to(root):
                raise ValueError("fixed witness image lies outside its scenario")
            with Image.open(image_path, formats=("PNG",)) as image:
                if image.mode != "RGB":
                    raise ValueError(
                        "physical display witness must be a genuine RGB PNG"
                    )
        entries, _ = _witnesses(root, sources)
        patches.append(entries)
    for lhs in patches[0]:
        for rhs in patches[1]:
            if (lhs.x, lhs.y, lhs.rgb.shape) == (rhs.x, rhs.y, rhs.rgb.shape):
                error = int(np.abs(lhs.rgb.astype(np.int16) - rhs.rgb).max())
                if error > lhs.tolerance + rhs.tolerance:
                    return
    raise ValueError(
        "before and after require at least one distinguishable fixed screen witness"
    )


def build_viewer(manifest, root):
    """Expand independently calibrated physical pixel states into the frozen sample cohorts."""
    root = root.resolve()
    if manifest.get("renderer") != "physical-wgpu-vulkan" or not manifest.get(
        "witness_provenance"
    ):
        raise ValueError("independent physical wgpu witness provenance is required")
    targets = Campaign.load(TARGETS_PATH).raw["targets"]
    count = math.ceil(
        targets["viewer_event_to_present"]["minimum_events"] / len(ACTIONS)
    )
    steps = [_physical_setup()]
    for condition in ("idle", "loaded"):
        group = manifest["cohorts"][condition]
        steps.extend(group["setup"])
        trials = group["trials"]
        if set(trials) != set(ACTIONS):
            raise ValueError(f"missing fixed witness family in {condition}")
        for trial in trials.values():
            _fixed_pixels(root, trial)
        for _ in range(count):
            for action in ACTIONS:
                trial = trials[action]
                steps.extend(trial.get("setup", ()))
                steps.append(
                    {
                        "kind": "viewer",
                        "condition": condition,
                        "action": action,
                        **{name: trial[name] for name in ("input", "before", "after")},
                    }
                )
    return _scenario(manifest["identity"], "T50", steps) | {
        "witness_provenance": manifest["witness_provenance"]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="recipe", required=True)
    lifecycle = sub.add_parser(
        "lifecycle", help="Prepare native pause/resume/cancel cycles"
    )
    lifecycle.add_argument(
        "--identity",
        type=Path,
        required=True,
        help="Exact GUI commit, SHA-256 and physical GPU UUID JSON",
    )
    lifecycle.add_argument("--workload", choices=("lifecycle", "D150"), required=True)
    viewer = sub.add_parser(
        "viewer", help="Expand independently reviewed physical-pixel trial families"
    )
    viewer.add_argument("--manifest", type=Path, required=True)
    for recipe in (lifecycle, viewer):
        recipe.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.recipe == "lifecycle":
        scenario = build_lifecycle(json.loads(args.identity.read_text()), args.workload)
    else:
        root = args.manifest.resolve().parent
        if args.output.resolve().parent != root:
            raise ValueError("keep the scenario beside its relative RGB witness paths")
        scenario = build_viewer(json.loads(args.manifest.read_text()), root)
    with args.output.open("x") as out:
        json.dump(scenario, out, indent=2)
        out.write("\n")


if __name__ == "__main__":
    main()
