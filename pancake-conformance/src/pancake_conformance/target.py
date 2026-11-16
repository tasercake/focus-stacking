"""Declarative target boundary; no application imports or toolkit assumptions."""
from dataclasses import dataclass, field, replace
import importlib
from pathlib import Path
import sys
import tomllib


@dataclass(frozen=True)
class TargetSpec:
    name: str
    root: Path
    cli: tuple[str, ...]
    gui: tuple[str, ...] = ()
    adapter: str = ""
    env: dict = field(default_factory=dict)
    stack: dict = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    descriptor: Path | None = None
    gui_vm: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)
    probe: tuple[str, ...] = ()
    services: dict = field(default_factory=dict)
    coverage_scope: Path | None = None
    instrumentation: dict = field(default_factory=dict)
    runtime: dict = field(default_factory=dict)
    fixtures: dict = field(default_factory=dict)
    ui: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        data = tomllib.loads(path.read_text())
        if data.get("schema_version") != 1:
            raise ValueError("unsupported target schema_version (expected 1)")
        for key in ("name", "root", "cli"):
            if not data.get(key):
                raise ValueError(f"target requires {key}")
        root = (path.parent / data["root"]).resolve()
        if not root.is_dir():
            raise ValueError(f"target root does not exist: {root}")
        for kind in ("cli", "gui", "probe"):
            command = data.get(kind, [])
            if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
                raise ValueError(f"{kind} must be an argument array")
        return cls(data["name"], root, tuple(data["cli"]), tuple(data.get("gui", [])),
                   data.get("adapter", ""), data.get("env", {}), data.get("stack", {}),
                   tuple(data.get("capabilities", [])), path, data.get("gui_vm", {}),
                   data.get("state", {}), tuple(data.get("probe", [])), data.get("services", {}),
                   (path.parent / data["coverage_scope"]).resolve() if data.get("coverage_scope") else None,
                   data.get("instrumentation", {}), data.get("runtime", {}), data.get("fixtures", {}), data.get("ui", {}))

    @property
    def coverage_source(self):
        source = self.instrumentation.get("source")
        return (self.root / source).resolve() if source else None

    @property
    def runtime_project(self):
        project = self.runtime.get("project")
        if project is None:
            return None
        if self.descriptor is None:
            raise ValueError("runtime.project requires a target descriptor")
        return (self.descriptor.parent / project).resolve()

    def adapter_hooks(self):
        """Load only the explicitly declared adapter module."""
        if not self.adapter:
            return None
        try:
            return importlib.import_module(self.adapter)
        except ImportError as exc:
            raise RuntimeError(f"Cannot load adapter {self.adapter}: {exc}") from exc

    def with_commands(self, *, cli=None, gui=None):
        for command in (cli, gui):
            if command is not None and (not command or not all(isinstance(x, str) for x in command)):
                raise ValueError("command must be a nonempty argument array")
        return replace(self, cli=tuple(cli) if cli is not None else self.cli,
                       gui=tuple(gui) if gui is not None else self.gui)

    def command(self, kind, **variables):
        values = {"python": sys.executable, "target": str(self.root), **variables}
        tokens = {"cli": self.cli, "gui": self.gui, "probe": self.probe}[kind]
        if not tokens:
            raise ValueError(f"target has no {kind} command")
        result = []
        for token in tokens:
            for key, value in values.items():
                token = token.replace("{" + key + "}", str(value))
            result.append(token)
        return result

    def stack_arguments(self, inputs, output, options):
        args = []
        for token in self.stack.get("input", ["--input", "{inputs}"]):
            args.extend(map(str, inputs)) if token == "{inputs}" else args.append(token)
        for token in self.stack.get("output", ["--output", "{output}"]):
            args.append(str(output) if token == "{output}" else token)
        mapping = self.stack.get("options", {})
        for key, value in options.items():
            if key not in mapping:
                raise ValueError(f"unsupported target option: {key}")
            if value is None or value is False:
                continue
            rule = mapping[key]
            if isinstance(rule, dict):
                if str(value) not in rule:
                    raise ValueError(f"unsupported {key}: {value}")
                args.extend(rule[str(value)])
            elif isinstance(value, bool):
                args.append(rule)
            else:
                args.extend((rule, str(value)))
        return args
