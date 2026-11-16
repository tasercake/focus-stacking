"""Native macOS UI driver. No target or UI framework dependencies."""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import sys
import subprocess
import tempfile
import time
import unicodedata
from typing import Any, Callable


def native_helper(cache_directory: Path | None = None) -> Path:
    """Compile the small AX/CGEvent transport once for each source revision."""
    source = Path(__file__).with_name("native_macos.swift")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    cache = cache_directory or Path(tempfile.gettempdir()) / "pancake-conformance-native"
    cache.mkdir(parents=True, exist_ok=True)
    binary = cache / f"macos-ui-{digest}"
    if not binary.exists():
        temporary = binary.with_name(binary.name + f".{os.getpid()}.tmp")
        result = subprocess.run(["xcrun", "swiftc", "-O", str(source), "-o", str(temporary), "-framework", "AppKit", "-framework", "ApplicationServices"], capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise RuntimeError(f"Native UI helper compilation failed:\n{result.stderr}")
        temporary.replace(binary)
    return binary


def find_node(snapshot: dict[str, Any], selector: str | dict[str, Any]) -> dict[str, Any]:
    """Find a semantic identifier or an explicit accessibility selector."""
    wanted = {"id": selector} if isinstance(selector, str) else selector
    matches = [node for node in snapshot["nodes"] if all(node.get(key) == value for key, value in wanted.items())]
    if len(matches) != 1:
        raise AssertionError(f"Expected one UI element for {wanted}; found {len(matches)}")
    return matches[0]


def assert_directory_breadcrumbs(titles, destination: Path) -> None:
    """Check the native path menu's full ancestor chain, not only a leaf name."""
    expected = list(reversed(Path(destination).resolve().parts[1:]))
    def normalize(value):
        return unicodedata.normalize("NFC", str(value))
    actual = [normalize(value) for value in titles[:len(expected)]]
    wanted = [normalize(value) for value in expected]
    assert actual == wanted, f"Unverified native destination: observed {actual}, expected {wanted}"


def native_path_ready(snapshot, destination: Path) -> bool:
    """Cocoa resolves typed paths asynchronously before accepting navigation."""
    expected = str(Path(destination).resolve())
    suggestions = [node for node in snapshot["nodes"] if node.get("role") == "AXList"
                   and node.get("description") == "path" and node.get("id") == expected]
    return any(any(row.get("role") == "AXRow" and row.get("selected")
                       and row.get("path") == suggestion["path"][:-2]
                       for row in snapshot["nodes"]) for suggestion in suggestions)


class MacOSUISession:
    """A process plus a native accessibility connection; records all requests."""

    def __init__(self, process: subprocess.Popen, directory: Path):
        self.process = process
        self.pid = process.pid
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._trace = (self.directory / "ui-actions.jsonl").open("a")
        self._stderr = (self.directory / "ui-driver.stderr").open("a")
        self._helper = None
        try:
            self._helper = subprocess.Popen([str(native_helper())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr, text=True, bufsize=1, start_new_session=True)
            if not self._request("trust")["trusted"]:
                raise RuntimeError("macOS Accessibility permission is required for native UI tests")
        except BaseException:
            if self._helper is not None:
                self._reap(self._helper)
            self._trace.close()
            self._stderr.close()
            raise

    def _request(self, command: str, **values: Any) -> Any:
        request = {"pid": self.pid, "command": command, **values}
        self._trace.write(json.dumps(request) + "\n")
        self._trace.flush()
        assert self._helper.stdin is not None and self._helper.stdout is not None
        self._helper.stdin.write(json.dumps(request) + "\n")
        self._helper.stdin.flush()
        poller = selectors.DefaultSelector()
        try:
            poller.register(self._helper.stdout, selectors.EVENT_READ)
            if not poller.select(20):
                raise TimeoutError(f"Native UI driver did not answer {command}")
        finally:
            poller.close()
        line = self._helper.stdout.readline()
        if not line:
            raise RuntimeError(f"Native UI driver exited ({self._helper.poll()})")
        result = json.loads(line)
        self._trace.write(json.dumps({"response": result}) + "\n")
        self._trace.flush()
        if not result["ok"]:
            raise RuntimeError(f"{result["error"]} (target exit status: {self.process.poll()})")
        return result["result"]

    @staticmethod
    def _selector(selector: str | dict[str, Any]) -> dict[str, Any]:
        return {"id": selector} if isinstance(selector, str) else selector

    def snapshot(self) -> dict[str, Any]:
        return self._request("snapshot")

    def node(self, selector: str | dict[str, Any], *, timeout: float = 5) -> dict[str, Any]:
        """Wait for native publication; reject ambiguous selectors immediately."""
        wanted = self._selector(selector)

        def matches(snapshot):
            return [node for node in snapshot["nodes"] if all(node.get(key) == value for key, value in wanted.items())]

        found = matches(self.snapshot())
        if not found:
            found = self.wait(matches, timeout=timeout, description=f"UI element {wanted}")
        return find_node({"nodes": found}, wanted)

    def click(self, selector: str | dict[str, Any], *, physical: bool = True, position: tuple[float, float] | None = None,
              count: int = 1, button: str = "left") -> None:
        if count not in (1, 2) or button not in ("left", "right"):
            raise ValueError("Native click supports one/two clicks and left/right buttons")
        if not physical and (count != 1 or button != "left"):
            raise ValueError("Pointer variants require physical input")
        command = "click" if physical or position is not None else "press"
        variants = {"count": count, "button": button} if count != 1 or button != "left" else {}
        self._request(command, selector=self._selector(selector), **variants,
                      **({"position": position} if position is not None else {}))

    def select(self, selector: str | dict[str, Any], value: str, *, timeout: float = 5) -> None:
        """Open once, wait for a visible option, and return after selection commits."""
        control = self.node(selector, timeout=timeout)

        def selected(node):
            return node.get("title") == value or node.get("value") == value

        if selected(control):
            return
        control_selector = self._selector(selector)
        if "role" not in control_selector and control.get("role"):
            control_selector = {**control_selector, "role": control["role"]}

        def option(snapshot):
            return next((node for node in snapshot["nodes"]
                         if node.get("role") in ("AXMenuItem", "AXStaticText", "AXRow", "AXCell")
                         and (node.get("title") == value or node.get("description") == value)
                         and len(node.get("size", [])) == 2
                         and all(length > 0 for length in node["size"])), None)

        actions = self._request("attributes", selector=control_selector).get("_AXActions", [])
        if "AXShowMenu" in actions:
            self._request("action", selector=control_selector, action="AXShowMenu")
        else:
            self.click(control_selector)
        try:
            item = self.wait(option, timeout=timeout, description=f"visible popup option {value}")
        except TimeoutError:
            # Some native controls advertise AXShowMenu but acknowledge it
            # without opening. Retry only a supported native press, and only
            # when the control explicitly reports that it stayed collapsed.
            state = self._request("attributes", selector=control_selector)
            if ("AXShowMenu" not in actions or state.get("AXExpanded") is not False
                    or "AXPress" not in state.get("_AXActions", [])):
                raise
            self._request("action", selector=control_selector, action="AXPress")
            item = self.wait(option, timeout=timeout, description=f"visible popup option {value}")
        self.click({"path": item["path"]})
        self.wait(lambda snapshot: selected(find_node(snapshot, control_selector)) and option(snapshot) is None,
                  timeout=timeout, description=f"committed popup selection {value}")

    def focus(self, selector: str | dict[str, Any]) -> None:
        self._request("focus", selector=self._selector(selector))

    def set_value(self, selector: str | dict[str, Any], value: Any) -> None:
        self._request("set", selector=self._selector(selector), value=value)

    def key(self, key: str, modifiers: tuple[str, ...] = ()) -> None:
        self._request("key", key=key, modifiers=modifiers)

    def text(self, text: str) -> None:
        self._request("text", text=text)

    def drag(self, selector: str | dict[str, Any], start: tuple[float, float], end: tuple[float, float]) -> None:
        self._request("drag", selector=self._selector(selector), start=start, end=end)

    def scroll(self, selector: str | dict[str, Any], dy: int, *, modifiers=(), units="pixel") -> None:
        if units not in ("pixel", "line"):
            raise ValueError("Native scroll units must be pixel or line")
        variants = {"modifiers": modifiers, "units": units} if modifiers or units != "pixel" else {}
        self._request("scroll", selector=self._selector(selector), dy=dy, **variants)

    def edit(self, selector, value) -> None:
        """Type into a native field or incrementor and commit with Tab."""
        self.click(selector, position=(0.35, 0.5))
        self.key("a", ("command",))
        self.text(str(value))
        self.key("tab")

    def navigate_folder(self, folder: Path) -> None:
        """Navigate a native file panel to an existing sandbox directory."""
        folder = Path(folder).resolve()
        sandbox = self.directory.parent.resolve()
        if not folder.is_dir() or not folder.is_relative_to(sandbox):
            raise ValueError(f"Native file panel directory must exist inside case sandbox: {folder}")
        snapshot = self.snapshot()
        triangles = [node for node in snapshot["nodes"] if node.get("id") == "NS_OPEN_SAVE_DISCLOSURE_TRIANGLE"]
        if triangles and triangles[0].get("value") == 0:
            self.click("NS_OPEN_SAVE_DISCLOSURE_TRIANGLE")
        self.key("g", ("command", "shift"))
        self.wait(lambda snap: any(node.get("id") == "PathTextField" for node in snap["nodes"]), description="native Go to Folder")
        self.click("PathTextField")
        self.set_value("PathTextField", "")
        self.text(str(folder))
        self.wait(lambda snap: find_node(snap, "PathTextField").get("value") == str(folder), description="complete sandbox path")
        self.wait(lambda snapshot: native_path_ready(snapshot, folder), description="resolved native folder suggestion")
        self.key("return")
        self.wait(lambda snap: not any(node.get("id") == "GoToWindow" for node in snap["nodes"]), description="native folder navigation")
        self.wait(lambda snap: find_node(snap, "where popup").get("value") == folder.name, description="verified sandbox destination")
        self.click("where popup")
        try:
            snapshot = self.wait(lambda snap: snap if any(node.get("role") == "AXMenu" and node.get("size", [0, 0])[0] > 0 for node in snap["nodes"]) else None, description="native destination path menu")
            menus = [node for node in snapshot["nodes"] if node.get("role") == "AXMenu" and node.get("size", [0, 0])[0] > 0]
            assert len(menus) == 1, "Destination path menu is ambiguous"
            prefix = menus[0]["path"]
            titles = [node.get("title") for node in snapshot["nodes"] if node.get("role") == "AXMenuItem" and len(node["path"]) == len(prefix) + 1 and node["path"][:len(prefix)] == prefix]
            assert_directory_breadcrumbs(titles, folder)
            items = [node for node in snapshot["nodes"] if node.get("role") == "AXMenuItem" and len(node["path"]) == len(prefix) + 1 and node["path"][:len(prefix)] == prefix]
            self.click({"path": items[0]["path"]}, physical=False)
            self.wait(lambda snap: not any(node.get("role") == "AXMenu" and node.get("size", [0, 0])[0] > 0 for node in snap["nodes"]), description="destination path menu closed")
        except BaseException:
            self.key("escape")
            raise
        self._verified_directory = folder

    def choose_file(self, path: Path) -> None:
        """Select a managed file through the actual native Open panel."""
        path = Path(path).resolve()
        if not path.is_file() or not path.is_relative_to(self.directory.parent.resolve()):
            raise ValueError(f"Native Open input must be a file inside case sandbox: {path}")
        self.key("g", ("command", "shift"))
        self.wait(lambda snap: any(node.get("id") == "PathTextField" for node in snap["nodes"]), description="native Go to File")
        self.click("PathTextField")
        self.set_value("PathTextField", "")
        self.text(str(path))
        self.wait(lambda snap: find_node(snap, "PathTextField").get("value") == str(path), description="complete sandbox file path")
        self.wait(lambda snapshot: native_path_ready(snapshot, path), description="resolved native file suggestion")
        self.key("return")
        self.wait(lambda snap: not any(node.get("id") == "GoToWindow" for node in snap["nodes"]), description="native file selection")
        self.click("OKButton", physical=False)

    def save_file(self, path: Path) -> Path:
        """Fill and accept the real native Save panel, after guarded navigation."""
        path = Path(path).resolve()
        if path.exists():
            raise ValueError(f"Conformance export must not overwrite an existing file: {path}")
        self.wait(lambda snap: any(node.get("id") == "save-panel" for node in snap["nodes"]), description="native Save panel")
        self.navigate_folder(path.parent)
        self.set_value("saveAsNameTextField", path.name)
        assert self.node("saveAsNameTextField")["value"] == path.name
        assert self._verified_directory == path.parent
        assert self.node("where popup")["value"] == path.parent.name
        self.click("OKButton", physical=False)
        self.wait(lambda snap: path.is_file() and not any(node.get("id") == "save-panel" for node in snap["nodes"]), description="export written inside sandbox")
        return path

    def screenshot(self, path: Path | None = None) -> Path:
        path = path or self.directory / "screenshot.png"
        self._request("screenshot", path=str(path))
        return path

    def wait(self, condition: Callable[[dict[str, Any]], Any], timeout: float = 30, *, description: str = "UI state") -> Any:
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Target exited ({self.process.returncode}) while waiting for {description}")
            try:
                last = self.snapshot()
                result = condition(last)
                if result:
                    return result
            except (AssertionError, RuntimeError) as exc:
                last = {"error": str(exc)}
            time.sleep(0.05)
        (self.directory / "timeout-tree.json").write_text(json.dumps(last, indent=2))
        try:
            self.screenshot(self.directory / "timeout.png")
        except RuntimeError:
            pass
        raise TimeoutError(f"Timed out after {timeout}s waiting for {description}")

    @staticmethod
    def _reap(process, timeout=5):
        forced = False
        if process is None:
            return forced
        if process.poll() is None:
            try:
                if os.getpgid(process.pid) == process.pid:
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                forced = True
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.getpgid(process.pid) == process.pid:
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=5)
            except ProcessLookupError:
                process.wait(timeout=5)
        return forced

    def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        try:
            self._close_processes()
        finally:
            lease = getattr(self, "_desktop_lease", None)
            if lease is not None:
                lease.release()

    def _close_processes(self) -> None:
        forced = False
        close_error = None
        with ExitStack() as cleanup:
            for stream in (self._trace, self._stderr, *getattr(self, "_target_logs", ()),
                           getattr(self._helper, "stdin", None), getattr(self._helper, "stdout", None)):
                if stream is not None:
                    cleanup.callback(stream.close)
            cleanup.callback(self._reap, self._helper)
            try:
                if self.process.poll() is None and self._helper.poll() is None:
                    try:
                        self.key("w", ("command",))
                        deadline = time.monotonic() + 5
                        while self.process.poll() is None and time.monotonic() < deadline:
                            snap = self.snapshot()
                            button = next((node for node in snap["nodes"]
                                           if node.get("title") in ("Quit Anyway", "Discard")
                                           and node.get("role") == "AXButton" and node.get("enabled") is True), None)
                            if button is not None:
                                self.click({"path": button["path"]}, physical=False)
                                break
                            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
                        self.process.wait(timeout=max(0, deadline - time.monotonic()))
                    except (RuntimeError, TimeoutError, OSError, subprocess.TimeoutExpired) as error:
                        close_error = str(error)
            finally:
                try:
                    forced = self._reap(self.process)
                finally:
                    returncode = self.process.poll()
                    expected_termination = forced and returncode in (-signal.SIGTERM, -signal.SIGKILL)
                    status = "clean" if returncode == 0 else "forced" if expected_termination else "failed"
                    outcome = {"pid": self.pid if hasattr(self, "pid") else self.process.pid,
                               "returncode": returncode, "forced": bool(forced), "status": status}
                    if close_error is not None:
                        outcome["close_error"] = close_error
                    (self.directory / "shutdown.json").write_text(json.dumps(outcome, indent=2) + "\n")
        if returncode != 0 and not expected_termination:
            raise RuntimeError(f"Native GUI target exited with status {returncode}; inspect {self.directory / 'shutdown.json'}")

    def __enter__(self) -> "MacOSUISession":
        try:
            self.wait(lambda snap: any(node.get("role") == "AXWindow" for node in snap["nodes"]), timeout=90, description="main window")
            self._request("raise")
        except BaseException as error:
            try:
                self.close()
            except Exception as cleanup_error:
                error.add_note(f"UI shutdown also failed: {cleanup_error}")
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            try:
                (self.directory / "failure-tree.json").write_text(json.dumps(self.snapshot(), indent=2))
                self.screenshot(self.directory / "failure.png")
            except Exception as diagnostics_error:
                exc.add_note(f"UI failure diagnostics also failed: {diagnostics_error}")
        try:
            self.close()
        except Exception as cleanup_error:
            if exc is None:
                raise
            exc.add_note(f"UI shutdown also failed: {cleanup_error}")


def open_session(command, *, cwd, env, directory, paths=(), settings_id="default"):
    """Launch any native target described by its external command and environment."""
    from .desktop import DesktopLease

    if not settings_id or Path(settings_id).name != settings_id or settings_id in {".", ".."}:
        raise ValueError("settings_id must be a single directory name")
    lease = DesktopLease().acquire()
    stdout = stderr = process = None
    try:
        if sys.platform == "linux" and env.get("PANCAKE_CONFORMANCE_LINUX_DESKTOP") != "1":
            raise RuntimeError("Linux UI requires an isolated desktop; use pancake-conformance run")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        environment = dict(env)
        environment["CONFORMANCE_UI_SETTINGS_DIR"] = str(directory.parent / "ui-settings" / settings_id)
        stdout = (directory / "target.stdout").open("w")
        stderr = (directory / "target.stderr").open("w")
        process = subprocess.Popen([*map(str, command), *map(str, paths)], cwd=cwd, env=environment,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        if sys.platform == "linux":
            from .linux_ui import LinuxUISession
            session = LinuxUISession(process, directory, environment)
        else:
            session = MacOSUISession(process, directory)
        session._target_logs = (stdout, stderr)
        session._desktop_lease = lease
        return session
    except BaseException:
        try:
            if process is not None:
                MacOSUISession._reap(process)
            for stream in (stdout, stderr):
                if stream is not None:
                    stream.close()
        finally:
            lease.release()
        raise
