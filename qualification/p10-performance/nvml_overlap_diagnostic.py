"""Measure E9 NVML call overlap without producing qualification results."""

import argparse
import json
import os
import queue
import signal
import subprocess
import tarfile
import tempfile
import threading
import time
from functools import partial
from itertools import pairwise
from pathlib import Path

from p10 import (
    ROOT,
    TARGETS_PATH,
    _assert_completion,
    _campaign_lock,
    _gpu_state,
    _pci_id,
    _write,
)
from protocol import Campaign, corpus, sha256, verify_frames, verify_output
from resources import (
    _MAX_SAMPLE_GAP_NS,
    _SAMPLE_NS,
    _UNAVAILABLE_MEMORY,
    NvidiaMemory,
    _session_memory,
    _signal_group,
)

UUID = "GPU-c7900bb5-e779-c07b-a37d-4adff841c8ac"
PCI = "0000:01:00.0"
DEVICE = "NVIDIA GeForce RTX 3090"
DRIVER = "580.178.04"
RELEASE = "12f2151c8a198b5209c8f4d506dbd17fd9aaa74f"
LOCK_SHA256 = "f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc"
SPEC_SHA256 = "58bb68533311c48696a3a844d80eef2f37a3c1f39649305948c838b7002663dc"
EVIDENCE = Path(__file__).with_name("evidence")
BUILDS = {
    "wgpu-vulkan": (
        "integrated-e9-12f2151/raw-paired-runs.tar.gz",
        "87b396f6984d4cb11414b2a044cf8e9aee0fcd180ae146e69c315c995de9c7ac",
        "integrated-e9-runs/vulkan/diagnostic-01/candidate/sample.json",
        "32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055",
    ),
    "cuda": (
        "integrated-e9-cuda-12f2151/raw-paired-cuda.tar.gz",
        "896db4114e2ce95eca592e03cc7be5ede139ff33b762342140545317a03c2087",
        "integrated-e9-cuda-run/cuda/diagnostic-01/candidate/sample.json",
        "45cb96ed124a3c8145e3c7cbbf836a3334580d14d63fde59596b393225910ec4",
    ),
}
CACHE_DIRS = {
    "HOME": "home",
    "XDG_CACHE_HOME": "cache",
    "XDG_CONFIG_HOME": "config",
    "TMPDIR": "tmp",
    "CUDA_CACHE_PATH": "cuda",
    "__GL_SHADER_DISK_CACHE_PATH": "nvidia",
    "MESA_SHADER_CACHE_DIR": "mesa",
    "NUMBA_CACHE_DIR": "numba",
    "PANCAKE_STATE_DIR": "home",
    "PANCAKE_COMPUTE_CACHE_DIR": "home/device-cache",
}
CALL_KINDS = ("compute", "graphics")
JOB_LIMIT = 12
DRAIN_LIMIT = 3


def pid_identity(pid):
    """Get session and process-start ticks from the same procfs row."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_bytes().rsplit(b")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    if fields[0] == b"Z":
        return None
    return int(fields[3]), int(fields[19])


class PairDevice(NvidiaMemory):
    """Share a prepared handle while allocating a fresh per-lane result array."""

    def __init__(self, provider):
        self.lib = provider.lib
        self.handle = provider.handle
        self.rows = type(provider.rows)()

    def read(self, kind):
        getter = getattr(self.lib, f"nvmlDeviceGet{kind.title()}RunningProcesses_v3")
        return [
            (
                row.pid,
                None if row.memory_bytes == _UNAVAILABLE_MEMORY else row.memory_bytes,
            )
            for row in self._query(getter, kind)
        ]


def capture_pair(
    lane, slot, scheduled_ns, session, read, identify, clock, publish=None
):
    """Record both returned tables, then reduce verified matching lifetimes."""
    calls = []
    issues = set()
    recorded_identities = {}
    bytes_by_pid = {}
    for kind in CALL_KINDS:
        before = clock()
        if publish is not None:
            publish({"slot": slot, "kind": kind, "started_ns": before})
        cpu = time.thread_time_ns()
        try:
            rows = read(kind)
        except (OSError, ValueError) as error:
            issues.add(f"query:{kind}")
            calls.append(
                {
                    "kind": kind,
                    "started_ns": before,
                    "finished_ns": clock(),
                    "error": str(error),
                    "records": [],
                }
            )
            continue
        call = {
            "kind": kind,
            "started_ns": before,
            "finished_ns": clock(),
            "thread_cpu_ns": time.thread_time_ns() - cpu,
            "records": [],
        }
        calls.append(call)
        for pid, used in rows:
            identity = identify(pid)
            call["records"].append(
                {
                    "pid": pid,
                    "bytes": used,
                    "identity": list(identity) if identity else None,
                    "identity_ns": clock(),
                }
            )
            if identity is None:
                issues.add(f"unresolved-pid:{pid}")
                continue
            if recorded_identities.setdefault(pid, identity) != identity:
                issues.add(f"pid-reuse:{pid}")
            if identity[0] == session:
                if used is None:
                    issues.add(f"unavailable:{pid}")
                else:
                    bytes_by_pid[pid] = max(bytes_by_pid.get(pid, 0), used)
    return {
        "lane": lane,
        "slot": slot,
        "scheduled_ns": scheduled_ns,
        "session": session,
        "calls": calls,
        "attributed_pids": sorted(bytes_by_pid),
        "bytes": sum(bytes_by_pid.values()) if not issues else None,
        "issues": sorted(issues),
        "finished_ns": clock(),
    }


class PairLane:
    """One worker with exactly one outstanding pair and no catch-up queue."""

    def __init__(self, capture):
        self.ready = threading.Event()
        self.commands = queue.Queue(maxsize=1)
        self.receipts = []
        self.active = None
        self.thread = threading.Thread(target=self._run, args=(capture,), daemon=True)
        self.thread.start()

    def _run(self, capture):
        self.ready.set()
        while (command := self.commands.get()) is not None:
            try:
                record = capture(*command)
            except (IndexError, OSError, RuntimeError, ValueError) as error:
                record = {"slot": command[0], "error": str(error)}
            self.receipts.append(record)
            self.active = None
            self.ready.set()

    def submit(self, command):
        if not self.ready.is_set():
            return False
        self.ready.clear()
        self.active = command
        self.commands.put_nowait(command)
        return True

    def close(self):
        self.commands.put_nowait(None)


def due_slot(launch_ns, now_ns, minimum_slot):
    """Use the newest due slot and leave any missed slots unfilled."""
    slot = (now_ns - launch_ns) // _SAMPLE_NS
    if slot < minimum_slot:
        return None
    return slot, launch_ns + slot * _SAMPLE_NS


def schedule(lanes, session, launch, stop, dispatches):
    next_slot = 0
    while not stop.is_set():
        now = time.monotonic_ns()
        due = due_slot(launch, now, next_slot)
        if due is None:
            stop.wait((launch + next_slot * _SAMPLE_NS - now) / 1e9)
            continue
        slot, at = due
        lane = next(
            (index for index, worker in enumerate(lanes) if worker.ready.is_set()), None
        )
        if stop.is_set():
            break
        if lane is not None:
            lanes[lane].submit((slot, at, session))
        dispatches.append(
            {
                "slot": slot,
                "scheduled_ns": at,
                "decision_ns": now,
                "lane": lane,
                "missed_slots": slot - next_slot,
            }
        )
        next_slot = slot + 1


def describe_arm(rows, launch, observed_exit):
    """Distinguish an observed bypass from bounded candidate coverage windows."""
    complete = [row for row in rows if "calls" in row]
    stalled = [
        row
        for row in complete
        if launch <= row["calls"][0]["started_ns"] < observed_exit
        and row["calls"][0]["finished_ns"] - row["calls"][0]["started_ns"]
        > _MAX_SAMPLE_GAP_NS
        and "error" not in row["calls"][0]
    ]
    in_job = [
        row
        for row in complete
        if launch
        <= row["calls"][0]["started_ns"]
        <= row["finished_ns"]
        <= observed_exit
        and not row["issues"]
    ]
    bounded = [
        row
        for row in in_job
        if row["finished_ns"] - row["calls"][0]["started_ns"] <= _MAX_SAMPLE_GAP_NS
    ]
    bypass = [
        [slow["slot"], fast["slot"]]
        for slow in stalled
        for fast in bounded
        if slow["lane"] != fast["lane"]
        and slow["calls"][0]["started_ns"] < fast["calls"][0]["started_ns"]
        and fast["finished_ns"] < slow["calls"][0]["finished_ns"]
    ]
    # A separate conservative series uses no overlapping acquisition windows.
    completions = [launch]
    window_gaps = []
    previous_begin = launch
    previous_end = launch
    for row in sorted(bounded, key=lambda item: item["finished_ns"]):
        completions.append(row["finished_ns"])
        begin = row["calls"][0]["started_ns"]
        if begin >= previous_end:
            window_gaps.append(row["finished_ns"] - previous_begin)
            previous_begin = begin
            previous_end = row["finished_ns"]
    completions.append(observed_exit)
    window_gaps.append(observed_exit - previous_begin)
    return {
        "stalled_slots": [row["slot"] for row in stalled],
        "bypass_slots": bypass,
        "after_exit_slots": [
            row["slot"] for row in complete if row["finished_ns"] > observed_exit
        ],
        "invalid_slots": [
            row["slot"] for row in rows if row.get("issues") or "error" in row
        ],
        "bounded_slots": [row["slot"] for row in bounded],
        "completion_gap_ns": max(right - left for left, right in pairwise(completions)),
        "conservative_window_gap_ns": max(window_gaps),
        "maximum_bounded_pair_bytes": max(
            (row["bytes"] for row in bounded), default=None
        ),
        "raw_complete_in_job_maximum_bytes": max(
            (row["bytes"] for row in in_job), default=None
        ),
    }


def classify_arms(serial, overlap):
    if not serial["stalled_slots"]:
        return "inconclusive-no-serial-stall"
    if not overlap["stalled_slots"]:
        return "inconclusive-no-overlap-stall"
    if not overlap["bypass_slots"]:
        return "no-independent-return-observed"
    return "independent-complete-return-observed"


def prepare(options):
    """Verify release binaries, immutable prior flags and native E9 source bytes."""
    if sha256(TARGETS_PATH) != SPEC_SHA256:
        raise ValueError("frozen target hash does not match the archived run")
    campaign = Campaign.load(TARGETS_PATH)
    records, source = corpus(ROOT, campaign, "E9")
    frames = verify_frames(options.input_root, records, 9)
    plans = {}
    for runtime, binary in (
        ("wgpu-vulkan", options.vulkan_cli),
        ("cuda", options.cuda_cli),
    ):
        archive_name, archive_hash, member, expected_hash = BUILDS[runtime]
        binary = binary.resolve(strict=True)
        if not os.access(binary, os.X_OK) or sha256(binary) != expected_hash:
            raise ValueError(f"unexpected binary for {runtime}: {binary}")
        archive_path = EVIDENCE / archive_name
        if sha256(archive_path) != archive_hash:
            raise ValueError(f"archived measurement hash changed for {runtime}")
        with tarfile.open(archive_path) as archive:
            prior = json.load(archive.extractfile(member))
            report_name = "/".join(member.split("/")[:2]) + "/report.json"
            report = json.load(archive.extractfile(report_name))
        identity = report["targets"]["candidate"]
        if (
            identity["commit"] != RELEASE
            or identity["lock_sha256"] != LOCK_SHA256
            or identity["binary_sha256"] != expected_hash
        ):
            raise ValueError(f"archived build identity changed for {runtime}")
        old = prior["argv"]
        output = old.index("--output")
        if old[1] != "--input" or [Path(item).name for item in old[2:output]] != [
            frame.name for frame in frames
        ]:
            raise ValueError(f"archived ordered frame arguments changed for {runtime}")
        plans[runtime] = {
            "binary": str(binary),
            "binary_sha256": expected_hash,
            "argv_suffix": old[output + 2 :],
            "archived_environment": prior["environment"],
            "archived_output": prior["output"],
            "archived_affinity": report["hardware"]["cpu_affinity"],
            "archive": str(archive_path),
            "archive_sha256": archive_hash,
            "sample_path": member,
        }
    return {
        "release": RELEASE,
        "cargo_lock_sha256": LOCK_SHA256,
        "performance_targets_sha256": SPEC_SHA256,
        "input_root": str(options.input_root.resolve()),
        "input_source": source,
        "inputs": records,
        "frames": list(map(str, frames)),
        "plans": plans,
    }


def measure_arm(argv, env, directory, provider, workers):
    """Direct spawn, separately wait for exit, then drain bounded diagnostic lanes."""
    ready = threading.Event()
    stop = threading.Event()
    deadline_hit = threading.Event()
    dispatches = []
    started_calls = [[] for _ in range(workers)]
    lanes = []
    coordinator = None
    job = None
    watchdog = None
    result = {
        "workers": workers,
        "argv": argv,
        "environment": env,
        "scratch": str(directory),
    }

    def dispatch():
        ready.wait()
        if job is not None:
            schedule(lanes, job.pid, launch, stop, dispatches)

    def terminate():
        if not stop.is_set():
            deadline_hit.set()
            _signal_group(job.pid, signal.SIGKILL)

    with (
        (directory / "stdout.txt").open("xb") as stdout,
        (directory / "stderr.txt").open("xb") as stderr,
    ):
        try:
            for lane, live in enumerate(started_calls):
                view = PairDevice(provider)
                lanes.append(
                    PairLane(
                        partial(
                            capture_pair,
                            lane,
                            read=view.read,
                            identify=pid_identity,
                            clock=time.monotonic_ns,
                            publish=live.append,
                        )
                    )
                )
            if not all(lane.ready.wait(DRAIN_LIMIT) for lane in lanes):
                raise RuntimeError("a diagnostic worker did not prearm")
            coordinator = threading.Thread(target=dispatch, daemon=True)
            coordinator.start()
            launch = time.monotonic_ns()
            job = subprocess.Popen(
                argv,
                cwd=directory,
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            result.update(
                launch_ns=launch,
                job_pid=job.pid,
                initial_job_identity=pid_identity(job.pid),
            )
            ready.set()
            remaining = max(0, JOB_LIMIT - (time.monotonic_ns() - launch) / 1e9)
            watchdog = threading.Timer(remaining, terminate)
            watchdog.daemon = True
            watchdog.start()
            _, status, _ = os.wait4(job.pid, 0)
            result["exit_observed_ns"] = time.monotonic_ns()
            stop.set()
            job.returncode = os.waitstatus_to_exitcode(status)
            result["returncode"] = job.returncode
        except (OSError, RuntimeError, ValueError) as error:
            result["launcher_error"] = str(error)
        except KeyboardInterrupt:
            result["launcher_error"] = "diagnostic interrupted"
        finally:
            stop.set()
            ready.set()
            if watchdog is not None:
                watchdog.cancel()
                watchdog.join()
            if job is not None and job.poll() is None:
                _signal_group(job.pid, signal.SIGKILL)
                job.wait()
            drain_deadline = time.monotonic() + DRAIN_LIMIT
            if coordinator is not None:
                coordinator.join(max(0, drain_deadline - time.monotonic()))
            coordinator_done = coordinator is None or not coordinator.is_alive()
            for lane in lanes:
                if coordinator_done and lane.ready.wait(
                    max(0, drain_deadline - time.monotonic())
                ):
                    lane.close()
                    lane.thread.join(max(0, drain_deadline - time.monotonic()))

    result["drained"] = coordinator_done and all(
        not lane.thread.is_alive() for lane in lanes
    )
    result["deadline_hit"] = deadline_hit.is_set()
    result["dispatches"] = dispatches.copy()
    result["started_calls_by_lane"] = [live.copy() for live in started_calls]
    result["inflight"] = [lane.active for lane in lanes]
    rows = sorted(
        (row for lane in lanes for row in lane.receipts.copy()),
        key=lambda row: row["slot"],
    )
    result["pairs"] = rows
    result["stdout"] = (directory / "stdout.txt").read_text(errors="replace")
    result["stderr"] = (directory / "stderr.txt").read_text(errors="replace")
    if "exit_observed_ns" in result:
        result["interval_ns"] = result["exit_observed_ns"] - result["launch_ns"]
        result["analysis"] = describe_arm(
            rows, result["launch_ns"], result["exit_observed_ns"]
        )
    if job is not None:
        try:
            remaining_pids, _ = _session_memory(job.pid)
            if remaining_pids:
                _signal_group(job.pid, signal.SIGKILL)
                result["unexpected_session_members_after_exit"] = sorted(remaining_pids)
        except OSError as error:
            result["launcher_error"] = str(error)
    return result


def run_arm(runtime, workers, prepared, directory, provider):
    plan = prepared["plans"][runtime]
    env = plan["archived_environment"].copy()
    for key, name in CACHE_DIRS.items():
        path = directory / name
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    events = directory / "events.jsonl"
    env["CONFORMANCE_EVENTS_PATH"] = str(events)
    output = directory / "complete.tif"
    argv = [
        plan["binary"],
        "--input",
        *prepared["frames"],
        "--output",
        str(output),
        *plan["argv_suffix"],
    ]
    result = measure_arm(argv, env, directory, provider, workers)
    if events.exists():
        result["events_jsonl"] = events.read_text(errors="replace")
    try:
        if not result["drained"]:
            raise ValueError("native workers failed to drain; no further arm can start")
        if (
            result.get("returncode") != 0
            or result["deadline_hit"]
            or result.get("unexpected_session_members_after_exit")
            or result.get("launcher_error")
        ):
            raise ValueError("measured CLI did not exit cleanly")
        image = verify_output(output, [339, 512, 3])
        result["image"] = image
        for key in ("pixel_sha256", "shape", "dtype"):
            if image[key] != plan["archived_output"][key]:
                raise ValueError(f"frozen E9 image check differed for {key}")
        completed = _assert_completion(events, "gpu", runtime, DEVICE, PCI)
        if completed.get("physical_gpu") is not True or completed.get(
            "fallback_reason"
        ):
            raise ValueError("physical device provenance was incomplete")
        if not result["analysis"]["raw_complete_in_job_maximum_bytes"]:
            raise ValueError(
                "no attributable positive device usage in a completed pair"
            )
        result["diagnostic_image_and_device_verified"] = True
    except (OSError, RuntimeError, ValueError) as error:
        result["diagnostic_image_and_device_verified"] = False
        result["failure"] = str(error)
    return result


def execute(prepared, output):
    """Hold the existing common lease through shutdown and retain each raw arm."""
    affinity = sorted(os.sched_getaffinity(0))
    if any(
        plan["archived_affinity"] != affinity for plan in prepared["plans"].values()
    ):
        raise ValueError("current affinity differs from the archived matched runs")
    report = {
        "scope": "instrumented E9 Vulkan and CUDA diagnostics only",
        "qualification_credit": False,
        "started_at_unix_ns": time.time_ns(),
        "cpu_affinity": affinity,
        "starting_provenance": prepared,
        "arms": {},
        "comparisons": {},
        "status": "starting",
    }
    with _campaign_lock():
        if output.exists():
            raise ValueError(f"refusing to overwrite receipt {output}")
        _write(output, report)
        provider = None
        try:
            gpu = _gpu_state(UUID)
            if (
                gpu["name"] != DEVICE
                or _pci_id(gpu["pci.bus_id"]) != _pci_id(PCI)
                or gpu["driver_version"] != DRIVER
            ):
                raise ValueError(
                    f"physical driver or device differs from the archived runs: {gpu}"
                )
            report["gpu_before"] = gpu
            provider = NvidiaMemory(UUID)
            for runtime in prepared["plans"]:
                arms = report["arms"][runtime] = {}
                for workers in (1, 2):
                    label = "serial" if workers == 1 else "overlap"
                    with tempfile.TemporaryDirectory(
                        prefix=f"pancake-e9-{runtime}-{label}-"
                    ) as scratch:
                        arm = run_arm(
                            runtime, workers, prepared, Path(scratch), provider
                        )
                        arms[label] = arm
                        if not arm["drained"]:
                            report["status"] = "aborted-native-call-still-inflight"
                            report["lease_released"] = False
                            _write(output, report)
                            # Do not close the driver or unwind the flock while its calls are live.
                            os._exit(2)
                        _write(output, report)
                    if not arm["diagnostic_image_and_device_verified"]:
                        raise ValueError(f"invalid diagnostic arm {runtime}/{label}")
                report["comparisons"][runtime] = classify_arms(
                    arms["serial"]["analysis"], arms["overlap"]["analysis"]
                )
            verify_frames(Path(prepared["input_root"]), prepared["inputs"], 9)
            for plan in prepared["plans"].values():
                if sha256(Path(plan["binary"])) != plan["binary_sha256"]:
                    raise ValueError(
                        "input or executable changed during the diagnostic"
                    )
            report["inputs_and_binaries_unchanged"] = True
            report["status"] = "complete-diagnostic"
        except (
            OSError,
            RuntimeError,
            ValueError,
            subprocess.CalledProcessError,
        ) as error:
            report["status"] = "aborted"
            report["error"] = str(error)
        except KeyboardInterrupt:
            report["status"] = "aborted"
            report["error"] = "diagnostic interrupted"
        finally:
            if provider is not None:
                report["device_close_pending"] = True
                _write(output, report)
                try:
                    provider.close()
                except (OSError, ValueError) as error:
                    report["status"] = "aborted"
                    report["close_error"] = str(error)
                report["device_close_pending"] = False
            report["finished_at_unix_ns"] = time.time_ns()
            _write(output, report)
    report["lease_released"] = True
    _write(output, report)
    return 0 if report["status"] == "complete-diagnostic" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--vulkan-cli", type=Path, required=True)
    parser.add_argument("--cuda-cli", type=Path, required=True)
    parser.add_argument("--run-diagnostic", type=Path, metavar="FRESH_RECEIPT")
    options = parser.parse_args(argv)
    try:
        prepared = prepare(options)
        if options.run_diagnostic is not None:
            handler = signal.signal(signal.SIGTERM, signal.default_int_handler)
            try:
                return execute(prepared, options.run_diagnostic.resolve())
            finally:
                signal.signal(signal.SIGTERM, handler)
        print(json.dumps(prepared, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
