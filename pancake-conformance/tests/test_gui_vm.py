"""VM boundary safety and orchestration checks; never boot a VM in unit tests."""
import io
import json
import os
import subprocess
import tarfile
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def isolated_vm_lease(tmp_path, monkeypatch):
    # Pure tests must never contend with a real conformance VM invocation.
    from pancake_conformance.gui_vm import TartGuiVM
    original = TartGuiVM.__init__
    def initialize(vm, *args, **kwargs):
        original(vm, *args, **kwargs)
        vm._lease_path = tmp_path / "leases" / (vm.name + ".lock")
        vm._bootstrap.cache = tmp_path / "bootstrap-cache"
    monkeypatch.setattr(TartGuiVM, "__init__", initialize)


def config(**extra):
    return {"name": "pancake-conformance", "ssh_user": "admin",
            "guest_root": "/Users/admin/pancake-conformance", **extra}


def test_config_rejects_shell_options_and_unowned_guest_root(tmp_path):
    from pancake_conformance.gui_vm import TartGuiVM
    for settings in (config(name="--bad"), config(ssh_user="admin;false"), config(guest_root="/")):
        with pytest.raises(ValueError):
            TartGuiVM(settings, tmp_path, tmp_path / "run")


def test_headless_boot_has_no_clipboard_or_audio_passthrough(tmp_path, monkeypatch):
    monkeypatch.setattr("pancake_conformance.gui_vm.platform.system", lambda: "Darwin")
    monkeypatch.setattr("pancake_conformance.gui_vm.platform.machine", lambda: "arm64")
    from pancake_conformance.gui_vm import TartGuiVM
    calls = []
    monkeypatch.setattr("pancake_conformance.gui_vm.shutil.which", lambda name: "/usr/local/bin/" + name)
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run", persist=True)
    monkeypatch.setattr(vm, "_execute", lambda argv, **kw: SimpleNamespace(returncode=0, stdout=json.dumps({"Running": False}), stderr=""))
    monkeypatch.setattr(vm, "_wait_for_ssh", lambda: None)
    monkeypatch.setattr(vm, "_preflight", lambda: None)
    monkeypatch.setattr("pancake_conformance.gui_vm.subprocess.Popen", lambda argv, **kw: calls.append((argv, kw)) or SimpleNamespace(poll=lambda: None))
    vm.prepare()
    assert calls[0][0] == ["/usr/local/bin/tart", "run", "pancake-conformance", "--no-graphics", "--no-clipboard", "--no-audio"]
    assert calls[0][1]["start_new_session"] is True
    vm.close()


def test_running_vm_is_reused_then_stopped_without_persist(tmp_path, monkeypatch):
    monkeypatch.setattr("pancake_conformance.gui_vm.platform.system", lambda: "Darwin")
    monkeypatch.setattr("pancake_conformance.gui_vm.platform.machine", lambda: "arm64")
    from pancake_conformance.gui_vm import TartGuiVM
    calls = []
    monkeypatch.setattr("pancake_conformance.gui_vm.shutil.which", lambda name: "/usr/local/bin/" + name)
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    monkeypatch.setattr(vm, "_execute", lambda argv, **kw: calls.append(argv) or SimpleNamespace(returncode=0, stdout=json.dumps({"Running": True}), stderr=""))
    monkeypatch.setattr(vm, "_wait_for_ssh", lambda: None)
    monkeypatch.setattr(vm, "_preflight", lambda: None)
    monkeypatch.setattr("pancake_conformance.gui_vm.subprocess.Popen", lambda *a, **kw: pytest.fail("running VM booted again"))
    vm.prepare()
    vm.close()
    assert sum("stop" in call for call in calls) == 1


def test_owned_vm_stops_only_when_persist_is_false(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    monkeypatch.setattr("pancake_conformance.gui_vm.shutil.which", lambda name: "/usr/local/bin/" + name)
    calls = []
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run", persist=False)
    vm._started = True
    monkeypatch.setattr(vm, "_execute", lambda argv, **kw: calls.append(argv) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    vm.close()
    assert calls == [["/usr/local/bin/tart", "stop", "pancake-conformance"]]


def test_ssh_uses_dedicated_known_hosts_and_batch_auth(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    monkeypatch.setattr("pancake_conformance.gui_vm.shutil.which", lambda name: "/usr/bin/" + name)
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    vm._ip = "192.168.64.8"
    argv = vm._ssh_arguments("printf hello")
    assert "BatchMode=yes" in argv
    assert "StrictHostKeyChecking=accept-new" in argv
    assert f"UserKnownHostsFile={tmp_path / 'run' / 'known_hosts'}" in argv
    assert argv[-2:] == ["admin@192.168.64.8", "printf hello"]
    assert "StrictHostKeyChecking=no" not in argv


def tar_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, kind, content in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = content
                archive.addfile(member)
            else:
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
    return stream.getvalue()


@pytest.mark.parametrize("name,kind,content", [("../escape", tarfile.REGTYPE, b"bad"),
                                               ("/absolute", tarfile.REGTYPE, b"bad"),
                                               ("link", tarfile.SYMTYPE, "../escape"),
                                               ("link", tarfile.LNKTYPE, "../escape")])
def test_guest_artifact_extraction_rejects_unsafe_members(tmp_path, name, kind, content):
    from pancake_conformance.gui_vm import safe_extract_artifacts
    archive = tmp_path / "guest.tar"
    archive.write_bytes(tar_bytes([(name, kind, content)]))
    with pytest.raises(ValueError, match="Unsafe"):
        safe_extract_artifacts(archive, tmp_path / "artifacts")
    assert not (tmp_path / "escape").exists()


def test_guest_artifacts_preserve_hidden_coverage_files(tmp_path):
    from pancake_conformance.gui_vm import safe_extract_artifacts
    archive = tmp_path / "guest.tar"
    archive.write_bytes(tar_bytes([("./coverage/.coverage", tarfile.REGTYPE, b"sqlite data"),
                                  ("report.json", tarfile.REGTYPE, b"{}")]))
    destination = tmp_path / "artifacts"
    safe_extract_artifacts(archive, destination)
    assert (destination / "coverage/.coverage").read_bytes() == b"sqlite data"
    assert (destination / "report.json").read_text() == "{}"


def test_launchagent_job_uses_guest_cli_and_never_host_gui(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    monkeypatch.setattr("pancake_conformance.gui_vm.shutil.which", lambda name: "/usr/bin/" + name)
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    argv = vm._guest_command(["interface.stack.hybrid"], "targets/example/example.toml", coverage=True, fail_fast=True)
    assert argv[0] == "/Users/admin/pancake-conformance/.venv/bin/pancake-conformance"
    assert "--no-gui-vm" in argv
    assert "--coverage" in argv
    assert "--case" in argv and "interface.stack.hybrid" in argv
    assert "--fail-fast" in argv
    assert not any(str(tmp_path) in token for token in argv)


def test_artifact_hardlinks_must_point_to_declared_regular_files(tmp_path):
    from pancake_conformance.gui_vm import safe_extract_artifacts
    archive = tmp_path / "guest.tar"
    archive.write_bytes(tar_bytes([("frame00.png", tarfile.REGTYPE, b"pixels"),
                                  ("frame01.png", tarfile.LNKTYPE, "frame00.png")]))
    destination = tmp_path / "artifacts"
    safe_extract_artifacts(archive, destination)
    assert (destination / "frame00.png").stat().st_ino == (destination / "frame01.png").stat().st_ino


def test_source_transport_preserves_git_pin_and_excludes_host_credentials(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM, safe_extract_artifacts
    workspace = tmp_path / "workspace"
    target = workspace / "submodules/ExampleStacker"
    (target / "src").mkdir(parents=True)
    (target / "src/__init__.py").write_text("value = 1\n")
    def git(*args):
        return subprocess.run(["git", "-C", str(target), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], capture_output=True, check=True, text=True).stdout.strip()
    git("init", "--quiet")
    git("add", ".")
    git("commit", "--quiet", "-m", "initial")
    git("tag", "v0.1")
    (target / "src/__init__.py").write_text("value = 2\n")
    git("commit", "--quiet", "-am", "second")
    descriptor = workspace / "targets/example/example.toml"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('root = "../../submodules/ExampleStacker"\n')
    for name in ("pyproject.toml", "uv.lock", "README.md", ".python-version"):
        (workspace / name).write_text("" if name == "pyproject.toml" else "fixture\n")
    package = workspace / "src/pancake_conformance"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    runtime = package / "adapters/runtime/.venv/lib"
    runtime.mkdir(parents=True)
    (runtime / "installed.py").write_text("never copy an installed dependency")
    private = workspace / ".ssh"
    private.mkdir()
    (private / "secret_key").write_text("never copy credentials")
    vm = TartGuiVM(config(), workspace, tmp_path / "run")
    archive, relative, target_relative, pin, digest = vm._source_archive(descriptor)
    assert relative == "targets/example/example.toml"
    assert target_relative == "submodules/ExampleStacker"
    assert pin == git("rev-parse", "HEAD") and len(digest) == 64
    guest = tmp_path / "guest"
    safe_extract_artifacts(archive, guest)
    assert not (guest / ".ssh").exists()
    assert not (guest / "src/pancake_conformance/adapters/runtime/.venv").exists()
    clone = guest / "submodules/ExampleStacker/.git"
    subprocess.run(["git", "clone", "--bare", "--quiet", str(guest / ".pancake-conformance-target.bundle"), str(clone)], check=True)
    description = subprocess.run(["git", "--git-dir", str(clone), "describe", "--tags", "--always"], capture_output=True, check=True, text=True).stdout.strip()
    assert description == git("describe", "--tags", "--always")


@pytest.mark.parametrize("project_path", ["pancake-conformance", "nested/pancake-conformance"])
def test_nested_project_transport_preserves_external_reference_paths(tmp_path, monkeypatch, project_path):
    from pancake_conformance.gui_vm import TartGuiVM, safe_extract_artifacts
    workspace = tmp_path / "workspace"
    project = workspace / project_path
    target = workspace / "submodules/ExampleStacker"
    (target / "src").mkdir(parents=True)
    (target / "src/__init__.py").write_text("value = 1\n")
    for arguments in (("init", "--quiet"), ("add", "."), ("commit", "--quiet", "-m", "initial")):
        subprocess.run(["git", "-C", str(target), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.test", *arguments], check=True)
    descriptor = project / "targets/example/example.toml"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text(f'root = "{os.path.relpath(target, descriptor.parent)}"\nadapter = "example-adapter"\n')
    for name in ("pyproject.toml", "uv.lock", "README.md", ".python-version"):
        (project / name).write_text("" if name == "pyproject.toml" else "fixture\n")
    package = project / "src/pancake_conformance"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (workspace / "unrelated-secret").write_text("never copy")
    rewrite = workspace / "pancake"
    rewrite.mkdir(parents=True)
    (rewrite / "app.py").write_text("never copy the application rewrite\n")
    vm = TartGuiVM(config(), workspace, tmp_path / "run", project=project)
    archive, relative, target_relative, _, _ = vm._source_archive(descriptor)
    assert relative == f"{project_path}/targets/example/example.toml"
    assert target_relative == "submodules/ExampleStacker"
    guest = tmp_path / "guest"
    safe_extract_artifacts(archive, guest)
    assert (guest / project_path / "src/pancake_conformance/__init__.py").is_file()
    assert (guest / "submodules/ExampleStacker/src/__init__.py").is_file()
    assert not (guest / "unrelated-secret").exists()
    assert not (guest / "pancake").exists()
    commands = []
    monkeypatch.setattr(vm, "_ssh", lambda command, **kwargs: commands.append(command) or SimpleNamespace(returncode=0))
    vm._sync_workspace(descriptor)
    assert f"cd /Users/admin/pancake-conformance/{project_path} &&" in next(command for command in commands if "uv sync" in command)
    command = vm._guest_command(["interface.case"], relative, coverage=False, fail_fast=False,
                                gui_command=[str(target / "bin/gui")])
    assert command[0] == f"/Users/admin/pancake-conformance/{project_path}/.venv/bin/pancake-conformance"
    assert json.loads(command[command.index("--gui-command") + 1]) == ["/Users/admin/pancake-conformance/submodules/ExampleStacker/bin/gui"]


def test_prepare_rejects_missing_aqua_before_dispatch(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    calls = []
    def ssh(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0 if "id -u" in command else 1, stdout="501\n", stderr="no GUI domain")
    monkeypatch.setattr(vm, "_ssh", ssh)
    clock = [0.0]
    monkeypatch.setattr("pancake_conformance.gui_vm.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("pancake_conformance.gui_vm.time.sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    with pytest.raises(RuntimeError, match="Aqua.*120s"):
        vm._preflight()
    assert not any("uv sync" in command for command in calls)
    assert clock[0] == 120


def test_effective_command_overrides_are_forwarded_with_guest_paths(tmp_path):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    command = vm._guest_command(["interface.case"], "targets/custom.toml", coverage=False, fail_fast=False,
                                cli_command=[str(tmp_path / "bin/custom"), "{python}"],
                                gui_command=["{python}", "-m", "custom.gui"])
    assert json.loads(command[command.index("--cli-command") + 1]) == ["/Users/admin/pancake-conformance/bin/custom", "{python}"]
    assert json.loads(command[command.index("--gui-command") + 1]) == ["{python}", "-m", "custom.gui"]


@pytest.mark.parametrize("runtime", ["", "adapter-runtime"])
def test_guest_uses_declared_runtime_project(tmp_path, monkeypatch, runtime):
    from pancake_conformance.gui_vm import TartGuiVM
    descriptor = tmp_path / "target.toml"
    descriptor.write_text(f'[runtime]\nproject = "{runtime or "."}"\n')
    (tmp_path / (runtime or ".")).mkdir(exist_ok=True)
    archive = tmp_path / "workspace.tar"
    archive.write_bytes(b"archive")
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    monkeypatch.setattr(vm, "_source_archive", lambda path: (archive, "target.toml", "app", "a" * 40, "b" * 64))
    commands = []
    monkeypatch.setattr(vm, "_ssh", lambda command, **kwargs: commands.append(command) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    vm._sync_workspace(descriptor)
    guest_runtime = "/Users/admin/pancake-conformance" + ("/" + runtime if runtime else "")
    sync = next(command for command in commands if "uv sync" in command)
    assert f"cd {guest_runtime} &&" in sync
    assert "--extra" not in sync
    command = vm._guest_command(["interface.case"], "target.toml", coverage=False, fail_fast=False)
    assert command[0] == guest_runtime + "/.venv/bin/pancake-conformance"


def test_guest_rejects_runtime_outside_workspace(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('[runtime]\nproject = ".."\n')
    archive = tmp_path / "workspace.tar"
    archive.write_bytes(b"archive")
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    monkeypatch.setattr(vm, "_source_archive", lambda path: (archive, "target.toml", "app", "a" * 40, "b" * 64))
    calls = []
    monkeypatch.setattr(vm, "_ssh", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="runtime.*workspace"):
        vm._sync_workspace(descriptor)
    assert calls == []


def test_guest_interpreter_pin_overrides_host_python_version_file(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('adapter = ""\n')
    archive = tmp_path / "workspace.tar"
    archive.write_bytes(b"archive")
    vm = TartGuiVM({**config(), "python": "3.12.16"}, tmp_path, tmp_path / "run")
    monkeypatch.setattr(vm, "_source_archive", lambda path: (archive, "target.toml", "app", "a" * 40, "b" * 64))
    commands = []
    monkeypatch.setattr(vm, "_ssh", lambda command, **kwargs: commands.append(command) or SimpleNamespace(returncode=0))
    vm._sync_workspace(descriptor)
    assert "--python 3.12.16" in next(command for command in commands if "uv sync" in command)


def test_vm_lease_rejects_second_owner_and_releases_on_close(tmp_path):
    from pancake_conformance.gui_vm import TartGuiVM
    first = TartGuiVM(config(), tmp_path, tmp_path / "first")
    second = TartGuiVM(config(), tmp_path, tmp_path / "second")
    first._lease_path = second._lease_path = tmp_path / "vm.lock"
    first._acquire_lease()
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            second._acquire_lease()
    finally:
        first.close()
    second._acquire_lease()
    second.close()


def test_vm_prepare_rejects_emulated_or_nonmac_host(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    monkeypatch.setattr("pancake_conformance.gui_vm.platform.system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="native macOS Apple Silicon"):
        vm.prepare()


def test_vm_preflight_rejects_intel_guest(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    def ssh(command, **kwargs):
        output = "501" if "id -u" in command else "Darwin x86_64"
        return SimpleNamespace(returncode=0, stdout=output, stderr="")
    monkeypatch.setattr(vm, "_ssh", ssh)
    with pytest.raises(RuntimeError, match="Darwin arm64"):
        vm._preflight()


def test_guest_job_records_nonpython_pin_without_python_source_directory(tmp_path):
    import sys
    from pancake_conformance.gui_vm import _GUEST_JOB
    job = tmp_path / "job"
    job.mkdir()
    output = tmp_path / "output"
    worker = job / "job.py"
    worker.write_text(_GUEST_JOB)
    child = "import os,pathlib,sys; assert os.environ['PANCAKE_CONFORMANCE_VM_GUEST']=='1'; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/'report.json').write_text('{}'); print('guest only'); sys.exit(1)"
    payload = {"command": [sys.executable, "-c", child, str(output)], "workspace": str(tmp_path),
               "output": str(output), "job": str(job), "source_root": str(tmp_path / "does-not-exist"),
               "target_commit": "a" * 40, "path": "/usr/bin:/bin", "adapter": "",
               "source_bundle_sha256": "b" * 64}
    config_path = job / "job.json"
    config_path.write_text(json.dumps(payload))
    subprocess.run([sys.executable, str(worker), str(config_path)], check=True, timeout=10)
    status = json.loads((job / "status.json").read_text())
    assert status["complete"] is True and status["returncode"] == 1
    assert "source_error" not in status
    assert json.loads((output / "vm-source.json").read_text())["target_commit"] == "a" * 40
    assert "guest only" in (output / "vm-cli.stdout").read_text()


def test_guest_progress_prints_only_new_completed_counts(tmp_path, monkeypatch, capsys):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    payload = {"completed_count": 3, "cases": [{"id": "interface.export", "status": "pending"}]}
    monkeypatch.setattr(vm, "_ssh", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""))
    completed = vm._report_progress(10, 0)
    assert completed == 3
    assert "GUI VM: 3/10 native cases; interface.export pending" in capsys.readouterr().out
    assert vm._report_progress(10, completed) == 3
    assert capsys.readouterr().out == ""


def test_guest_progress_ignores_partial_json_during_report_write(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    monkeypatch.setattr(vm, "_ssh", lambda *a, **kw: SimpleNamespace(returncode=0, stdout='{"cases":', stderr=""))
    assert vm._report_progress(10, 2) == 2


def test_preflight_records_guest_versions_and_sip_without_adding_a_security_gate(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    def ssh(command, **kwargs):
        responses = {"/usr/bin/id -u": "501", "/usr/bin/uname -s -m": "Darwin arm64",
                     "/usr/bin/sw_vers -productVersion": "26.6.2", "/usr/bin/sw_vers -buildVersion": "25G205",
                     "/usr/bin/xcrun --find swiftc": "/Library/Developer/CommandLineTools/usr/bin/swiftc",
                     "/usr/bin/xcrun swift --version": "Apple Swift version 6.3.3",
                     "/usr/bin/csrutil status": "System Integrity Protection status: disabled."}
        output = responses.get(command, "uv 0.13.8")
        return SimpleNamespace(returncode=0, stdout=output, stderr="")
    monkeypatch.setattr(vm, "_ssh", ssh)
    vm._preflight()
    metadata = json.loads((vm.output / "vm-preflight.json").read_text())
    assert metadata["guest"]["architecture"] == "arm64"
    assert metadata["guest"]["os_version"] == "26.6.2"
    assert metadata["guest"]["os_build"] == "25G205"
    assert metadata["guest"]["aqua_uid"] == 501
    assert metadata["guest"]["swift_version"] == "Apple Swift version 6.3.3"
    assert "disabled" in metadata["guest"]["sip_status"]
    assert metadata["checks"]["aqua"] is True


def test_preflight_waits_for_aqua_after_ssh_is_already_available(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM(config(), tmp_path, tmp_path / "run")
    attempts = []
    sleeps = []
    def ssh(command, **kwargs):
        if "launchctl print gui/" in command:
            attempts.append(command)
            return SimpleNamespace(returncode=0 if len(attempts) == 3 else 1, stdout="", stderr="not ready")
        output = "501" if "id -u" in command else "Darwin arm64" if "uname" in command else "available"
        return SimpleNamespace(returncode=0, stdout=output, stderr="")
    monkeypatch.setattr(vm, "_ssh", ssh)
    monkeypatch.setattr("pancake_conformance.gui_vm.time.sleep", lambda seconds: sleeps.append(seconds))
    vm._preflight()
    metadata = json.loads((vm.output / "vm-preflight.json").read_text())
    assert metadata["checks"]["aqua"] is True
    assert metadata["guest"]["aqua_attempts"] == 3
    assert sleeps == [1, 1]
