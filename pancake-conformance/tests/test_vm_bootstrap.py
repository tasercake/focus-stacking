"""Bootstrap boundaries: local installs, owned guests, and exact visual actions."""
import hashlib
import io
import tarfile

import pytest


def test_tart_archive_is_verified_before_extracting(tmp_path):
    from pancake_conformance.vm_bootstrap import install_archive
    archive = tmp_path / 'tart.tar.gz'
    archive.write_bytes(b'not trusted')
    with pytest.raises(RuntimeError, match='checksum'):
        install_archive(archive, tmp_path / 'install', '0' * 64)
    assert not (tmp_path / 'install').exists()


def test_tart_archive_rejects_escape_and_preserves_app_bundle(tmp_path):
    from pancake_conformance.vm_bootstrap import install_archive
    archive = tmp_path / 'tart.tar.gz'
    with tarfile.open(archive, 'w:gz') as stream:
        item = tarfile.TarInfo('../escape')
        item.size = 1
        stream.addfile(item, io.BytesIO(b'x'))
    with pytest.raises((RuntimeError, tarfile.FilterError)):
        install_archive(archive, tmp_path / 'bad', hashlib.sha256(archive.read_bytes()).hexdigest())
    with tarfile.open(archive, 'w:gz') as stream:
        for name in ('tart.app/Contents/MacOS/tart', 'tart.app/Contents/embedded.provisionprofile'):
            item = tarfile.TarInfo(name)
            item.size = 1
            item.mode = 0o755
            stream.addfile(item, io.BytesIO(b'x'))
    binary = install_archive(archive, tmp_path / 'good', hashlib.sha256(archive.read_bytes()).hexdigest())
    assert binary.relative_to(tmp_path / 'good').as_posix() == 'tart.app/Contents/MacOS/tart'
    assert (binary.parent.parent / 'embedded.provisionprofile').exists()


def test_vnc_endpoint_must_be_loopback():
    from pancake_conformance.vm_bootstrap import vnc_endpoint
    assert vnc_endpoint('VNC server: vnc://:secret@127.0.0.1:5901') == ('127.0.0.1::5901', 'secret')
    with pytest.raises(RuntimeError, match='loopback'):
        vnc_endpoint('vnc://:secret@192.168.1.2:5901')


def test_visual_click_requires_one_exact_label():
    from pancake_conformance.vm_bootstrap import label_position
    labels = [('Allow', (.5, .2, .2, .1)), ("Don’t Allow", (.1, .2, .2, .1))]
    assert label_position(labels, 'Allow', (1000, 800)) == (600, 600)
    assert label_position(labels, 'Missing', (1000, 800)) is None
    with pytest.raises(RuntimeError, match='Ambiguous'):
        label_position(labels + labels, 'Allow', (1000, 800))


def test_custom_existing_vm_is_not_provisioned(tmp_path, monkeypatch):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    vm = SimpleNamespace(name='personal', config={}, _tart='/bin/tart', output=tmp_path,
                         _execute=lambda *a, **kw: SimpleNamespace(returncode=0))
    bootstrap = Bootstrap(vm, cache=tmp_path / 'cache')
    bootstrap.ensure_host_and_vm()
    assert not bootstrap.managed
    assert not (tmp_path / 'cache').exists()


def test_new_guest_is_marked_before_clone_and_never_overwrites(tmp_path):
    from pancake_conformance.vm_bootstrap import Bootstrap, IMAGE
    from types import SimpleNamespace
    calls = []
    def execute(argv, **kwargs):
        calls.append(argv)
        if 'get' in argv:
            return SimpleNamespace(returncode=1)
        assert (tmp_path / 'guests' / 'fresh.json').is_file()
        return SimpleNamespace(returncode=0)
    vm = SimpleNamespace(name='fresh', config={}, _tart='/bin/tart', output=tmp_path, _execute=execute)
    bootstrap = Bootstrap(vm, cache=tmp_path)
    bootstrap.ensure_host_and_vm()
    assert bootstrap.managed
    clone = next(c for c in calls if 'clone' in c)
    assert IMAGE in clone and 'TART_NO_AUTO_PRUNE=1' in clone
    assert '--overwrite' not in clone


def test_permission_probe_checks_actual_runtime_and_all_permissions():
    from pancake_conformance.vm_bootstrap import permission_probe
    script = permission_probe('/Users/admin/result.json')
    assert 'native_helper' in script
    assert 'CGRequestScreenCaptureAccess' in script
    assert 'System Events' in script
    assert 'screencapture' in script
    compile(script, '<guest probe>', 'exec')


def test_guest_visual_client_never_connects_to_nonlocal_endpoint(tmp_path):
    from pancake_conformance.vm_bootstrap import GuestScreen
    with pytest.raises(RuntimeError, match='loopback'):
        GuestScreen('vnc://:secret@8.8.8.8:5900', tmp_path)


def test_permission_result_requires_every_check():
    from pancake_conformance.vm_bootstrap import permissions_ready
    result = {'trust': {'trusted': True, 'post_event_access': True}, 'screen': True,
              'automation': True, 'screenshot': True}
    assert permissions_ready(result)
    for key in ('screen', 'automation', 'screenshot'):
        assert not permissions_ready({**result, key: False})
    assert not permissions_ready({**result, 'trust': {'trusted': True}})
    assert not permissions_ready({})


def test_bootstrap_default_is_workspace_independent(tmp_path):
    from pancake_conformance.gui_vm import TartGuiVM
    first = TartGuiVM({}, tmp_path / 'one', tmp_path / 'out1')
    second = TartGuiVM({}, tmp_path / 'two', tmp_path / 'out2')
    assert first.name == second.name == 'pancake-conformance'


def test_permissions_are_checked_after_runtime_sync(tmp_path, monkeypatch):
    from pancake_conformance.gui_vm import TartGuiVM
    vm = TartGuiVM({}, tmp_path, tmp_path / 'run')
    events = []
    monkeypatch.setattr(vm, 'prepare', lambda: None)
    vm._bootstrap.managed = True
    monkeypatch.setattr(vm, '_sync_workspace', lambda path: events.append('sync') or ('target.toml', 'target', 'pin'))
    monkeypatch.setattr(vm._bootstrap, 'ensure_permissions', lambda: events.append('permissions'))
    monkeypatch.setattr(vm._bootstrap, '_configure_display', lambda: events.append('display'))
    def command(*args, **kwargs):
        assert events == ['sync', 'permissions', 'display']
        raise RuntimeError('checked')
    monkeypatch.setattr(vm, '_guest_command', command)
    with pytest.raises(RuntimeError, match='checked'):
        vm.run_cases(['interface.smoke'], target_path=tmp_path / 'target.toml')


def test_visual_menu_label_tolerates_ocr_spaces():
    from pancake_conformance.vm_bootstrap import label_position
    assert label_position([('Util ities', (.1, .8, .1, .1))], 'Utilities', (1000, 800)) == (150, 120)


def test_recovery_flow_only_enables_sip(tmp_path, monkeypatch):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    events = []
    screen = SimpleNamespace(click=lambda text, **kw: events.append(('click', text)) or True,
                             wait_text=lambda text, **kw: events.append(('wait', text)),
                             text=lambda text: events.append(('type', text)), close=lambda: None)
    enabled = False
    def ssh(*a, **kw):
        return SimpleNamespace(stdout='System Integrity Protection status: enabled.' if enabled else 'disabled')
    vm = SimpleNamespace(name='fresh', user='admin', output=tmp_path, _ssh=ssh, _wait_for_ssh=lambda: None,
                         _uid='501', _wait_for_aqua=lambda uid: None, _process=None)
    bootstrap = Bootstrap(vm, cache=tmp_path)
    def restart(*, recovery=False):
        nonlocal enabled
        enabled = not recovery
    monkeypatch.setattr(bootstrap, '_restart', restart)
    monkeypatch.setattr(bootstrap, 'screen', lambda: screen)
    bootstrap._restore_sip()
    assert ('type', 'csrutil enable\n') in events
    assert ('type', 'halt\n') in events
    assert not any('disable' in str(e) for e in events)


def test_visual_capture_reconnects_after_boot_timeout(tmp_path, monkeypatch):
    from pancake_conformance.vm_bootstrap import GuestScreen
    from types import SimpleNamespace
    events = []
    screen = object.__new__(GuestScreen)
    screen.path = tmp_path / 'screen.png'
    screen.endpoint, screen.password = '127.0.0.1::5901', 'secret'
    def capture(path):
        raise TimeoutError('booting')
    screen.client = SimpleNamespace(captureScreen=capture, disconnect=lambda: events.append('disconnect'))
    monkeypatch.setattr('vncdotool.api.connect', lambda *a, **kw: events.append('reconnect') or screen.client)
    assert screen.labels() == ([], (1, 1))
    assert events == ['disconnect', 'reconnect']


def test_tart_install_requires_embedded_profile(tmp_path):
    from pancake_conformance.vm_bootstrap import install_archive
    archive = tmp_path / 'incomplete.tar.gz'
    with tarfile.open(archive, 'w:gz') as stream:
        item = tarfile.TarInfo('tart.app/Contents/MacOS/tart')
        item.size = 1
        stream.addfile(item, io.BytesIO(b'x'))
    with pytest.raises(RuntimeError, match='app bundle'):
        install_archive(archive, tmp_path / 'install', hashlib.sha256(archive.read_bytes()).hexdigest())
    assert not (tmp_path / 'install').exists()


def test_concurrent_guests_share_one_tart_install(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from pancake_conformance import vm_bootstrap
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:gz') as stream:
        for name in ('tart.app/Contents/MacOS/tart', 'tart.app/Contents/embedded.provisionprofile'):
            member = tarfile.TarInfo(name)
            member.size = 1
            stream.addfile(member, io.BytesIO(b'x'))
    payload = archive.getvalue()
    downloads = []
    def download(*args, **kwargs):
        downloads.append(True)
        return io.BytesIO(payload)
    monkeypatch.setattr(vm_bootstrap, 'urlopen', download)
    monkeypatch.setattr(vm_bootstrap, 'TART_SHA256', hashlib.sha256(payload).hexdigest())
    def setup(name):
        vm = SimpleNamespace(name=name, config={}, _tart=None, output=tmp_path,
                             _execute=lambda *a, **kw: SimpleNamespace(returncode=0))
        vm_bootstrap.Bootstrap(vm, cache=tmp_path).ensure_host_and_vm()
        return vm._tart
    with ThreadPoolExecutor(2) as pool:
        binaries = list(pool.map(setup, ('one', 'two')))
    assert len(downloads) == 1
    assert binaries[0] == binaries[1]


def test_each_frame_uses_a_new_vnc_connection(tmp_path, monkeypatch):
    from pancake_conformance.vm_bootstrap import GuestScreen
    from types import SimpleNamespace
    screen = object.__new__(GuestScreen)
    screen.path = tmp_path / 'screen.png'
    screen.endpoint, screen.password = '127.0.0.1::5901', 'secret'
    events = []
    client = SimpleNamespace(captureScreen=lambda path: events.append('capture'),
                             disconnect=lambda: events.append('disconnect'))
    screen.client = client
    monkeypatch.setattr('vncdotool.api.connect', lambda *a, **kw: events.append('connect') or client)
    assert screen._capture()
    assert screen._capture()
    assert events == ['disconnect', 'connect', 'capture', 'disconnect', 'connect', 'capture']


def test_bootstrap_approves_only_expected_python_prompt(tmp_path):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    bootstrap = Bootstrap(SimpleNamespace(), cache=tmp_path)
    clicks = []
    labels = [('"python3.12" is requesting to', (0, 0, 1, 1)),
              ('access your screen and audio.', (0, 0, 1, 1))]
    screen = SimpleNamespace(labels=lambda: (labels, (1000, 800)),
                             click=lambda text, **kw: clicks.append(text) or True)
    assert bootstrap._approve_prompt(screen)
    assert clicks == ['Allow']
    labels[:] = [('Safari wants access to your screen', (0, 0, 1, 1))]
    assert not bootstrap._approve_prompt(screen)
    assert clicks == ['Allow']


def test_bootstrap_rejects_wrong_guest_display(tmp_path):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    vm = SimpleNamespace(output=tmp_path, _ssh=lambda *a, **kw: SimpleNamespace(stdout='{"width":1024,"height":768,"pixel_width":2048,"pixel_height":1536}'))
    with pytest.raises(RuntimeError, match='1440'):
        Bootstrap(vm, cache=tmp_path)._configure_display()


def test_bootstrap_records_verified_guest_display(tmp_path):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    vm = SimpleNamespace(output=tmp_path, _ssh=lambda *a, **kw: SimpleNamespace(stdout='{"width":1440,"height":1000,"pixel_width":2880,"pixel_height":2000}'))
    Bootstrap(vm, cache=tmp_path)._configure_display()
    import json
    assert json.loads((tmp_path / 'vm-display.json').read_text())['pixel_width'] == 2880


def test_display_is_verified_after_configuring_process_exits(tmp_path):
    from pancake_conformance.vm_bootstrap import Bootstrap
    from types import SimpleNamespace
    responses = iter(['{"width":1440,"height":1000,"pixel_width":2880,"pixel_height":2000}',
                      '{"width":1024,"height":768,"pixel_width":2048,"pixel_height":1536}'])
    vm = SimpleNamespace(output=tmp_path, _ssh=lambda *a, **kw: SimpleNamespace(stdout=next(responses)))
    with pytest.raises(RuntimeError, match='1440'):
        Bootstrap(vm, cache=tmp_path)._configure_display()
