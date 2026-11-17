"""Observe real native controls and pixels through the unchanged Linux driver."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from PIL import Image
from pancake_conformance.linux_ui import LinuxUISession, isolated_desktop


def value(snapshot, identifier):
    """Read exactly one published native node, with no application imports."""
    nodes = [node for node in snapshot["nodes"] if node["id"] == identifier]
    if len(nodes) != 1:
        raise AssertionError(f"Expected native node {identifier}, found {nodes}")
    return str(nodes[0]["value"])


def preview_matches(ui, snapshot, destination, inverted):
    """Require independent black/white checker samples inside actual preview pixels."""
    nodes = [node for node in snapshot["nodes"] if node["id"] == "preview"]
    if len(nodes) != 1:
        return False
    node = nodes[0]
    image = Image.open(ui.screenshot(destination)).convert("RGB")
    for x, y, white in [(16, 16, False), (48, 16, True), (16, 48, True), (48, 48, False)]:
        point = (round(node["position"][0] + x * node["size"][0] / 512),
                 round(node["position"][1] + y * node["size"][1] / 384))
        expected = (255, 255, 255) if white ^ inverted else (0, 0, 0)
        if image.getpixel(point) != expected:
            return False
    return snapshot


def run(binary, directory):
    """Prove input, real image presentation, bounded ownership and cancellation."""
    directory.mkdir(parents=True, exist_ok=True)
    with isolated_desktop(directory / "desktop", os.environ) as environment:
        # AccessKit activates only when the private desktop accessibility status
        # is enabled. This changes this owned bus, never the host session.
        subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.a11y.Bus", "--object-path", "/org/a11y/bus",
             "--method", "org.freedesktop.DBus.Properties.Set", "org.a11y.Status", "IsEnabled", "<true>"],
            env=environment, check=True, capture_output=True, text=True,
        )
        log = (directory / "application.log").open("w")
        process = subprocess.Popen([str(binary)], env=environment, stdout=log, stderr=log)
        try:
            with LinuxUISession(process, directory, environment) as ui:
                ui.node("toggle-pattern")
                initial = ui.wait(lambda snap: preview_matches(ui, snap, directory / "before.png", False)
                                  if "Ready" in value(snap, "worker-state") else None,
                                  description="independent initial computed pixels")
                assert "confirmed" in value(initial, "interop-state"), initial
                assert "Cpu" not in value(initial, "device-state"), initial
                ui.click("toggle-pattern")
                changed = ui.wait(lambda snap: preview_matches(ui, snap, directory / "after.png", True)
                                  if "Pattern B" in value(snap, "pattern-state") and "Ready" in value(snap, "worker-state") else None,
                                  description="independent replacement computed pixels")
                ui.click("start-job")
                running = ui.wait(lambda snap: snap if "Running" in value(snap, "worker-state") and int(value(snap, "completed-batches")) > 0 else None,
                                  description="completed real compute batch")
                ui.click("ping-ui")
                responsive = ui.wait(lambda snap: snap if value(snap, "ui-count") == "1" and "Running" in value(snap, "worker-state")
                                     and int(value(snap, "completed-batches")) > int(value(running, "completed-batches")) else None,
                                     description="responsive native control during compute")
                ui.click("cancel-job")
                cancelled = ui.wait(lambda snap: snap if "Cancelled" in value(snap, "worker-state") else None, description="batch-boundary cancellation")
                completed = int(value(cancelled, "completed-batches"))
                assert 0 < completed < 128, cancelled
                assert int(value(cancelled, "submitted-batches")) == completed, cancelled
                cache_peak = int(value(cancelled, "cache-peak"))
                assert cache_peak == 2, cancelled
                budget = {key: int(number) for key, number in
                          (part.split("=", 1) for part in value(cancelled, "budget-state").split(";"))}
                assert budget["cmd_slots"] == budget["preview_slots"] == 1, budget
                assert budget["u16_peak"] == 2 and budget["u16_bytes"] == 12_582_912, budget
                assert 1 <= budget["rgba_peak"] <= 3 and budget["rgba_bytes"] == 786_432 * budget["rgba_peak"], budget
                assert budget["texture_peak"] == 2 and budget["texture_bytes"] == 1_572_864, budget
                assert budget["u16_live"] == budget["rgba_live"] == 0, budget
                ui.click("ping-ui")
                stopped = ui.wait(lambda snap: snap if value(snap, "ui-count") == "2" else None, description="responsive cancelled state")
                assert int(value(stopped, "submitted-batches")) == completed, stopped
                ui.click("start-job")
                ui.wait(lambda snap: "Running" in value(snap, "worker-state") and int(value(snap, "completed-batches")) > 0,
                        description="worker reuse after cancellation")
                ui.click("cancel-job")
                reused = ui.wait(lambda snap: snap if "Cancelled" in value(snap, "worker-state") else None, description="second cancellation")
                result = {"initial": initial, "pattern_changed": changed, "running": running, "responsive": responsive,
                          "cancelled": cancelled, "stopped": stopped, "reused": reused, "cache_peak": cache_peak,
                          "completed_before_cancel": completed, "budget": budget,
                          "device": value(initial, "device-state")}
                # Normal window-manager close exercises application ownership
                # teardown; the driver's forced process cleanup is not a pass.
                ui.key("F4", modifiers=("alt",))
                result["normal_exit_status"] = process.wait(timeout=10)
                assert result["normal_exit_status"] == 0, result
                (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
                return result
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    run(arguments.binary.resolve(), arguments.directory.resolve())
