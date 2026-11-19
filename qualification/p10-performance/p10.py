"""Execute frozen completed-job pairs against the actual target CLIs on Linux."""

import argparse
import fcntl
import gzip
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from contextlib import ExitStack, contextmanager
from importlib import metadata
from pathlib import Path

from pancake_conformance.target import TargetSpec
from protocol import (
    Campaign,
    corpus,
    evaluate_latency,
    merge_latency_samples,
    pixel_metrics,
    profile_result,
    sha256,
    verify_frames,
    verify_output,
)
from resources import (
    DEFAULT_RSS_SAMPLE_INTERVAL_MS,
    RSS_SAMPLE_INTERVALS_MS,
    NvidiaMemory,
    measure,
)

ROOT = Path(__file__).resolve().parents[2]
TARGETS_PATH = ROOT / "pancake/docs/performance-targets.json"
ADAPTERS = ROOT / "pancake-conformance/src/pancake_conformance/adapters"
REFERENCE = ADAPTERS / "chimpstackr_reference/chimpstackr.toml"
R50_REFERENCE = ADAPTERS / "pancake/cr3_reference.py"
E9_REFERENCE = ADAPTERS / "pancake/e9_reference.py"
E9_PROFILES = {"E9.exposure_fusion.cpu", "E9.exposure_fusion.gpu"}
CANDIDATE = ADAPTERS / "pancake/pancake.toml"
RUNTIMES = {"cpu": None, "wgpu-vulkan": "wgpu", "cuda": "cuda"}


def _output(args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def _git(cwd, *args):
    return _output(["git", *args], cwd)


def _require_clean(cwd, *paths):
    status = _git(
        cwd, "status", "--porcelain", "--untracked-files=normal", "--", *paths
    )
    if status:
        raise ValueError(
            f"dirty application or descriptor sources under {cwd}:\n{status}"
        )


@contextmanager
def _campaign_lock():
    """Prevent overlapping CLI or native benchmarks in this Git repository."""
    git_dir = Path(
        _git(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir")
    )
    with (git_dir / "pancake-performance.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _snapshot(target, lock):
    return {
        "commit": _git(target.root, "rev-parse", "HEAD"),
        "lock_sha256": sha256(lock),
        "descriptor_sha256": sha256(target.descriptor),
    }


def _write(path, payload):
    temporary = path.with_suffix(path.suffix + ".writing")
    with temporary.open("x") as stream:
        stream.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def _candidate_binary(target, component="cli"):
    executable = target.command(component)[0]
    return (target.root / executable).resolve(strict=True)


def prepare_candidate(options):
    """Build a locked release binary and retain exact source and artifact provenance."""
    output = options.receipt.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f"build receipt exists: {output}")
    target = TargetSpec.load(CANDIDATE)
    _require_clean(ROOT, "pancake", str(CANDIDATE))
    lock = target.root / "Cargo.lock"
    expected = _snapshot(target, lock)
    build = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--bin",
        f"pancake-{options.component}",
    ]
    if options.features:
        build.extend(("--features", options.features))
    build_env = dict(os.environ, CARGO_TARGET_DIR=str(target.root / "target"))
    subprocess.run(build, cwd=target.root, env=build_env, check=True)
    executable = _candidate_binary(target, options.component)
    _require_clean(ROOT, "pancake", str(CANDIDATE))
    if _snapshot(target, lock) != expected:
        raise ValueError("candidate sources changed during build")
    receipt = {
        **expected,
        "build": build,
        "component": options.component,
        "executable": str(executable),
        "binary_sha256": sha256(executable),
        "rustc": _output(["rustc", "-vV"], target.root),
        "cargo": _output(["cargo", "-V"], target.root),
        "build_environment": {
            key: value
            for key, value in build_env.items()
            if key in ("CARGO_TARGET_DIR", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS")
        },
    }
    _write(output, receipt)


def _reference_launch(target, interpreter, profile_key):
    """Bind the scoped reference launcher for the frozen R50 or E9 profile."""
    if profile_key in E9_PROFILES:
        return {
            "command": [str(interpreter), str(E9_REFERENCE)],
            "exposure_combiner": {
                "path": str(E9_REFERENCE.relative_to(ROOT)),
                "sha256": sha256(E9_REFERENCE),
                "policy": "equal-final-batch-mean-v1",
            },
        }
    if profile_key.partition(".")[0] != "R50":
        return {"command": target.command("cli", python=interpreter)}
    return {
        "command": [str(interpreter), str(R50_REFERENCE)],
        "raw_ingest": {
            "path": str(R50_REFERENCE.relative_to(ROOT)),
            "sha256": sha256(R50_REFERENCE),
        },
    }


def _prepared_targets(options, campaign):
    reference, candidate = (TargetSpec.load(path) for path in (REFERENCE, CANDIDATE))
    lock_pin = campaign.raw["reference"]
    _require_clean(
        ROOT, "pancake", str(CANDIDATE), str(REFERENCE), lock_pin["runtime_lock_path"]
    )
    if options.profile.partition(".")[0] == "R50":
        _require_clean(ROOT, str(R50_REFERENCE))
    if options.profile in E9_PROFILES:
        _require_clean(ROOT, str(E9_REFERENCE))
    _require_clean(reference.root)
    expected_reference = _snapshot(reference, ROOT / lock_pin["runtime_lock_path"])
    pinned_reference = {
        "commit": lock_pin["source_commit"],
        "lock_sha256": lock_pin["runtime_lock_sha256"],
        "descriptor_sha256": lock_pin["descriptor_sha256"],
    }
    if expected_reference != pinned_reference:
        raise ValueError(
            "reference source, lock or descriptor differs from the frozen protocol"
        )
    expected_candidate = _snapshot(candidate, candidate.root / "Cargo.lock")
    executable = _candidate_binary(candidate)
    expected_candidate.update(
        {"executable": str(executable), "binary_sha256": sha256(executable)}
    )
    receipt = json.loads(options.build_receipt.read_text())
    if {key: receipt.get(key) for key in expected_candidate} != expected_candidate:
        raise ValueError(
            "candidate binary, source, lock or descriptor differs from its release build receipt"
        )
    reference_python = REFERENCE.parent / ".venv/bin/python"
    if not reference_python.is_file():
        raise ValueError(
            "reference environment missing; run uv sync --frozen in the pinned reference project"
        )
    environment = _output(
        ["uv", "pip", "freeze", "--python", str(reference_python)], REFERENCE.parent
    )
    expected_reference.update(
        {
            "python": str(reference_python),
            "python_sha256": sha256(reference_python),
            **_reference_launch(reference, reference_python, options.profile),
            "packages": environment.splitlines(),
        }
    )
    return (
        {"reference": reference, "candidate": candidate},
        {"reference": expected_reference, "candidate": receipt},
    )


def _hardware(gpu_uuid):
    if sys.platform != "linux":
        raise ValueError(
            "this runner measures the Linux lane; Mac footprint requires a separate native receipt"
        )
    governors = {}
    for path in Path("/sys/devices/system/cpu/cpufreq").glob(
        "policy*/scaling_governor"
    ):
        governors[str(path.parent)] = path.read_text().strip()
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        platform.processor(),
    )
    record = {
        "cpu": cpu,
        "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "kernel": platform.platform(),
        "os_release": platform.freedesktop_os_release(),
        "frequency_policy": governors,
        "timer": {
            "python": sys.version,
            "clock": vars(time.get_clock_info("monotonic")),
        },
        "memory": "Linux procfs session sum and NVIDIA NVML per PID; sampled, transient peaks can be missed",
        "validator": {
            name: metadata.version(name)
            for name in ("numpy", "tifffile", "imagecodecs")
        },
    }
    if gpu_uuid:
        record["gpu"] = _gpu_state(gpu_uuid)
    return record


def _gpu_state(uuid):
    properties = (
        "uuid",
        "pci.bus_id",
        "name",
        "driver_version",
        "pstate",
        "temperature.gpu",
        "power.draw",
        "power.limit",
        "clocks.gr",
        "clocks.mem",
    )
    result = _output(
        [
            "nvidia-smi",
            "--id",
            uuid,
            "--query-gpu=" + ",".join(properties),
            "--format=csv,noheader,nounits",
        ]
    )
    row = [field.strip() for field in result.split(",")]
    if len(row) != len(properties) or row[0] != uuid:
        raise ValueError(
            f"GPU snapshot did not resolve the requested physical UUID {uuid}"
        )
    return dict(zip(properties, row, strict=True))


def _cpu_thermal_state():
    readings = {}
    for device in Path("/sys/class/hwmon").glob("hwmon*"):
        name = device / "name"
        if name.is_file() and name.read_text().strip() in ("k10temp", "coretemp"):
            readings.update(
                {
                    str(sensor): int(sensor.read_text())
                    for sensor in device.glob("temp*_input")
                }
            )
    return readings


def _compress_trace(directory):
    for name in ("resources.jsonl", "gpu-resources.jsonl"):
        path = directory / name
        if not path.is_file():
            continue
        with (
            path.open("rb") as source,
            gzip.open(path.with_suffix(".jsonl.gz"), "xb") as destination,
        ):
            shutil.copyfileobj(source, destination)
        path.unlink()


def _cache_inventory(cache):
    files = [
        entry
        for entry in cache.rglob("*")
        if entry.is_file() and not entry.is_symlink()
    ]
    return {"files": len(files), "bytes": sum(entry.stat().st_size for entry in files)}


def _environment(
    target,
    cache,
    artifact_dir,
    threads,
    gpu_uuid,
    runtime,
    diagnostics,
    *,
    cuda_library_path=None,
):
    # Start without coverage, injected Python code, arbitrary device overrides or user caches.
    keys = {
        "PATH",
        "LANG",
        "TZ",
        "LD_LIBRARY_PATH",
        "VK_DRIVER_FILES",
        "VK_ICD_FILENAMES",
        "OCL_ICD_VENDORS",
    }
    env = {
        key: value
        for key, value in os.environ.items()
        if key in keys or key.startswith("LC_")
    }
    for label in ("home", "cache", "config", "tmp", "cuda", "nvidia", "numba", "mesa"):
        (cache / label).mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HOME": str(cache / "home"),
            "XDG_CACHE_HOME": str(cache / "cache"),
            "XDG_CONFIG_HOME": str(cache / "config"),
            "TMPDIR": str(cache / "tmp"),
            "CUDA_CACHE_PATH": str(cache / "cuda"),
            "__GL_SHADER_DISK_CACHE_PATH": str(cache / "nvidia"),
            "MESA_SHADER_CACHE_DIR": str(cache / "mesa"),
            "NUMBA_CACHE_DIR": str(cache / "numba"),
            "NUMBA_NUM_THREADS": str(threads),
            "OMP_NUM_THREADS": str(threads),
            "RAYON_NUM_THREADS": str(threads),
            "OPENBLAS_NUM_THREADS": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    for key, value in target.env.items():
        value = str(value).replace("{home}", env["HOME"]).replace("{run}", str(cache))
        env.setdefault(key, value)
    if gpu_uuid:
        env["CUDA_VISIBLE_DEVICES"] = gpu_uuid
    if runtime:
        env["PANCAKE_RUNTIME"] = runtime
    if runtime == "cuda" and cuda_library_path is not None:
        env["LD_LIBRARY_PATH"] = str(cuda_library_path.resolve(strict=True))
    if diagnostics:
        events = artifact_dir / "events.jsonl"
        hooks = target.adapter_hooks()
        if hooks is not None and hasattr(hooks, "environment"):
            env = hooks.environment(target, env, events)
        else:
            env["CONFORMANCE_EVENTS_PATH"] = str(events)
    return env


def _pci_id(address):
    if not isinstance(address, str) or not re.fullmatch(
        r"[0-9a-fA-F]{4,8}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]", address
    ):
        raise ValueError(f"missing or invalid physical PCI address: {address}")
    return tuple(int(part, 16) for part in re.split(r"[:.]", address))


def _assert_completion(events_path, device, runtime, gpu_name, gpu_pci=None):
    events = [
        json.loads(line)
        for line in events_path.read_text().splitlines()
        if line.strip()
    ]
    if any(
        event.get("event") in ("observer_error", "backend_fallback") for event in events
    ):
        raise ValueError(f"backend fallback or observer error in {events_path}")
    completed = [event for event in events if event.get("event") == "stack_complete"]
    if (
        len(completed) != 1
        or completed[0].get("completed") is not True
        or completed[0].get("actual_backend") != device
    ):
        raise ValueError(f"expected one completed {device} stack in {events_path}")
    result = completed[0]
    if runtime is not None and result.get("runtime") != runtime:
        raise ValueError(
            f"completed runtime did not match {runtime}: {result.get('runtime')}"
        )
    if gpu_name and gpu_name.casefold() not in str(result.get("device", "")).casefold():
        raise ValueError(
            f"completed physical GPU did not match {gpu_name}: {result.get('device')}"
        )
    if gpu_pci is not None and _pci_id(result.get("device_pci_address")) != _pci_id(
        gpu_pci
    ):
        raise ValueError(
            f"completed physical PCI address did not match {gpu_pci}: {result.get('device_pci_address')}"
        )
    return result


def _assert_primary_gpu(record, case):
    if not record["observed_peak_gpu_bytes"]:
        raise ValueError(
            f"no attributed process residency on the selected physical GPU: {case}"
        )
    for filename in ("stdout.txt", "stderr.txt"):
        output = (case / filename).read_text(errors="replace").casefold()
        fallback = ("falling back to the cpu", "no usable gpu", "not enough gpu memory")
        if any(message in output for message in fallback):
            raise ValueError(
                f"forced GPU execution reported CPU fallback: {case / filename}"
            )


def _opencl_preflight(args, target, identity, hardware, directory):
    cache = directory / "cache" / "reference" / "hardware-probe"
    env = _environment(target, cache, directory, args.threads, None, None, False)
    argv = [
        identity["python"],
        "-c",
        'import runpy, sys; runpy.run_path(sys.argv.pop(1), run_name="__main__")',
        str(Path(__file__).with_name("physical.py")),
        str(args.reference_gpu_index),
    ]
    result = subprocess.run(
        argv,
        cwd=target.root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    _write(
        directory / "opencl-preflight.json",
        {
            "argv": argv,
            "cwd": str(target.root),
            "environment": env,
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    result.check_returncode()
    selected = json.loads(result.stdout)
    if selected["uuid"] != hardware["uuid"]:
        raise ValueError(
            f"reference OpenCL index resolves a different physical GPU: {selected['uuid']} != {hardware['uuid']}"
        )
    return selected


def _run_sample(
    profile,
    pair,
    name,
    spec,
    identity,
    args,
    frames,
    bounds,
    directory,
    gpu,
    *,
    rss_sample_interval_ms=DEFAULT_RSS_SAMPLE_INTERVAL_MS,
):
    kind, ordinal, _ = pair
    scope = directory / f"{kind}-{ordinal:02d}"
    case = scope / name
    case.mkdir(parents=True, exist_ok=False)
    cache_name = "warm" if kind in ("warmup", "warm") else f"{kind}-{ordinal:02d}"
    cache = directory / "cache" / name / cache_name
    overrides = {}
    if profile.device == "gpu":
        overrides["gpu_id"] = (
            args.reference_gpu_index
            if name == "reference"
            else args.candidate_gpu_index
        )
    settings = profile.options | overrides
    path = case / "complete.tif"
    runtime = RUNTIMES[args.runtime] if name == "candidate" else None
    env = _environment(
        spec,
        cache,
        case,
        args.threads,
        args.gpu_uuid,
        runtime,
        kind == "diagnostic",
        cuda_library_path=args.cuda_library_path,
    )
    command = (
        identity["command"]
        if name == "reference"
        else [identity["executable"], *spec.command("cli")[1:]]
    )
    argv = [*command, *spec.stack_arguments(frames, path, settings)]
    record = {
        "kind": kind,
        "number": ordinal,
        "target": name,
        "argv": argv,
        "cwd": str(spec.root),
        "environment": env,
        "rss_sampler_cpu": args.rss_sampler_cpu,
        "sample_interval_ns": rss_sample_interval_ms * 1_000_000,
        "gpu_before": _gpu_state(args.gpu_uuid) if gpu else None,
        "cpu_temperature_before_millidegrees": _cpu_thermal_state(),
        "cache_before": _cache_inventory(cache),
        "valid": False,
    }
    _write(case / "launch.json", record)
    try:
        record.update(
            measure(
                argv,
                cwd=spec.root,
                env=env,
                directory=case,
                timeout=args.timeout,
                gpu=gpu,
                rss_sampler_cpu=args.rss_sampler_cpu,
                rss_sample_interval_ms=rss_sample_interval_ms,
            )
        )
        record["gpu_after"] = _gpu_state(args.gpu_uuid) if gpu else None
        record["cpu_temperature_after_millidegrees"] = _cpu_thermal_state()
        record["cache_after"] = _cache_inventory(cache)
        if record["returncode"] or record["timed_out"]:
            raise ValueError(f"job did not exit successfully in {case}")
        if record["resource_errors"]:
            raise ValueError(
                f"job resource observations failed in {case}: {record['resource_errors']}"
            )
        if gpu:
            _assert_primary_gpu(record, case)
        record["output"] = verify_output(path, bounds)
        if kind == "diagnostic":
            record["completion"] = _assert_completion(
                case / "events.jsonl",
                profile.device,
                args.runtime if name == "candidate" else None,
                record["gpu_before"]["name"] if gpu else None,
                record["gpu_before"]["pci.bus_id"]
                if gpu and name == "candidate"
                else None,
            )
        record["valid"] = True
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        record["invalid_reason"] = str(error)
    finally:
        _write(case / "sample.json", record)
        _compress_trace(case)
    return record, path


def _cleanup_outputs(directory, result, *, keep_review_images):
    """Keep requested review images from a complete, source-verified profile."""
    outputs = set(directory.glob("*/*/complete.tif"))
    warm_pair = {
        directory / "warm-01" / target / "complete.tif"
        for target in ("candidate", "reference")
    }
    retain = (
        keep_review_images
        and "gates" in result
        and result.get("inputs_unchanged") is True
        and warm_pair <= outputs
    )
    remove = sorted(outputs - warm_pair if retain else outputs)
    for path in remove:
        path.unlink()
    return {
        "removed_partial_or_diagnostic_outputs": [
            str(path.relative_to(directory)) for path in remove
        ],
        "retained_review_pair": retain,
    }


def run_profile(args):
    device = "cpu" if args.runtime == "cpu" else "gpu"
    interval_ms = args.rss_sample_interval_ms
    if device != "cpu" and interval_ms != DEFAULT_RSS_SAMPLE_INTERVAL_MS:
        raise ValueError("--rss-sample-interval-ms overrides are for CPU profiles only")
    campaign = Campaign.load(TARGETS_PATH)
    if bool(args.gpu_uuid) != (device == "gpu") or (
        args.gpu_uuid and not args.gpu_uuid.startswith("GPU-")
    ):
        raise ValueError(
            "an explicit physical GPU UUID is required only for a GPU profile"
        )
    if args.runtime == "cuda" and args.candidate_gpu_index != 0:
        raise ValueError(
            "the explicitly selected CUDA UUID is device index 0 inside the benchmark process"
        )
    if args.cuda_library_path is not None and (
        args.runtime != "cuda" or not args.cuda_library_path.is_dir()
    ):
        raise ValueError(
            "--cuda-library-path requires a directory and the cuda runtime"
        )
    if sys.platform != "linux":
        raise ValueError("Linux process counters required for this campaign")
    job_affinity = os.sched_getaffinity(0)
    if args.threads != len(job_affinity) or args.timeout <= 0:
        raise ValueError(
            "--threads must match the common CPU affinity width and timeout must be positive"
        )
    if args.rss_sampler_cpu is not None and (
        args.rss_sampler_cpu < 0 or args.rss_sampler_cpu in job_affinity
    ):
        raise ValueError("--rss-sampler-cpu must be outside the common job affinity")
    profile = next(
        (item for item in campaign.profiles(device) if item.key == args.profile), None
    )
    if profile is None:
        raise ValueError(f"unknown frozen profile for {device}: {args.profile}")
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": 1,
        "status": "pending",
        "profile": profile.key,
        "candidate_runtime": args.runtime,
        "reference_runtime": "opencl" if device == "gpu" else "cpu",
        "settings": profile.options,
        "sample_interval_ns": interval_ms * 1_000_000,
        "performance_targets_sha256": sha256(TARGETS_PATH),
        "samples": [],
        "pixel_comparisons": [],
        "diagnostics": [],
        "started_at_unix_ns": time.time_ns(),
    }

    verified_corpus = None
    try:
        with _campaign_lock(), ExitStack() as context:
            specs, identities = _prepared_targets(args, campaign)
            hardware = _hardware(args.gpu_uuid)
            records, source = corpus(ROOT, campaign, profile.workload)
            workload = next(
                item
                for item in campaign.raw["workloads"]
                if item["id"] == profile.workload
            )
            frames = verify_frames(args.input_root, records, workload["frames"])
            verified_corpus = (records, workload["frames"])
            # Both public CLIs sort inputs. The P0 selection must yield this exact same order.
            if frames != sorted(frames, key=str):
                raise ValueError(
                    "pinned selection does not match public CLI input ordering"
                )
            first = records[0]
            bounds = first.get("shape", first.get("decoded_shape"))
            if profile.workload == "R50":
                capture = json.loads(
                    _output(
                        [
                            *identities["reference"]["command"],
                            "--cr3-geometry",
                            str(frames[0]),
                        ],
                        specs["reference"].root,
                    )
                )
                bounds = capture["oriented_shape_hwc"]
                result["reference_raw_source_geometry"] = capture
            gpu = None
            if args.gpu_uuid:
                hardware["reference_opencl"] = _opencl_preflight(
                    args,
                    specs["reference"],
                    identities["reference"],
                    hardware["gpu"],
                    directory,
                )
                gpu = NvidiaMemory(args.gpu_uuid)
                context.callback(gpu.close)
            result.update(
                {
                    "targets": identities,
                    "hardware": hardware,
                    "corpus": source,
                    "frames": records,
                    "input_root": str(args.input_root.resolve()),
                }
            )
            _write(directory / "report.json", result)
            pair_paths = {}
            for pair in campaign.schedule():
                kind, ordinal, target = pair
                record, path = _run_sample(
                    profile,
                    pair,
                    target,
                    specs[target],
                    identities[target],
                    args,
                    frames,
                    bounds,
                    directory,
                    gpu,
                    rss_sample_interval_ms=interval_ms,
                )
                result["samples"].append(record)
                _write(directory / "report.json", result)
                if not record["valid"]:
                    raise ValueError(record["invalid_reason"])
                pair_paths[target] = path
                if len(pair_paths) == 2:
                    comparison = pixel_metrics(
                        pair_paths["reference"], pair_paths["candidate"], bounds
                    )
                    comparison.update({"kind": kind, "number": ordinal})
                    result["pixel_comparisons"].append(comparison)
                    if not (
                        args.keep_review_images and kind == "warm" and ordinal == 1
                    ):
                        for path in pair_paths.values():
                            path.unlink()
                    pair_paths.clear()
            for target in ("reference", "candidate"):
                pair = ("diagnostic", 1, target)
                record, path = _run_sample(
                    profile,
                    pair,
                    target,
                    specs[target],
                    identities[target],
                    args,
                    frames,
                    bounds,
                    directory,
                    gpu,
                    rss_sample_interval_ms=interval_ms,
                )
                result["diagnostics"].append(record)
                if not record["valid"]:
                    raise ValueError(record["invalid_reason"])
                matching_warm = [
                    sample
                    for sample in result["samples"]
                    if sample["kind"] == "warm" and sample["target"] == target
                ]
                record["matching_warm_pixel_hashes"] = sum(
                    sample["output"]["pixel_sha256"] == record["output"]["pixel_sha256"]
                    for sample in matching_warm
                )
                path.unlink()
            _, final_identities = _prepared_targets(args, campaign)
            if final_identities != identities:
                raise ValueError("target provenance changed during benchmark")
            result.update(profile_result(campaign, device, result["samples"]))
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        result.update({"status": "fail", "invalid_reason": str(error)})
    finally:
        if verified_corpus is not None:
            try:
                verify_frames(args.input_root, *verified_corpus)
                result["inputs_unchanged"] = True
            except (OSError, ValueError) as error:
                result.update(
                    {
                        "status": "fail",
                        "inputs_unchanged": False,
                        "input_verification_error": str(error),
                    }
                )
        result["cleanup"] = _cleanup_outputs(
            directory, result, keep_review_images=args.keep_review_images
        )
        cache = directory / "cache"
        try:
            if cache.exists():
                shutil.rmtree(cache)
        except OSError as error:
            result.update({"status": "fail", "cache_cleanup_error": str(error)})
        result["finished_at_unix_ns"] = time.time_ns()
        _write(directory / "report.json", result)
    return 1 if result["status"] == "fail" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    matrix = sub.add_parser(
        "matrix", help="List frozen workloads, methods and all explicit Linux runtimes"
    )
    matrix.add_argument("--runtime", choices=RUNTIMES, required=True)
    candidate = sub.add_parser(
        "prepare-candidate", help="Build and fingerprint the actual release CLI"
    )
    candidate.add_argument("--receipt", type=Path, required=True)
    candidate.add_argument("--features")
    candidate.add_argument("--component", choices=("cli", "gui"), default="cli")
    run = sub.add_parser(
        "run",
        help="Run one serialized profile and its two independent backend diagnostics",
    )
    run.add_argument(
        "--profile", required=True, help="Use a profile ID from the matrix command"
    )
    run.add_argument("--runtime", choices=RUNTIMES, required=True)
    run.add_argument("--input-root", type=Path, required=True)
    run.add_argument("--build-receipt", type=Path, required=True)
    run.add_argument(
        "--output", type=Path, required=True, help="Fresh artifact directory"
    )
    run.add_argument(
        "--threads",
        type=int,
        required=True,
        help="Explicit OMP/Numba/Rayon thread limit",
    )
    run.add_argument(
        "--timeout", type=float, required=True, help="Per-job deadline in seconds"
    )
    run.add_argument(
        "--rss-sampler-cpu",
        type=int,
        help="Pin only the RSS sampler to a logical CPU outside the common job affinity",
    )
    run.add_argument(
        "--rss-sample-interval-ms",
        type=int,
        choices=RSS_SAMPLE_INTERVALS_MS,
        default=DEFAULT_RSS_SAMPLE_INTERVAL_MS,
        help="Nominal RSS interval for CPU profiles in ms (default: %(default)s)",
    )
    run.add_argument("--gpu-uuid")
    run.add_argument("--reference-gpu-index", type=int, default=0)
    run.add_argument("--candidate-gpu-index", type=int, default=0)
    run.add_argument(
        "--cuda-library-path",
        type=Path,
        help="Toolkit library directory for the CUDA candidate child",
    )
    run.add_argument(
        "--keep-review-images",
        action="store_true",
        help="Retain only the first warm pair for visual review",
    )
    latency = sub.add_parser(
        "latency", help="Reduce independently collected native event timestamp records"
    )
    latency.add_argument(
        "input", nargs="+", type=Path, help="Verified native capture receipts"
    )
    args = parser.parse_args()
    try:
        if args.operation == "matrix":
            device = "cpu" if args.runtime == "cpu" else "gpu"
            print(
                json.dumps(
                    [
                        {
                            "profile": profile.key,
                            "candidate_runtime": args.runtime,
                            "settings": profile.options,
                        }
                        for profile in Campaign.load(TARGETS_PATH).profiles(device)
                    ],
                    indent=2,
                )
            )
            return 0
        if args.operation == "prepare-candidate":
            prepare_candidate(args)
            return 0
        if args.operation == "latency":
            captures = [json.loads(path.read_text()) for path in args.input]
            target_hash = sha256(TARGETS_PATH)
            if any(
                capture.get("performance_targets_sha256") != target_hash
                for capture in captures
            ):
                raise ValueError(
                    "native capture target specification differs from the frozen version"
                )
            viewer, lifecycle, workloads = merge_latency_samples(captures)
            result = evaluate_latency(Campaign.load(TARGETS_PATH), viewer, lifecycle)
            profile_complete = "lifecycle" in workloads and bool(
                {"R50", "D150", "E9"}.intersection(workloads)
            )
            result["native_lifecycle_workloads"] = {
                "status": "pass" if profile_complete else "pending",
                "workloads": workloads,
            }
            print(json.dumps(result, indent=2))
            passed = all(
                entry["status"] == "pass"
                for collection in (result["viewer"], result["lifecycle"])
                for entry in collection.values()
            )
            return 0 if profile_complete and passed else 1
        return run_profile(args)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    sys.exit(main())
