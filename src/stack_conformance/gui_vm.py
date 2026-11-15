"""One persistent Tart macOS guest for native conformance, isolated from host input.

This module only transports the unchanged suite and target into a configured VM.
Native control, image assertions and source coverage remain in their own layers.
There is no host GUI fallback on any provisioning or execution failure.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import fcntl
import io
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import platform
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time
import tomllib
import uuid


@dataclass(frozen=True)
class VMRun:
    report: dict
    artifacts: Path
    returncode: int
    guest_output: str
    guest_source_root: str
    source_provenance: dict


def safe_extract_artifacts(archive_path, destination):
    """Extract only contained directories, regular files and verified hardlinks."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        names = {}
        for member in members:
            name = PurePosixPath(member.name)
            target = destination / str(name)
            if (name.is_absolute() or ".." in name.parts or
                    not target.resolve().is_relative_to(destination) or
                    not (member.isfile() or member.isdir() or member.islnk())):
                raise ValueError(f"Unsafe guest artifact member: {member.name}")
            if member.islnk():
                link = PurePosixPath(member.linkname)
                if link.is_absolute() or ".." in link.parts:
                    raise ValueError(f"Unsafe guest artifact hardlink: {member.name}")
            names[str(name)] = member
        for member in members:
            target = destination / str(PurePosixPath(member.name))
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        for member in members:
            if member.islnk():
                link_name = str(PurePosixPath(member.linkname))
                source = destination / link_name
                if (link_name not in names or not names[link_name].isfile() or
                        not source.resolve().is_relative_to(destination) or not source.is_file()):
                    raise ValueError(f"Unsafe guest artifact hardlink target: {member.linkname}")
                target = destination / str(PurePosixPath(member.name))
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target.unlink()
                os.link(source, target)


# The LaunchAgent runs this wrapper in the logged-in guest's Aqua session.
# subprocess argv comes from a JSON file, never from shell interpolation.
_GUEST_JOB = r'''import json, os, pathlib, shutil, signal, subprocess, sys, traceback
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
output = pathlib.Path(payload["output"])
job = pathlib.Path(payload["job"])
status = {"complete": False, "returncode": 2}
child = None

def stopped(signum, frame):
    if child is not None and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, stopped)
try:
    environment = dict(os.environ, CF_VM_GUEST="1", PATH=payload["path"])
    with (job / "cli.stdout").open("w") as stdout, (job / "cli.stderr").open("w") as stderr:
        child = subprocess.Popen(payload["command"], cwd=payload["workspace"], env=environment,
                                 stdout=stdout, stderr=stderr, start_new_session=True)
        status["returncode"] = child.wait()
except BaseException:
    (job / "wrapper-error.txt").write_text(traceback.format_exc())
finally:
    if child is not None and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    output.mkdir(parents=True, exist_ok=True)
    try:
        if payload.get("adapter") == "chimpstackr-python":
            from stack_conformance.coverage import source_provenance
            manifest = source_provenance(payload["source_root"], target_commit=payload["target_commit"])
        else:
            manifest = {"schema_version": 1, "target_commit": payload["target_commit"],
                        "source_bundle_sha256": payload["source_bundle_sha256"], "adapter": payload.get("adapter", "")}
        (output / "vm-source.json").write_text(json.dumps(manifest, indent=2) + "\n")
    except BaseException:
        status["source_error"] = traceback.format_exc()
    for source in job.iterdir():
        if source.name in ("cli.stdout", "cli.stderr", "wrapper-error.txt"):
            shutil.copyfile(source, output / ("vm-" + source.name))
    status["complete"] = True
    temporary = job / "status.tmp"
    temporary.write_text(json.dumps(status))
    temporary.replace(job / "status.json")
    (output / "vm-job-status.json").write_text(json.dumps(status, indent=2) + "\n")
'''


class TartGuiVM:
    def __init__(self, config, workspace, output, visible=False, persist=False):
        self.config = dict(config)
        self.name = str(self.config.get("name", ""))
        self.user = str(self.config.get("ssh_user", "admin"))
        self.guest_root = str(self.config.get("guest_root", f"/Users/{self.user}/stack-conformance"))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", self.name):
            raise ValueError("gui_vm.name must be a configured local Tart VM name")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", self.user):
            raise ValueError("gui_vm.ssh_user is invalid")
        guest = PurePosixPath(self.guest_root)
        if (not guest.is_absolute() or ".." in guest.parts or
                len(guest.parts) < 4 or guest.parts[:3] != ("/", "Users", self.user)):
            raise ValueError("gui_vm.guest_root must be a dedicated directory below the guest user's home")
        self.workspace = Path(workspace).resolve()
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.visible, self.persist = bool(visible), bool(persist)
        self._tart = shutil.which("tart")
        self._ssh_binary = shutil.which("ssh") or "/usr/bin/ssh"
        self._ip = None
        self._started = False
        self._prepared = False
        self._process = None
        self._boot_log = None
        self._job_label = None
        self._uid = None
        self._repositories = []
        self._adapter = ""
        self._bundle_digest = ""
        self._lease_path = Path(tempfile.gettempdir()) / f"stack-conformance-tart-{os.getuid()}" / (self.name + ".lock")
        self._lease_file = None
        self.run_id = "vm-" + uuid.uuid4().hex
        self.guest_output = str(guest / "artifacts" / self.run_id)
        self.guest_path = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/" + self.user + "/.local/bin"

    def _execute(self, argv, *, input=None, timeout=120, check=True, stdout=None):
        try:
            result = subprocess.run(list(map(str, argv)), input=input,
                                    stdout=subprocess.PIPE if stdout is None else stdout,
                                    stderr=subprocess.PIPE, text=not isinstance(input, bytes), timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"GUI VM command timed out after {timeout}s: {Path(str(argv[0])).name}") from exc
        if isinstance(result.stdout, bytes):
            result.stdout = result.stdout.decode(errors="replace")
        if isinstance(result.stderr, bytes):
            result.stderr = result.stderr.decode(errors="replace")
        if check and result.returncode:
            raise RuntimeError(f"GUI VM {Path(str(argv[0])).name} failed ({result.returncode}): {result.stderr.strip()}")
        return result

    def _ssh_arguments(self, command):
        if self._ip is None:
            raise RuntimeError("GUI VM has no SSH address")
        argv = [self._ssh_binary, "-F", "/dev/null", "-o", "ForwardAgent=no", "-o", "ClearAllForwardings=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=accept-new", "-o", f"HostKeyAlias={self.name}",
                "-o", f"UserKnownHostsFile={self.output / 'known_hosts'}"]
        identity = self.config.get("ssh_identity")
        if identity:
            path = Path(identity).expanduser().resolve()
            if not path.is_file():
                raise RuntimeError("GUI VM SSH identity file does not exist")
            argv.extend(("-i", str(path), "-o", "IdentitiesOnly=yes"))
        argv.extend((f"{self.user}@{self._ip}", command))
        return argv

    def _ssh(self, command, **kwargs):
        return self._execute(self._ssh_arguments(command), **kwargs)

    def _wait_for_ssh(self):
        deadline = time.monotonic() + 180
        error = "guest not reachable"
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"Tart exited while booting {self.name}; see {self.output / 'tart.log'}")
            address = self._execute([self._tart, "ip", self.name], timeout=10, check=False)
            if address.returncode == 0:
                try:
                    self._ip = str(ipaddress.ip_address(address.stdout.strip()))
                except ValueError:
                    raise RuntimeError("Tart returned an invalid guest IP address") from None
                result = self._ssh("true", timeout=10, check=False)
                if result.returncode == 0:
                    return
                error = result.stderr.strip()
                if "Permission denied" in error or "IDENTIFICATION HAS CHANGED" in error:
                    raise RuntimeError(f"GUI VM SSH authentication failed: {error}")
            time.sleep(1)
        raise RuntimeError(f"GUI VM SSH did not become ready within 180s: {error}")

    def _wait_for_aqua(self, uid, timeout=120):
        deadline = time.monotonic() + timeout
        self._aqua_attempts = 0
        while time.monotonic() < deadline:
            self._aqua_attempts += 1
            ready = self._ssh("/bin/launchctl print gui/" + uid, timeout=10, check=False)
            if ready.returncode == 0:
                return self._aqua_attempts
            if self._aqua_attempts == 1:
                print("GUI VM: SSH ready; waiting for guest Aqua login", flush=True)
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        raise RuntimeError(f"GUI VM Aqua session did not become ready within {timeout}s; sign in as {self.user} in the guest desktop and check automatic login")

    def _preflight(self):
        metadata = {"vm": self.name, "host": {"os": platform.system(), "architecture": platform.machine()},
                    "guest": {"ssh_user": self.user}, "checks": {}}
        try:
            uid = self._ssh("/usr/bin/id -u", timeout=20).stdout.strip()
            if not uid.isdigit() or int(uid) == 0:
                raise RuntimeError("GUI VM SSH user must be a non-root logged-in desktop user")
            self._uid = uid
            metadata["guest"]["aqua_uid"] = int(uid)
            metadata["checks"]["aqua"] = False
            metadata["guest"]["aqua_attempts"] = self._wait_for_aqua(uid)
            metadata["checks"]["aqua"] = True
            architecture = self._ssh("/usr/bin/uname -s -m", timeout=20).stdout.split()
            metadata["checks"]["native_arm64"] = architecture == ["Darwin", "arm64"]
            if not metadata["checks"]["native_arm64"]:
                raise RuntimeError("GUI VM must run native Darwin arm64; emulation is unsupported")
            metadata["guest"].update({"os": architecture[0], "architecture": architecture[1]})
            for command, label, key in ((["/usr/bin/env", "PATH=" + self.guest_path, "uv", "--version"], "uv", "uv_version"),
                                        (["/usr/bin/xcrun", "--find", "swiftc"], "Swift command-line tools", "swift_compiler")):
                result = self._ssh(shlex.join(command), timeout=30, check=False)
                metadata["checks"][key] = result.returncode == 0
                metadata["guest"][key] = result.stdout.strip()
                if result.returncode:
                    raise RuntimeError(f"GUI VM lacks {label}; provision the guest before testing")
            for command, key in (("/usr/bin/sw_vers -productVersion", "os_version"),
                                 ("/usr/bin/sw_vers -buildVersion", "os_build"),
                                 ("/usr/bin/xcrun swift --version", "swift_version"),
                                 ("/usr/bin/csrutil status", "sip_status")):
                result = self._ssh(command, timeout=30, check=False)
                metadata["guest"][key] = result.stdout.strip() if result.returncode == 0 else "unavailable: " + result.stderr.strip()
        finally:
            metadata["guest"]["aqua_attempts"] = getattr(self, "_aqua_attempts", 0)
            (self.output / "vm-preflight.json").write_text(json.dumps(metadata, indent=2) + "\n")

    def _acquire_lease(self):
        if self._lease_file is not None:
            return
        self._lease_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = self._lease_path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise RuntimeError(f"GUI VM {self.name} is already in use by another conformance run") from exc
        self._lease_file = handle

    def prepare(self):
        if self._prepared:
            return
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("GUI VM execution requires a native macOS Apple Silicon host")
        self._acquire_lease()
        try:
            self._prepare()
        except BaseException:
            self.close()
            raise

    def _prepare(self):
        if not self._tart:
            raise RuntimeError("Tart is required for --gui-vm; no host GUI fallback is allowed")
        state = self._execute([self._tart, "get", self.name, "--format", "json"], timeout=20)
        try:
            running = json.loads(state.stdout)["Running"]
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("Tart did not return a valid VM state") from exc
        if not running:
            self._boot_log = (self.output / "tart.log").open("w")
            argv = [self._tart, "run", self.name]
            if not self.visible:
                argv.append("--no-graphics")
            argv.extend(("--no-clipboard", "--no-audio"))
            self._process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=self._boot_log,
                                             stderr=subprocess.STDOUT, start_new_session=True)
            self._started = True
        print(f"GUI VM: {'starting' if self._started else 'reusing'} {self.name}", flush=True)
        self._wait_for_ssh()
        self._preflight()
        self._prepared = True

    def _source_archive(self, target_path):
        target_path = Path(target_path).resolve()
        if not target_path.is_relative_to(self.workspace):
            raise ValueError("VM target descriptor must be inside the project workspace")
        data = tomllib.loads(target_path.read_text())
        target_root = (target_path.parent / data["root"]).resolve()
        if not target_root.is_relative_to(self.workspace):
            raise ValueError("VM target source must be inside the project workspace")
        repositories = [(target_root, "target")]
        reference = self.workspace / "submodules/ChimpStackr"
        if reference.is_dir() and reference.resolve() != target_root:
            project = tomllib.loads((self.workspace / "pyproject.toml").read_text())
            members = project.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
            if "submodules/ChimpStackr" in members:
                repositories.append((reference, "reference"))
        files = [self.workspace / name for name in ("pyproject.toml", "uv.lock", "README.md", ".python-version")]
        files.extend(path for path in (self.workspace / "src").rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
        files.extend(path for path in (self.workspace / "targets").rglob("*") if path.is_file())
        self._repositories = []
        for repository, label in repositories:
            commit = self._execute(["git", "-C", str(repository), "rev-parse", "HEAD"]).stdout.strip()
            if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
                raise RuntimeError("Cannot determine pinned VM target commit")
            bundle = self.output / (label + ".bundle")
            if bundle.exists():
                bundle.unlink()
            self._execute(["git", "-C", str(repository), "bundle", "create", str(bundle), "HEAD", "--tags"], timeout=180)
            listed = subprocess.run(["git", "-C", str(repository), "ls-files", "-z"], capture_output=True, check=True)
            files.extend(repository / name.decode() for name in listed.stdout.split(b"\0") if name)
            self._repositories.append({"relative": repository.relative_to(self.workspace).as_posix(),
                                       "bundle": ".conformance-" + label + ".bundle", "commit": commit,
                                       "local_bundle": bundle})
        pin = self._repositories[0]["commit"]
        files.append(target_path)
        archive_path = self.output / "workspace.tar"
        digest = hashlib.sha256()
        with tarfile.open(archive_path, "w") as archive:
            for path in sorted(set(files)):
                if not path.is_file():
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(self.workspace):
                    raise ValueError(f"VM source contains an unsupported symlink: {path}")
                relative = path.relative_to(self.workspace).as_posix()
                content = path.read_bytes()
                digest.update(relative.encode() + b"\0" + content)
                member = tarfile.TarInfo(relative)
                member.size = len(content)
                member.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                archive.addfile(member, io.BytesIO(content))
            for repository in self._repositories:
                bundle = repository["local_bundle"]
                member = tarfile.TarInfo(repository["bundle"])
                member.size = bundle.stat().st_size
                with bundle.open("rb") as source:
                    archive.addfile(member, source)
        return archive_path, target_path.relative_to(self.workspace).as_posix(), target_root.relative_to(self.workspace).as_posix(), pin, digest.hexdigest()

    def _sync_workspace(self, target_path):
        archive, descriptor, target_relative, pin, digest = self._source_archive(target_path)
        root = shlex.quote(self.guest_root)
        # Remove only suite-owned source directories; preserve the VM and its venv.
        repositories = self._repositories or [{"relative": target_relative, "bundle": ".conformance-target.bundle", "commit": pin}]
        cleanup_names = ["src", "targets", *[item["relative"] for item in repositories]]
        cleanup = "import json,pathlib,shutil,sys; r=pathlib.Path(sys.argv[1]); [shutil.rmtree(r/n,ignore_errors=True) for n in json.loads(sys.argv[2])]; r.mkdir(parents=True,exist_ok=True)"
        self._ssh(shlex.join(["/usr/bin/python3", "-c", cleanup, self.guest_root, json.dumps(cleanup_names)]), timeout=30)
        self._ssh(f"/usr/bin/tar -xf - -C {root}", input=archive.read_bytes(), timeout=300)
        target = str(PurePosixPath(self.guest_root) / target_relative)
        # A bundle contains repository objects/tags, never host Git config or SSH credentials.
        repositories = self._repositories or [{"relative": target_relative, "bundle": ".conformance-target.bundle", "commit": pin}]
        for repository in repositories:
            checkout = str(PurePosixPath(self.guest_root) / repository["relative"])
            commands = [
                ["/usr/bin/git", "clone", "--bare", "--quiet", str(PurePosixPath(self.guest_root) / repository["bundle"]), checkout + "/.git"],
                ["/usr/bin/git", "--git-dir", checkout + "/.git", "config", "core.bare", "false"],
                ["/usr/bin/git", "--git-dir", checkout + "/.git", "config", "core.worktree", checkout],
                ["/usr/bin/git", "-C", checkout, "reset", "--mixed", "--quiet", repository["commit"]],
            ]
            for command in commands:
                self._ssh(shlex.join(command), timeout=180)
        self._adapter = tomllib.loads(Path(target_path).read_text()).get("adapter", "")
        self._bundle_digest = digest
        extra = " --extra chimpstackr" if self._adapter == "chimpstackr-python" else ""
        self._ssh(f"cd {root} && PATH={shlex.quote(self.guest_path)} uv sync --locked{extra}", timeout=600)
        metadata = {"name": self.name, "guest_root": self.guest_root, "target_commit": pin,
                    "source_bundle_sha256": digest, "visible": self.visible, "persist": self.persist}
        (self.output / "vm.json").write_text(json.dumps(metadata, indent=2) + "\n")
        return descriptor, target, pin

    def _guest_command(self, case_ids, descriptor, *, coverage, fail_fast, cli_command=None, gui_command=None):
        command = [self.guest_root + "/.venv/bin/stack-conformance", "run", "--no-gui-vm",
                   "--target", str(PurePosixPath(self.guest_root) / descriptor), "--output", self.guest_output,
                   "--coverage" if coverage else "--no-coverage"]
        if fail_fast:
            command.append("--fail-fast")
        for case_id in case_ids:
            command.extend(("--case", case_id))
        for flag, override in (("--cli-command", cli_command), ("--gui-command", gui_command)):
            if override is not None:
                if not override or not all(isinstance(token, str) for token in override):
                    raise ValueError("VM command override must be a nonempty string array")
                translated = [self.guest_root + token[len(str(self.workspace)):] if
                              (token == str(self.workspace) or token.startswith(str(self.workspace) + os.sep))
                              else token for token in override]
                command.extend((flag, json.dumps(translated)))
        return command

    def _write_guest(self, path, content):
        self._ssh("/bin/cat > " + shlex.quote(str(path)), input=content, timeout=120)

    def _launch(self, command, target, pin):
        uid = self._ssh("/usr/bin/id -u", timeout=20).stdout.strip()
        if not uid.isdigit() or int(uid) == 0:
            raise RuntimeError("GUI VM SSH user must be a non-root logged-in desktop user")
        self._uid = uid
        ready = self._ssh("/bin/launchctl print gui/" + uid, timeout=20, check=False)
        if ready.returncode:
            raise RuntimeError("GUI VM has no logged-in Aqua session; provision guest login before testing")
        job = str(PurePosixPath(self.guest_root) / ".vm-jobs" / self.run_id)
        self._ssh(shlex.join(["/bin/mkdir", "-p", job]), timeout=20)
        self._write_guest(job + "/job.py", _GUEST_JOB)
        payload = {"command": command, "workspace": self.guest_root, "output": self.guest_output,
                   "job": job, "source_root": target + "/src", "target_commit": pin, "path": self.guest_path,
                   "adapter": self._adapter, "source_bundle_sha256": self._bundle_digest}
        self._write_guest(job + "/job.json", json.dumps(payload))
        self._job_label = "me.chimpstackr.conformance." + self.run_id
        plist = {"Label": self._job_label, "ProgramArguments": [self.guest_root + "/.venv/bin/python", job + "/job.py", job + "/job.json"],
                 "WorkingDirectory": self.guest_root, "RunAtLoad": True, "KeepAlive": False,
                 "LimitLoadToSessionType": "Aqua", "ProcessType": "Interactive",
                 "EnvironmentVariables": {"PATH": self.guest_path, "CF_VM_GUEST": "1"},
                 "StandardOutPath": job + "/launch.stdout", "StandardErrorPath": job + "/launch.stderr"}
        plist_path = job + "/job.plist"
        self._write_guest(plist_path, plistlib.dumps(plist))
        self._ssh(shlex.join(["/bin/launchctl", "bootstrap", "gui/" + uid, plist_path]), timeout=30)
        return job

    def _fetch(self):
        archive = self.output / "guest-artifacts.tar"
        with archive.open("wb") as stream:
            self._ssh(shlex.join(["/usr/bin/tar", "-C", self.guest_output, "-cf", "-", "."]),
                      timeout=600, stdout=stream)
        destination = self.output / "guest-artifacts"
        safe_extract_artifacts(archive, destination)
        return destination

    def _report_progress(self, total, last_count):
        result = self._ssh("/bin/cat " + shlex.quote(self.guest_output + "/report.json"), timeout=10, check=False)
        if result.returncode:
            return last_count
        try:
            report = json.loads(result.stdout)
            count = int(report.get("completed_count", 0))
            cases = report.get("cases", [])
            if last_count < count <= total and cases:
                latest = cases[-1]
                print(f"GUI VM: {count}/{total} native cases; {latest['id']} {latest['status']}", flush=True)
                return count
        except (ValueError, TypeError, KeyError):
            # The guest may be between writes to its JSON checkpoint.
            pass
        return last_count

    def run_cases(self, case_ids, *, target_path, coverage=True, fail_fast=False, timeout=3600, cli_command=None, gui_command=None):
        if not case_ids or len(case_ids) != len(set(case_ids)) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", item) for item in case_ids):
            raise ValueError("VM case IDs must be nonempty, unique, literal case identifiers")
        self.prepare()
        print("GUI VM: syncing pinned source and locked dependencies", flush=True)
        descriptor, target, pin = self._sync_workspace(target_path)
        command = self._guest_command(case_ids, descriptor, coverage=coverage, fail_fast=fail_fast,
                                      cli_command=cli_command, gui_command=gui_command)
        job = self._launch(command, target, pin)
        print(f"GUI VM: running {len(case_ids)} cases in guest Aqua session", flush=True)
        deadline = time.monotonic() + timeout
        status = None
        last_count, next_progress = 0, time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                if time.monotonic() >= next_progress:
                    last_count = self._report_progress(len(case_ids), last_count)
                    next_progress = time.monotonic() + 10
                result = self._ssh("/bin/cat " + shlex.quote(job + "/status.json"), timeout=20, check=False)
                if result.returncode == 0:
                    status = json.loads(result.stdout)
                    if status.get("complete"):
                        break
                time.sleep(1)
            if not status or not status.get("complete"):
                raise RuntimeError(f"GUI VM test job exceeded {timeout}s; host GUI was not used")
            artifacts = self._fetch()
        finally:
            self._stop_job()
        report_path = artifacts / "report.json"
        if not report_path.is_file() or status.get("source_error"):
            raise RuntimeError(f"GUI VM suite failed before a valid report; inspect {artifacts}")
        report = json.loads(report_path.read_text())
        manifest = json.loads((artifacts / "vm-source.json").read_text())
        return VMRun(report, artifacts, int(status["returncode"]), self.guest_output, target + "/src", manifest)

    def _stop_job(self):
        if self._job_label and self._ip and self._uid:
            self._ssh(shlex.join(["/bin/launchctl", "bootout", "gui/" + self._uid + "/" + self._job_label]),
                      timeout=20, check=False)
            self._job_label = None

    def close(self):
        try:
            try:
                self._stop_job()
            finally:
                if (self._prepared or self._started) and not self.persist:
                    self._execute([self._tart, "stop", self.name], timeout=60)
                    self._started = False
                self._prepared = False
        finally:
            if self._boot_log is not None:
                self._boot_log.close()
                self._boot_log = None
            if self._lease_file is not None:
                fcntl.flock(self._lease_file.fileno(), fcntl.LOCK_UN)
                self._lease_file.close()
                self._lease_file = None
