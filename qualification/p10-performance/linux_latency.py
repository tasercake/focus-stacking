"""Capture native viewer presentation and worker acknowledgements on private Xvfb."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path

import numpy as np
from framebuffer import (
    Patch,
    XTestPointer,
    XwdScreen,
    observe_transition,
    observed_desktop,
    wait_pixels,
)
from p10 import (
    CANDIDATE,
    ROOT,
    TARGETS_PATH,
    _campaign_lock,
    _candidate_binary,
    _environment,
    _hardware,
    _pci_id,
    _require_clean,
    _snapshot,
    _write,
)
from pancake_conformance.fixtures import generate_fixture
from pancake_conformance.linux_ui import LinuxUISession
from pancake_conformance.macos_ui import MacOSUISession, find_node
from pancake_conformance.target import TargetSpec
from PIL import Image
from protocol import Campaign, corpus, sha256, verify_frames
from resources import NvidiaMemory


def _gui_target(receipt_path):
    target = TargetSpec.load(CANDIDATE)
    _require_clean(ROOT, "pancake", str(CANDIDATE))
    expected = _snapshot(target, target.root / "Cargo.lock")
    executable = _candidate_binary(target, "gui")
    expected.update(
        {
            "component": "gui",
            "executable": str(executable),
            "binary_sha256": sha256(executable),
        }
    )
    receipt = json.loads(receipt_path.read_text())
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError(
            "GUI source, lock, descriptor or binary differs from its release build receipt"
        )
    return target, receipt


def _workload(args, directory):
    if args.workload == "lifecycle":
        root = directory / "lifecycle-inputs"
        fixture = generate_fixture("lifecycle", root)
        frames = [
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in fixture.paths
        ]
        proof = {
            "fixture_implementation_sha256": sha256(
                Path(sys.modules[generate_fixture.__module__].__file__)
            ),
            "metadata": fixture.metadata,
            "shape": list(fixture.shape),
        }
        return root, frames, 64, proof
    if args.input_root is None:
        raise ValueError("provide the verified workload staging directory")
    campaign = Campaign.load(TARGETS_PATH)
    rows, proof = corpus(ROOT, campaign, args.workload)
    recipe = next(
        item for item in campaign.raw["workloads"] if item["id"] == args.workload
    )
    return args.input_root.resolve(), rows, recipe["frames"], proof


def _control_point(ui, anchor):
    if "point" in anchor:
        return anchor["point"]
    node = ui.node(anchor["control"])
    x, y = node["position"]
    width, height = node["size"]
    if width <= 0 or height <= 0 or node.get("enabled") is False:
        raise ValueError(f"native input control is unavailable: {anchor['control']}")
    fx, fy = anchor.get("fraction", (0.5, 0.5))
    if not (0 < fx < 1 and 0 < fy < 1):
        raise ValueError("native control fractions must identify an interior point")
    return x + int(width * fx), y + int(height * fy)


@contextmanager
def _prepare_pointer(pointer, ui, motion):
    kind = motion["kind"]
    if kind not in ("click", "scroll_up", "scroll_down", "drag"):
        raise ValueError(f"unsupported native input {kind}")
    start = _control_point(ui, motion["at"])
    final = _control_point(ui, motion["to"]) if kind == "drag" else None
    button = {"scroll_up": 4, "scroll_down": 5}.get(kind, 1)
    pointer.move(*start)
    if final is not None:
        pointer.button(button, True)
    pointer.settle()
    released = False

    def dispatch():
        nonlocal released
        if final is None:
            pointer.button(button, True)
        else:
            pointer.move(*final)
        pointer.button(button, False)
        released = True
        pointer.flush()

    try:
        yield dispatch
    finally:
        if final is not None and not released:
            pointer.button(button, False)
            pointer.flush()


def _witnesses(scenario_root, records):
    patches, identity = [], []
    for record in records:
        path = (scenario_root / record["png"]).resolve(strict=True)
        if not path.is_relative_to(scenario_root):
            raise ValueError(f"witness PNG is outside the scenario directory: {path}")
        with Image.open(path, formats=("PNG",)) as image:
            pixels = np.asarray(image.convert("RGB")).copy()
        tolerance = record.get("max_channel_error", 0)
        if not isinstance(tolerance, int) or not 0 <= tolerance < 255:
            raise ValueError("invalid witness color tolerance")
        x, y = record["point"]
        patches.append(Patch(x, y, pixels, tolerance))
        identity.append(
            {
                **record,
                "size": [pixels.shape[1], pixels.shape[0]],
                "sha256": sha256(path),
            }
        )
    return patches, identity


def _state(ui, status):
    node = find_node(ui.snapshot(), status["control"])
    label = str(node[status.get("field", "title")]).strip()
    if not label:
        raise ValueError("native worker status is empty")
    return label.split(maxsplit=1)[0].rstrip(":").casefold(), label


def _wait_state(ui, status, expected, timeout, *, numerical=False):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        phase, label = _state(ui, status)
        observed = time.monotonic_ns()
        if phase in expected and (
            not numerical or _matches_viewer_load("loaded", phase, label)
        ):
            return observed, label
        time.sleep(0.001)
    raise TimeoutError(f"native worker did not report any of {sorted(expected)}")


def _matches_viewer_load(condition, phase, label):
    """Require a native worker admission from the actual numerical pipeline."""
    if condition == "idle":
        return phase in {"idle", "completed"}
    fields = label.casefold().split("·")
    return (
        phase == "running"
        and len(fields) >= 2
        and fields[1].strip() in {"decode", "register", "fuse"}
    )


def _viewer(step, context, sample, output, scenario_root):
    ui, screen, pointer, status = context
    condition = step["condition"]
    if condition not in ("idle", "loaded"):
        raise ValueError(f"unknown viewer load condition: {condition}")
    before, before_identity = _witnesses(scenario_root, step["before"])
    after, after_identity = _witnesses(scenario_root, step["after"])
    with _prepare_pointer(pointer, ui, step["input"]) as dispatch:
        wait_pixels(screen, before, 10)
        phase, label = _state(ui, status)
        if not _matches_viewer_load(condition, phase, label):
            raise ValueError(
                f"native state before {condition} viewer event was {label!r}"
            )
        sample["worker_before"] = label
        observation = observe_transition(screen, dispatch, before, after, timeout=4)
    # Read worker state after the visible framebuffer endpoint, outside the timer.
    phase, label = _state(ui, status)
    sample["worker_after"] = label
    witnesses = observation.pop("witnesses")
    sample.update(observation)
    sample.update(
        {
            "condition": condition,
            "action": step["action"],
            "expected_before": before_identity,
            "expected_after": after_identity,
            "actual_after": [],
        }
    )
    for index, (observed, error) in enumerate(witnesses):
        path = output / f"presented-{index:02d}.png"
        Image.fromarray(observed).save(path)
        sample["actual_after"].append(
            {"path": str(path), "sha256": sha256(path), "max_channel_error": error}
        )
    if not _matches_viewer_load(condition, phase, label):
        raise ValueError(
            f"worker left the requested viewer workload during sample: {label!r}"
        )


def _worker_metadata(ui, status):
    node = find_node(ui.snapshot(), status["control"])
    data = json.loads(node["description"])
    if not isinstance(data, dict):
        raise TypeError(
            "native worker status lacks structured acknowledgement evidence"
        )
    return data


def _cancel_observation(before, after):
    """Accept the current or latched native acknowledgement from the same job."""
    generation = before.get("generation")
    if not generation or after.get("generation") != generation:
        raise ValueError("native generation changed during cancellation observation")
    if (
        before.get("state") != "Running"
        or before.get("cancel_acknowledged") is not False
    ):
        raise ValueError(
            "cancel requires an active generation without a stale acknowledgement"
        )
    state = after.get("state")
    acknowledged = after.get("cancel_acknowledged") is True
    if acknowledged and state == "Cancelling":
        return "native_cancelling_state"
    if acknowledged and state == "Idle":
        return "latched_actual_acknowledgement"
    if state in {"Idle", "Completed", "Failed"}:
        raise ValueError(
            f"native worker entered {state} without a cancellation acknowledgement"
        )
    if acknowledged:
        raise ValueError(
            f"native worker reported cancellation acknowledgement in inconsistent state {state}"
        )
    return None


def _wait_cancel(ui, status, before, timeout, *, settled=False):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = _worker_metadata(ui, status)
        observed = time.monotonic_ns()
        kind = _cancel_observation(before, current)
        if kind and (not settled or current["state"] == "Idle"):
            return observed, kind, current
        time.sleep(0.001)
    raise TimeoutError(
        "native worker did not expose the requested same-generation cancellation evidence"
    )


def _lifecycle(step, context, sample):
    ui, _, pointer, status = context
    operation = step["operation"]
    if operation not in ("pause", "cancel"):
        raise ValueError(f"unknown lifecycle operation: {operation}")
    sample["operation"] = operation
    before = None
    with _prepare_pointer(pointer, ui, step["input"]) as dispatch:
        _, sample["worker_before"] = _wait_state(
            ui, status, {"running"}, 10, numerical=True
        )
        if operation == "cancel":
            before = _worker_metadata(ui, status)
            _cancel_observation(before, before)
            sample["native_job_before"] = before
        sample["dispatched_ns"] = time.monotonic_ns()
        dispatch()
    if before is None:
        ack, label = _wait_state(ui, status, {"paused"}, 4)
        sample.update(
            {
                "acknowledged_ns": ack,
                "settled_ns": ack,
                "worker_at_acknowledgement": label,
                "worker_settled": label,
                "ack_observation": "native_paused_state",
            }
        )
    else:
        ack, observed_kind, acknowledged = _wait_cancel(ui, status, before, 4)
        sample.update(
            {
                "acknowledged_ns": ack,
                "ack_observation": observed_kind,
                "worker_at_acknowledgement": acknowledged,
            }
        )
        settled, terminal = ack, acknowledged
        if acknowledged["state"] != "Idle":
            settled, _, terminal = _wait_cancel(ui, status, before, 120, settled=True)
        sample.update({"settled_ns": settled, "worker_settled": terminal})


def _setup(step, context):
    ui, _, pointer, status = context
    for motion in step.get("inputs", ()):
        with _prepare_pointer(pointer, ui, motion) as dispatch:
            dispatch()
    if "worker_phase" in step:
        _wait_state(ui, status, {step["worker_phase"]}, 120)


def _steps(steps, context, directory, scenario_root, ledger):
    for index, step in enumerate(steps):
        sample = {"step": index, "input": step.get("input"), "valid": False}
        output = directory / f"event-{index:04d}"
        output.mkdir()
        try:
            kind = step["kind"]
            if kind == "viewer":
                _viewer(step, context, sample, output, scenario_root)
            elif kind == "lifecycle":
                _lifecycle(step, context, sample)
            elif kind == "setup":
                _setup(step, context)
            else:
                raise ValueError(f"unknown native scenario step {kind}")
            sample["valid"] = True
            if kind in ("viewer", "lifecycle"):
                ledger[kind].append(sample)
        finally:
            _write(output / "sample.json", sample)


def _physical_execution_proof(path, pci):
    events = [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    ]
    completions = [event for event in events if event.get("event") == "stack_complete"]
    if not completions or any(
        event.get("event") in {"observer_error", "backend_fallback"} for event in events
    ):
        raise ValueError(
            "native capture lacks successful physical wgpu completion evidence"
        )
    for event in completions:
        if (
            event.get("completed") is not True
            or event.get("actual_backend") != "gpu"
            or event.get("runtime") != "wgpu-vulkan"
            or event.get("physical_gpu") is not True
            or event.get("fallback_reason")
            or _pci_id(event.get("device_pci_address")) != _pci_id(pci)
        ):
            raise ValueError(
                "native job did not complete on the matched physical wgpu device"
            )
    return completions


def collect(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    scenario_path = args.scenario.resolve(strict=True)
    scenario = json.loads(scenario_path.read_text())
    if scenario.get("schema_version") != 1:
        raise ValueError("unsupported native scenario schema")
    if scenario.get("workload", args.workload) != args.workload:
        raise ValueError("native scenario uses a different frozen input set")
    if (
        any(step["kind"] == "viewer" for step in scenario["steps"])
        and args.workload != "T50"
    ):
        raise ValueError(
            "native viewer capture requires the frozen generated 24 MP T50 source"
        )
    ledger = {
        "schema_version": 1,
        "candidate": None,
        "workload": args.workload,
        "status": "pending",
        "capture": "private Xvfb XWD screen. First observed correct frame is a conservative upper bound",
        "performance_targets_sha256": sha256(TARGETS_PATH),
        "collector_sha256": sha256(Path(__file__)),
        "scenario": str(scenario_path),
        "scenario_sha256": sha256(scenario_path),
        "viewer": [],
        "lifecycle": [],
    }
    staged = None
    resources = ExitStack()
    try:
        resources.enter_context(_campaign_lock())
        target, receipt = _gui_target(args.build_receipt)
        physical = scenario.get("physical_wgpu")
        residency = None
        gpu_uuid = physical["gpu_uuid"] if physical else None
        if physical:
            if any(
                physical.get(key) != receipt.get(key)
                for key in ("commit", "binary_sha256")
            ):
                raise ValueError(
                    "physical view scenario uses a different exact GUI build"
                )
            residency = NvidiaMemory(gpu_uuid)
            resources.callback(residency.close)
        hardware = _hardware(gpu_uuid)
        staged = _workload(args, output)
        root, records, count, proof = staged
        frames = verify_frames(
            root, records, count, distinct_content=args.workload != "lifecycle"
        )
        ledger.update(
            {
                "candidate": receipt,
                "input_manifest": proof,
                "ordered_inputs": records,
                "hardware": hardware,
            }
        )
        env = _environment(
            target,
            output / "cache",
            output,
            len(os.sched_getaffinity(0)),
            gpu_uuid,
            "wgpu" if physical else None,
            bool(physical),
        )
        env.update(
            {
                key: os.environ[key]
                for key in ("XDG_DATA_DIRS", "XDG_CONFIG_DIRS", "PANCAKE_ATSPI_PYTHON")
                if key in os.environ
            }
        )
        argv = [receipt["executable"], *target.command("gui")[1:], *map(str, frames)]
        with (
            observed_desktop(output, env) as (private, screen_path),
            XwdScreen(screen_path) as screen,
            (output / "stdout.txt").open("wb") as stdout,
            (output / "stderr.txt").open("wb") as stderr,
        ):
            process = subprocess.Popen(
                argv,
                cwd=target.root,
                env=private,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                with (
                    LinuxUISession(process, output, private) as ui,
                    XTestPointer(private, screen) as pointer,
                ):
                    ledger.update(
                        {
                            "argv": argv,
                            "display": private["DISPLAY"],
                            "size": [screen.width, screen.height],
                        }
                    )
                    if residency is not None:
                        observed = residency.sample({process.pid})
                        if not observed:
                            raise ValueError(
                                "visible GUI did not show residency on the selected physical GPU before jobs"
                            )
                        ledger["physical_wgpu_run"] = {
                            "gpu_uuid": gpu_uuid,
                            "display_backend": "default automatic shared wgpu",
                            "process_gpu_residency_at_visible_launch_bytes": observed,
                        }
                    _steps(
                        scenario["steps"],
                        (ui, screen, pointer, scenario["worker_status"]),
                        output,
                        scenario_path.parent,
                        ledger,
                    )
            finally:
                MacOSUISession._reap(process)
        if physical:
            ledger["physical_wgpu_run"]["stack_completions"] = (
                _physical_execution_proof(
                    output / "events.jsonl", hardware["gpu"]["pci.bus_id"]
                )
            )
        if _gui_target(args.build_receipt)[1] != receipt:
            raise ValueError("candidate GUI provenance changed during capture")
        ledger["status"] = "captured"
    except (
        AssertionError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        ledger.update({"status": "fail", "error": str(error)})
    finally:
        if staged is not None:
            root, records, count, _ = staged
            try:
                verify_frames(
                    root, records, count, distinct_content=args.workload != "lifecycle"
                )
                ledger["inputs_unchanged"] = True
            except (OSError, ValueError) as error:
                ledger.update(
                    {
                        "status": "fail",
                        "inputs_unchanged": False,
                        "source_error": str(error),
                    }
                )
        try:
            for name in (
                "lifecycle-inputs",
                "cache",
                "screen",
                "bin",
                "home",
                "runtime",
            ):
                owned = output / name
                if owned.is_dir():
                    shutil.rmtree(owned)
        except OSError as error:
            ledger.update({"status": "fail", "cleanup_error": str(error)})
        finally:
            resources.close()
            _write(output / "native-latency.json", ledger)
    return 0 if ledger["status"] == "captured" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument(
        "--workload", choices=("T50", "lifecycle", "R50", "D150", "E9"), required=True
    )
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return collect(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
