"""Scenario operations expressed only through external application boundaries."""
import json
import hashlib
import glob
import os
from pathlib import Path

from .process import ProcessRunner


class CaseContext:
    def __init__(self, target, directory, *, environment=None):
        self.target = target
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.notes = {}
        self.outputs = {}
        self._environment = dict(environment or os.environ)
        self._calls = 0

    def note(self, key, value):
        self.notes[key] = value

    def state_directory(self, name):
        """Resolve declared mutable state inside this case, without creating it."""
        if name not in self.target.state:
            raise ValueError(f"target has no configured state directory: {name}")
        value = str(self.target.state[name])
        for key, replacement in {"case": self.directory, "home": self.directory / "home"}.items():
            value = value.replace("{" + key + "}", str(replacement.resolve()))
        path = Path(value)
        path = (self.directory / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(self.directory.resolve()):
            raise ValueError("configured state must stay inside the case directory")
        return path

    def record_output(self, path, name=None):
        path = Path(path)
        assert path.is_file(), f"export missing: {path}"
        name = name or path.name
        assert name not in self.outputs, f"duplicate output name: {name}"
        self.outputs[name] = path

    def fixture(self, name):
        from .fixtures import generate_fixture
        fixture = generate_fixture(name, self.directory / "fixtures" / name)
        self.notes.setdefault("fixtures", {})[name] = {
            "metadata": fixture.metadata,
            "inputs": [{"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                       for path in fixture.paths],
        }
        return fixture

    def environment(self, call_dir):
        env = dict(self._environment)
        home = self.directory / "home"
        home.mkdir(exist_ok=True)
        values = {"case": str(self.directory), "home": str(home), "target": str(self.target.root),
                  "run": str(self.directory.parent.parent)}
        env.update({"HOME": str(home), "XDG_CACHE_HOME": str(home / "cache"),
                    "XDG_CONFIG_HOME": str(home / "config"), "TMPDIR": str(self.directory / "tmp")})
        Path(env["TMPDIR"]).mkdir(exist_ok=True)
        for key, value in self.target.env.items():
            value = str(value)
            for name, replacement in values.items():
                value = value.replace("{" + name + "}", replacement)
            env[key] = value
        env["CONFORMANCE_EVENTS_PATH"] = str(call_dir / "events.jsonl")
        # Observation hooks are reference-specific. Scenarios never depend on Python instrumentation.
        if self.target.adapter == "chimpstackr-python":
            from .adapters.chimpstackr import ChimpStackrAdapter
            adapter = ChimpStackrAdapter(self.target.root, __import__("sys").executable)
            env = adapter.environment(env, events_path=call_dir / "events.jsonl")
        return env

    def _call_dir(self):
        self._calls += 1
        directory = self.directory / f"call-{self._calls:02d}"
        directory.mkdir(exist_ok=True)
        return directory

    def command(self, arguments, timeout=120):
        if self._environment.get("CF_VM_GUEST") == "1":
            raise RuntimeError("CLI execution belongs on the host; use assert_cli_parity for guest GUI comparisons")
        directory = self._call_dir()
        result = ProcessRunner().run(self.target.command("cli") + list(map(str, arguments)),
                                     cwd=self.target.root, env=self.environment(directory),
                                     directory=directory, timeout=timeout)
        assert not result.timed_out, f"target timed out after {timeout}s: {result.command}"
        events = directory / "events.jsonl"
        if events.exists():
            result.diagnostics = {"events": [json.loads(line) for line in events.read_text().splitlines() if line.strip()]}
        return result

    def probe(self, operation, *, arrays=None, options=None, timeout=120):
        """Run a language-neutral component hook as a separate host process."""
        import re
        import numpy as np
        from .probes import encode_array, portable_options, ProbeResult
        if self._environment.get("CF_VM_GUEST") == "1":
            raise RuntimeError("component execution belongs on the host")
        directory = self._call_dir()
        wire = {name: encode_array(value) for name, value in (arrays or {}).items()}
        request = {"schema_version": 1, "operation": operation, "arrays": wire, "options": options or {}}
        request_path, response_path = directory / "request.json", directory / "response.json"
        request_path.write_text(json.dumps(request, allow_nan=False))
        self.notes.setdefault("requests", []).append({
            "operation": operation, "options": portable_options(options or {}, self.directory), "arrays": {
                name: {"dtype": value["dtype"], "shape": value["shape"],
                       "sha256": hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()}
                for name, value in wire.items()}})
        process = ProcessRunner().run(self.target.command("probe") + ["--request", str(request_path),
                                      "--response", str(response_path)], cwd=self.target.root,
                                      env=self.environment(directory), directory=directory, timeout=timeout)
        assert not process.timed_out, f"component timed out after {timeout}s"
        assert process.returncode == 0, f"component exited {process.returncode}: {process.stderr}"
        assert response_path.is_file(), "component response missing"
        result = ProbeResult.decode(json.loads(response_path.read_text()))
        for name, array in result.arrays.items():
            assert re.fullmatch(r"[a-zA-Z0-9_.-]+", name), "unsafe component array name"
            output = directory / f"{name}.npy"
            np.save(output, array, allow_pickle=False)
            self.record_output(output, f"probe-{self._calls:02d}-{name}")
        self.notes.setdefault("probe_results", []).append({"operation": operation, "ok": result.ok,
                                                          "values": result.values, "error": result.error})
        return result

    def assert_cli_parity(self, output, fixture_or_paths, *, mean_limit, max_limit,
                          note="surface_parity", **options):
        """Compare exported pixels to CLI output, with CLI work kept on the host."""
        from .validators import assert_pixels_close
        if self._environment.get("CF_VM_GUEST") != "1":
            result = self.stack(fixture_or_paths, **options)
            assert result.returncode == 0, result.stderr
            self.note(note, assert_pixels_close(output, result.output, mean_limit=mean_limit, max_limit=max_limit))
            return
        paths = fixture_or_paths.paths if hasattr(fixture_or_paths, "paths") else fixture_or_paths
        def relative(path):
            return Path(path).resolve().relative_to(self.directory.resolve()).as_posix()
        output = Path(output)
        request = {"gui_output": relative(output), "gui_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                   "inputs": [{"path": relative(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()} for path in paths],
                   "options": options, "mean_limit": mean_limit, "max_limit": max_limit, "note": note,
                   "cli_output_name": f"output-{self._calls + 1:02d}.{options.get('output_format', 'png')}"}
        self._calls += 1
        self.notes.setdefault("host_parity_requests", []).append(request)
        self.notes["host_verification_pending"] = True

    def stack(self, fixture_or_paths, **options):
        paths = fixture_or_paths.paths if hasattr(fixture_or_paths, "paths") else fixture_or_paths
        output_format = options.pop("output_format", "png")
        output = self.directory / f"output-{self._calls + 1:02d}.{output_format}"
        defaults = {"device": "cpu", "kernel_size": 3, "pyramid_levels": 4, "scale_factor": 6}
        defaults.update(options)
        inputs = []
        for path in paths:
            path = Path(path)
            matches = [path] if path.is_file() else [Path(p) for p in sorted(glob.glob(str(path))) if Path(p).is_file()]
            if matches:
                inputs.extend({"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in matches)
            else:
                inputs.append({"name": path.name, "sha256": None})
        self.notes.setdefault("requests", []).append({"options": defaults.copy(), "output_format": output_format,
                                                       "input_names": [Path(path).name for path in paths], "inputs": inputs})
        result = self.command(self.target.stack_arguments(paths, output, defaults))
        result.output = output
        if result.returncode == 0 and output.is_file():
            self.record_output(output)
        return result

    def open_ui(self, paths=(), settings_id="default", service_endpoints=None):
        from .macos_ui import open_session
        directory = self._call_dir()
        env = self.environment(directory)
        for name, endpoint in (service_endpoints or {}).items():
            if name not in self.target.services:
                raise ValueError(f"target has no configured service endpoint: {name}")
            env[self.target.services[name]] = str(endpoint)
        return open_session(self.target.command("gui"), cwd=self.target.root, env=env,
                            directory=directory, paths=paths, settings_id=settings_id)
