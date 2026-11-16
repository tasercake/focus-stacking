"""Portable routing and platform configuration regressions."""
import sys
from contextlib import contextmanager

import pytest


def test_platform_overrides_merge_without_changing_other_platforms(tmp_path, monkeypatch):
    from pancake_conformance.target import TargetSpec
    descriptor = tmp_path / 'target.toml'
    descriptor.write_text('''schema_version=1
name="example"
root="."
cli=["stack"]
[env]
SHARED="yes"
[ui.controls]
settings={title="Preferences"}
[platforms.linux.env]
QT_QPA_PLATFORM="xcb"
[platforms.linux.ui.controls]
settings={title="Settings"}
''')
    monkeypatch.setattr(sys, 'platform', 'linux')
    target = TargetSpec.load(descriptor)
    assert target.env == {'SHARED': 'yes', 'QT_QPA_PLATFORM': 'xcb'}
    assert target.ui['controls']['settings'] == {'title': 'Settings'}
    monkeypatch.setattr(sys, 'platform', 'darwin')
    target = TargetSpec.load(descriptor)
    assert target.env == {'SHARED': 'yes'}
    assert target.ui['controls']['settings'] == {'title': 'Preferences'}


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux desktop routing')
def test_linux_cli_owns_desktop_and_passes_isolated_environment(tmp_path, monkeypatch):
    from pancake_conformance import cli
    from pancake_conformance.model import Case
    events = []
    @contextmanager
    def desktop(directory, environment):
        events.append('start')
        try:
            yield {**environment, 'DISPLAY': ':123', 'DBUS_SESSION_BUS_ADDRESS': 'private'}
        finally:
            events.append('stop')
    def case(context):
        assert context._environment['DISPLAY'] == ':123'
        assert context._environment['DBUS_SESSION_BUS_ADDRESS'] == 'private'
        events.append('case')
    descriptor = tmp_path / 'target.toml'
    descriptor.write_text('schema_version=1\nname="example"\nroot="."\ncli=["unused"]\n')
    monkeypatch.setattr(cli, 'catalog', lambda: [Case('interface.example', 'interface', case)])
    monkeypatch.setattr('pancake_conformance.linux_ui.isolated_desktop', desktop)
    assert cli.main(['run', '--target', str(descriptor), '--output', str(tmp_path / 'run')]) == 0
    assert events == ['start', 'case', 'stop']


def test_linux_desktop_reports_missing_dependencies_before_starting(tmp_path, monkeypatch):
    from pancake_conformance.linux_ui import isolated_desktop
    monkeypatch.setattr('pancake_conformance.linux_ui.shutil.which', lambda command: None)
    with pytest.raises(RuntimeError, match='Xvfb'):
        with isolated_desktop(tmp_path, {}):
            pytest.fail('Missing desktop dependencies were accepted')


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux desktop boundary')
def test_linux_open_session_never_launches_on_inherited_host_display(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import open_session
    released = []
    lease = SimpleNamespace(acquire=lambda: lease, release=lambda: released.append(True))
    monkeypatch.setattr('pancake_conformance.desktop.DesktopLease', lambda: lease)
    monkeypatch.setattr('pancake_conformance.macos_ui.subprocess.Popen',
                        lambda *args, **kwargs: pytest.fail('Target launched on host display'))
    with pytest.raises(RuntimeError, match='isolated desktop'):
        open_session(['unused'], cwd=tmp_path, env={'DISPLAY': ':0'}, directory=tmp_path)
    assert released == [True]


def test_dbus_services_inherit_private_display_and_home(tmp_path, monkeypatch):
    """D-Bus activation must never launch a file manager on the inherited desktop."""
    import io
    import os
    from types import SimpleNamespace
    from pancake_conformance.linux_ui import isolated_desktop
    launched, stopped = [], []
    def launch(command, **kwargs):
        launched.append((command, dict(kwargs.get('env', {}))))
        if command[0] == 'Xvfb':
            os.write(kwargs['pass_fds'][0], b'123\n')
        return SimpleNamespace(stdout=io.StringIO('unix:path=private-bus\n') if command[0] == 'dbus-daemon' else None)
    monkeypatch.setattr('pancake_conformance.linux_ui.shutil.which', lambda name: name)
    monkeypatch.setattr('pancake_conformance.linux_ui.subprocess.Popen', launch)
    monkeypatch.setattr('pancake_conformance.linux_ui.subprocess.run',
                        lambda *args, **kwargs: SimpleNamespace(stdout='window id # 1'))
    monkeypatch.setattr('pancake_conformance.linux_ui.MacOSUISession._reap', stopped.append)
    with isolated_desktop(tmp_path, {'DISPLAY': ':0', 'HOME': '/original', 'AT_SPI_BUS_ADDRESS': 'host'}) as environment:
        bus = next(env for command, env in launched if command[0] == 'dbus-daemon')
        assert bus['DISPLAY'] == environment['DISPLAY'] == ':123'
        assert 'AT_SPI_BUS_ADDRESS' not in bus
        assert 'DBUS_SESSION_BUS_ADDRESS' not in bus
        assert bus['HOME'] == str(tmp_path / 'home')
        assert bus['XDG_RUNTIME_DIR'] == str(tmp_path / 'runtime')
        assert environment['DBUS_SESSION_BUS_ADDRESS'] == 'unix:path=private-bus'
    assert len(stopped) == 3
