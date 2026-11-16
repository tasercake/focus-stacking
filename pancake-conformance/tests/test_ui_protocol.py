"""Checks for the external macOS accessibility transport."""
import pytest
import sys
import json
import subprocess


@pytest.mark.skipif(sys.platform != "darwin", reason="Tests Apple native APIs; Linux driver has separate coverage")
def test_native_helper_reports_accessibility_trust(tmp_path):
    from pancake_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    result = subprocess.run([str(helper)], input=json.dumps({"command": "trust"}) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert isinstance(response["result"]["trusted"], bool)


@pytest.mark.skipif(sys.platform != "darwin", reason="Tests Apple native APIs; Linux driver has separate coverage")
def test_native_helper_rejects_unknown_command(tmp_path):
    from pancake_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    result = subprocess.run([str(helper)], input=json.dumps({"command": "not-a-command"}) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "Unknown command" in response["error"]


@pytest.mark.skipif(sys.platform != "darwin", reason="Tests Apple native APIs; Linux driver has separate coverage")
def test_native_helper_returns_error_for_missing_application(tmp_path):
    from pancake_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    request = {"command": "snapshot", "pid": 2147483646}
    result = subprocess.run([str(helper)], input=json.dumps(request) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "application" in response["error"].lower()




def test_native_destination_check_rejects_same_leaf_in_other_directory():
    import pytest
    from pathlib import Path
    from pancake_conformance.macos_ui import assert_directory_breadcrumbs

    destination = Path('/private/tmp/run-123/case')
    assert_directory_breadcrumbs(['case', 'run-123', 'tmp', 'private', 'Macintosh HD'], destination)
    with pytest.raises(AssertionError, match='native destination'):
        assert_directory_breadcrumbs(['case', 'run-456', 'tmp', 'private', 'Macintosh HD'], destination)


def test_open_session_takes_desktop_lease_before_spawning(tmp_path):
    import os
    import sys
    import pytest
    from pancake_conformance.desktop import DesktopLease
    from pancake_conformance.macos_ui import open_session

    marker = tmp_path / 'spawned'
    command = [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("spawned")', str(marker)]
    with DesktopLease():
        with pytest.raises(RuntimeError, match='Native desktop is in use'):
            session = open_session(command, cwd=tmp_path, env=os.environ, directory=tmp_path / 'case')
            session.close()
    assert not marker.exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="Tests Apple native APIs; Linux driver has separate coverage")
def test_native_snapshot_distinguishes_running_process_from_missing_app_registration(tmp_path):
    import sys
    from pancake_conformance.macos_ui import native_helper

    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
    try:
        request = {'command': 'snapshot', 'pid': process.pid}
        result = subprocess.run([str(native_helper(tmp_path))], input=json.dumps(request) + '\n', text=True, capture_output=True, check=True)
        response = json.loads(result.stdout)
        assert response['ok'], response.get('error')
        assert response['result']['pid'] == process.pid
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_select_waits_for_visible_option_and_committed_value(tmp_path):
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    def snapshot(value, popup=False):
        nodes = [{'id': 'export.format', 'role': 'AXMenuButton', 'title': value, 'path': [0], 'size': [200, 30]}]
        if popup:
            nodes.append({'role': 'AXStaticText', 'title': 'TIFF (.tif)', 'path': [1, 0], 'size': [180, 25]})
        return {'nodes': nodes}

    states = iter([snapshot('JPEG (.jpg)'), snapshot('JPEG (.jpg)'),
                   snapshot('JPEG (.jpg)', True), snapshot('JPEG (.jpg)', True), snapshot('TIFF (.tif)')])
    actions, observed = [], []

    class DelayedNativeDriver(MacOSUISession):
        def __init__(self):
            self.process = SimpleNamespace(poll=lambda: None)
            self.directory = tmp_path

        def _request(self, command, **values):
            if command == 'snapshot':
                state = next(states)
                observed.append(state['nodes'][0]['title'])
                return state
            if command == 'attributes':
                return {'_AXActions': []}
            assert command == 'click', f'Unexpected one-shot native operation: {command}'
            actions.append(values['selector'])
            return {'clicked': True}

    driver = DelayedNativeDriver()
    driver.select('export.format', 'TIFF (.tif)')
    assert observed[-1] == 'TIFF (.tif)'
    assert len(actions) == 2
    assert actions[0]['id'] == 'export.format'
    assert actions[1] == {'path': [1, 0]}


def test_select_current_value_sends_no_input(tmp_path):
    from pancake_conformance.macos_ui import MacOSUISession

    class AlreadySelectedDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path

        def _request(self, command, **values):
            assert command == 'snapshot', 'Selecting the current value must not open another popup'
            return {'nodes': [{'id': 'alignment', 'role': 'AXMenuButton', 'title': 'Off', 'path': [0]}]}

    AlreadySelectedDriver().select('alignment', 'Off')


def test_native_path_readiness_waits_for_resolved_selected_suggestion():
    from pathlib import Path
    from pancake_conformance.macos_ui import native_path_ready

    target = Path('/private/tmp/run/case')
    typed_only = {'nodes': [{'id': 'PathTextField', 'role': 'AXTextField', 'value': str(target)}]}
    assert not native_path_ready(typed_only, target)
    resolved = {'nodes': [*typed_only['nodes'],
                         {'path': [0, 1], 'role': 'AXRow', 'selected': True},
                         {'path': [0, 1, 0, 0], 'role': 'AXList', 'id': str(target), 'description': 'path'}]}
    assert native_path_ready(resolved, target)
    assert not native_path_ready(resolved, Path('/private/tmp/other-run/case'))


def test_select_uses_advertised_show_menu_action_for_new_dialog(tmp_path):
    """A first pointer click can focus a new dialog without opening its popup."""
    from pancake_conformance.macos_ui import MacOSUISession

    class NewDialogDriver(MacOSUISession):
        def __init__(self):
            from types import SimpleNamespace
            self.process = SimpleNamespace(poll=lambda: None)
            self.directory = tmp_path
            self.value = '8-bit'
            self.popup = False
            self.actions = []

        def _request(self, command, **values):
            self.actions.append((command, values))
            if command == 'snapshot':
                nodes = [{'id': 'export.depth', 'role': 'AXMenuButton', 'title': self.value,
                          'path': [0], 'size': [291, 30]}]
                if self.popup:
                    nodes.append({'role': 'AXStaticText', 'title': '16-bit',
                                  'path': [1, 0], 'size': [180, 25]})
                return {'nodes': nodes}
            if command == 'attributes':
                return {'_AXActions': ['AXPress', 'AXShowMenu']}
            if command == 'action':
                assert values['action'] == 'AXShowMenu'
                self.popup = True
                return {'performed': True}
            assert command == 'click' and values['selector'] == {'path': [1, 0]}, (
                'A new dialog popup must open through its advertised AXShowMenu action')
            self.value = '16-bit'
            self.popup = False
            return {'clicked': True}

    driver = NewDialogDriver()
    driver.select('export.depth', '16-bit')
    assert driver.value == '16-bit'
    assert not driver.popup
    assert [(command, values.get('action')) for command, values in driver.actions
            if command == 'action'] == [('action', 'AXShowMenu')]


def test_select_rejects_unreadable_native_popup_without_inferred_input(tmp_path):
    import pytest
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    class InvalidPopupDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path
            self.process = SimpleNamespace(poll=lambda: None)
            self.expanded = False
            self.input = []
            self.open_count = 0

        def _request(self, command, **values):
            if command == 'snapshot':
                nodes = [{'id': 'alignment', 'role': 'AXMenuButton', 'title': 'Standard',
                          'path': [1, 0], 'size': [282, 30]}]
                if self.expanded:
                    nodes += [{'path': [0], 'role': 'AXWindow', 'subrole': 'AXDialog',
                               'size': [282, 202]}, {'path': [0, 0]}]
                return {'nodes': nodes}
            if command == 'attributes':
                return {'_AXActions': ['AXShowMenu'], 'AXExpanded': self.expanded}
            if command == 'action':
                self.open_count += 1
                self.expanded = True
                return {'performed': 'AXShowMenu'}
            if command == 'screenshot':
                return {'path': values['path']}
            self.input.append(command)
            raise AssertionError(f'Unreadable popup must not receive inferred input: {command}')

    driver = InvalidPopupDriver()
    with pytest.raises(TimeoutError, match='visible popup option'):
        driver.select('alignment', 'Focus breathing', timeout=0.01)
    assert driver.input == []
    assert driver.open_count == 1


def test_node_waits_for_delayed_native_control_publication(tmp_path):
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    expected = {'id': 'export.depth', 'role': 'AXMenuButton', 'title': '16-bit', 'path': [0, 4]}

    class DelayedControlDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path
            self.process = SimpleNamespace(poll=lambda: None)
            self.snapshots = 0

        def _request(self, command, **values):
            assert command == 'snapshot', 'Control lookup must not repeat application input'
            self.snapshots += 1
            return {'nodes': [expected] if self.snapshots == 3 else [{'path': [0, 4]}]}

    driver = DelayedControlDriver()
    assert driver.node('export.depth') == expected
    assert driver.snapshots == 3


def test_node_rejects_ambiguous_selector_without_waiting(tmp_path):
    import pytest
    from pancake_conformance.macos_ui import MacOSUISession

    class AmbiguousDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path
            self.snapshots = 0

        def _request(self, command, **values):
            assert command == 'snapshot'
            self.snapshots += 1
            return {'nodes': [{'id': 'export.depth', 'path': [0]}, {'id': 'export.depth', 'path': [1]}]}

    driver = AmbiguousDriver()
    with pytest.raises(AssertionError, match='found 2'):
        driver.node('export.depth')
    assert driver.snapshots == 1


def test_node_missing_control_times_out_without_input(tmp_path):
    import pytest
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    class MissingDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path
            self.process = SimpleNamespace(poll=lambda: None)

        def _request(self, command, **values):
            assert command in ('snapshot', 'screenshot'), 'Missing control must not trigger input'
            return {'nodes': []} if command == 'snapshot' else {'path': values['path']}

    with pytest.raises(TimeoutError, match='UI element'):
        MissingDriver().node('export.depth', timeout=0.01)


def test_lifecycle_uses_public_menu_state_when_progress_children_are_unreadable(monkeypatch):
    from types import SimpleNamespace
    from pancake_conformance.cases import interface
    from pancake_conformance.macos_ui import find_node

    class NativeMenuUI:
        def __init__(self):
            self.state = 'idle'
            self.starts = 0
            self.actions = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def snapshot(self):
            busy = self.state in ('running', 'paused')
            return {'nodes': [
                {'id': 'stack.start', 'enabled': not busy},
                {'id': 'export.start', 'enabled': self.state == 'done'},
                {'id': 'stack.resume' if self.state == 'paused' else 'stack.pause', 'enabled': busy},
                {'id': 'stack.stop', 'enabled': busy},
                {'path': [0, 0, 35]}, {'path': [0, 0, 36]},
            ]}

        def node(self, selector):
            return find_node(self.snapshot(), selector)

        def wait(self, condition, **kwargs):
            result = condition(self.snapshot())
            assert result, kwargs.get('description')
            return result

        def action(self, selector):
            return self.click(selector)

        def click(self, selector, **kwargs):
            self.actions.append(selector)
            if selector == 'stack.start':
                self.starts += 1
                self.state = 'done' if self.starts == 2 else 'running'
            else:
                expected, replacement = {'stack.pause': ('running', 'paused'), 'stack.resume': ('paused', 'running'),
                                         'stack.stop': ('running', 'idle')}[selector]
                assert self.state == expected
                self.state = replacement

    ui = NativeMenuUI()
    context = SimpleNamespace(fixture=lambda _: SimpleNamespace(paths=()), open_ui=lambda **_: ui)
    monkeypatch.setattr(interface, '_prepare_lifecycle', lambda *args: None)
    interface._lifecycle(context)
    assert [action for action in ui.actions if action != 'stack.start'] == ['stack.pause', 'stack.resume', 'stack.stop']
    assert ui.starts == 2
    assert ui.state == 'done'


def _shutdown_session(tmp_path, process):
    import io
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    class Session(MacOSUISession):
        def __enter__(self):
            return self

        def snapshot(self):
            raise RuntimeError('Target has already exited')

    session = Session.__new__(Session)
    session.directory = tmp_path
    session.process = process
    session._helper = SimpleNamespace(pid=0, poll=lambda: 0, wait=lambda **_: 0,
                                      stdin=io.StringIO(), stdout=io.StringIO())
    session._trace, session._stderr = io.StringIO(), io.StringIO()
    session._target_logs = (io.StringIO(), io.StringIO())
    released = []
    session._desktop_lease = SimpleNamespace(release=lambda: released.append(True))
    return session, released


def test_close_rejects_real_natural_nonzero_exit_and_records_shutdown(tmp_path):
    import sys
    import pytest

    process = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(7)'])
    process.wait(timeout=5)
    session, released = _shutdown_session(tmp_path, process)
    with pytest.raises(RuntimeError, match='Native GUI target exited with status 7'):
        session.close()
    status = json.loads((tmp_path / 'shutdown.json').read_text())
    assert status['returncode'] == 7
    assert status['forced'] is False
    assert status['status'] == 'failed'
    assert released == [True]
    assert all(stream.closed for stream in (session._trace, session._stderr, *session._target_logs,
                                           session._helper.stdin, session._helper.stdout))


def test_close_rejects_sigsegv_and_preserves_body_failure(tmp_path):
    import signal
    import pytest
    from types import SimpleNamespace

    process = SimpleNamespace(pid=12345, returncode=-signal.SIGSEGV,
                              poll=lambda: -signal.SIGSEGV, wait=lambda **_: -signal.SIGSEGV)
    session, released = _shutdown_session(tmp_path, process)
    with pytest.raises(AssertionError, match='Original body failure') as raised:
        with session:
            raise AssertionError('Original body failure')
    assert any('status -11' in note for note in raised.value.__notes__)
    status = json.loads((tmp_path / 'shutdown.json').read_text())
    assert status['returncode'] == -signal.SIGSEGV
    assert status['forced'] is False
    assert status['status'] == 'failed'
    assert released == [True]
    assert all(stream.closed for stream in (session._trace, session._stderr, *session._target_logs,
                                           session._helper.stdin, session._helper.stdout))


def test_close_records_intentional_harness_termination_separately(tmp_path):
    import sys
    import signal

    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
    try:
        session, released = _shutdown_session(tmp_path, process)
        session.close()
        status = json.loads((tmp_path / 'shutdown.json').read_text())
        assert status['returncode'] == -signal.SIGTERM
        assert status['forced'] is True
        assert status['status'] == 'forced'
        assert released == [True]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_close_releases_all_streams_and_lease_when_helper_cleanup_fails(tmp_path):
    import pytest
    from types import SimpleNamespace

    process = SimpleNamespace(pid=12345, returncode=0, poll=lambda: 0, wait=lambda **_: 0)
    session, released = _shutdown_session(tmp_path, process)

    def reap(candidate, timeout=5):
        if candidate is session._helper:
            raise RuntimeError('Helper cleanup failed')
        return False

    session._reap = reap
    with pytest.raises(RuntimeError, match='Helper cleanup failed'):
        session.close()
    assert released == [True]
    assert all(stream.closed for stream in (session._trace, session._stderr, *session._target_logs,
                                           session._helper.stdin, session._helper.stdout))


def test_close_records_clean_zero_exit(tmp_path):
    from types import SimpleNamespace

    process = SimpleNamespace(pid=12345, returncode=0, poll=lambda: 0, wait=lambda **_: 0)
    session, released = _shutdown_session(tmp_path, process)
    session.close()
    assert json.loads((tmp_path / 'shutdown.json').read_text()) == {
        'pid': 12345, 'returncode': 0, 'forced': False, 'status': 'clean',
    }
    assert released == [True]


def test_forced_cleanup_never_excuses_a_concurrent_sigsegv(tmp_path):
    import signal
    import pytest
    from types import SimpleNamespace

    process = SimpleNamespace(pid=12345, returncode=-signal.SIGSEGV,
                              poll=lambda: -signal.SIGSEGV, wait=lambda **_: -signal.SIGSEGV)
    session, _ = _shutdown_session(tmp_path, process)
    session._reap = lambda *args, **kwargs: True
    with pytest.raises(RuntimeError, match='status -11'):
        session.close()
    status = json.loads((tmp_path / 'shutdown.json').read_text())
    assert status['forced'] is True
    assert status['status'] == 'failed'


def _live_shutdown_session(tmp_path):
    from types import SimpleNamespace
    import signal

    process = SimpleNamespace(pid=12345, returncode=None)
    process.poll = lambda: process.returncode

    def wait(timeout=None):
        if process.returncode is None:
            raise subprocess.TimeoutExpired('native target', timeout)
        return process.returncode

    process.wait = wait
    session, released = _shutdown_session(tmp_path, process)
    session._helper.poll = lambda: None

    def reap(candidate, timeout=5):
        if candidate is process and process.returncode is None:
            process.returncode = -signal.SIGTERM
            return True
        return False

    session._reap = reap
    return session, released


def test_close_waits_for_published_enabled_confirmation_then_presses_once(tmp_path):
    session, released = _live_shutdown_session(tmp_path)
    keys, presses, snapshots = [], [], []
    session.key = lambda key, modifiers: keys.append((key, modifiers))

    def snapshot():
        snapshots.append(True)
        nodes = ([{'path': [0, 0]}] if len(snapshots) == 1 else
                 [{'path': [0, 2], 'role': 'AXButton', 'title': 'Quit Anyway',
                   'enabled': len(snapshots) >= 3}])
        return {'nodes': nodes}

    def click(selector, *, physical=True):
        assert len(snapshots) == 3, 'Confirmation must be published and enabled before input'
        assert physical is False, 'Close confirmation uses its native AX press action'
        presses.append(selector)
        session.process.returncode = 0

    session.snapshot, session.click = snapshot, click
    session.close()
    assert keys == [('w', ('command',))]
    assert len(presses) == 1
    assert released == [True]
    assert json.loads((tmp_path / 'shutdown.json').read_text())['status'] == 'clean'


def test_close_skips_dialog_lookup_after_normal_exit(tmp_path):
    session, released = _live_shutdown_session(tmp_path)
    keys = []

    def key(value, modifiers):
        keys.append(value)
        session.process.returncode = 0

    def snapshot():
        raise AssertionError('Exited application must not receive a dialog query')

    session.key, session.snapshot = key, snapshot
    session.close()
    assert keys == ['w']
    assert released == [True]
    assert json.loads((tmp_path / 'shutdown.json').read_text())['status'] == 'clean'


def test_close_records_native_input_failure_without_retrying(tmp_path):
    session, released = _live_shutdown_session(tmp_path)
    keys = []

    def key(value, modifiers):
        keys.append(value)
        raise RuntimeError('Native close input failed')

    session.key = key
    session.close()
    assert keys == ['w']
    assert released == [True]
    status = json.loads((tmp_path / 'shutdown.json').read_text())
    assert status['status'] == 'forced'
    assert status['close_error'] == 'Native close input failed'


@pytest.mark.skipif(sys.platform != "darwin", reason="Tests Apple native APIs; Linux driver has separate coverage")
def test_scroll_event_targets_requested_viewport_before_native_post(tmp_path):
    """Compile the real Swift event construction; never post host input."""
    from pathlib import Path
    from pancake_conformance import macos_ui

    source = Path(macos_ui.__file__).with_name('native_macos.swift').read_text()
    operation = source.split('    if command == "scroll" {', 1)[1].split('        return ["scrolled":true]', 1)[0]
    construction = '\n'.join(line for line in operation.splitlines()
                             if 'let p =' not in line and 'let dy =' not in line)
    # Only event construction is executed. Pointer movement and native posting
    # stay outside this read-only SDK regression test.
    construction = construction.replace('event?.post(tap:.cghidEventTap)', '')
    assert 'pointer(' not in construction and '.post(' not in construction
    script = tmp_path / 'scroll-construction.swift'
    script.write_text('import CoreGraphics\n'
                      'let inputSource = CGEventSource(stateID: .privateState)\n'
                      'let request: [String: Any] = [:]\n'
                      'let dy = 120\n'
                      'for p in [CGPoint(x:321,y:654), CGPoint(x:789,y:123)] {\n'
                      + construction + '\n'
                      'print("\\(event!.location.x),\\(event!.location.y),\\(event!.getIntegerValueField(.scrollWheelEventIsContinuous))")\n'
                      '}\n')
    result = subprocess.run(['swift', str(script)], capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == ['321.0,654.0,1', '789.0,123.0,1'], 'Native scroll inherited stale pointer coordinates'


def test_select_retries_advertised_press_only_when_show_menu_remains_collapsed(tmp_path):
    from types import SimpleNamespace
    from pancake_conformance.macos_ui import MacOSUISession

    class CollapsedDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path
            self.process = SimpleNamespace(poll=lambda: None)
            self.expanded = self.chosen = False
            self.actions = []
        def _request(self, command, **values):
            if command == 'snapshot':
                nodes = [{'id': 'alignment', 'role': 'AXMenuButton', 'title': 'Focus breathing' if self.chosen else 'Standard',
                          'path': [0], 'size': [200, 30]}]
                if self.expanded:
                    nodes.append({'role': 'AXMenuItem', 'title': 'Focus breathing', 'path': [1], 'size': [200, 30]})
                return {'nodes': nodes}
            if command == 'attributes':
                return {'_AXActions': ['AXShowMenu', 'AXPress'], 'AXExpanded': self.expanded}
            if command == 'action':
                self.actions.append(values['action'])
                self.expanded = values['action'] == 'AXPress'
                return {'performed': values['action']}
            if command == 'click':
                assert self.expanded and values['selector'] == {'path': [1]}
                self.chosen, self.expanded = True, False
                return {}
            if command == 'screenshot':
                return {}
            raise AssertionError(command)
    driver = CollapsedDriver()
    driver.select('alignment', 'Focus breathing', timeout=.01)
    assert driver.actions == ['AXShowMenu', 'AXPress']
    assert driver.chosen


def test_lifecycle_configures_motion_before_bulk_native_import(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from pancake_conformance.cases import interface
    calls = []
    class UI:
        def select(self, key, value):
            calls.append(('select', key, value))
        def action(self, name):
            assert calls == [('select', 'alignment', 'breathing')]
            calls.append(('action', name))
        def wait(self, predicate, **kwargs):
            assert predicate({'nodes': [{'id': 'open-panel'}]})
        def navigate_folder(self, path):
            calls.append(('folder', path))
        def click(self, name, **kwargs):
            calls.append(('click', name))
        def observe(self, name, snapshot=None):
            assert name == 'source_total', 'Virtualized AX rows are not the imported image count'
            return 64
    monkeypatch.setattr(interface, '_prepare', lambda ui, method, mode: calls.append(('prepare', method, mode)))
    fixture = SimpleNamespace(paths=[Path('/fixture/frame.png')]*64)
    interface._prepare_lifecycle(UI(), fixture)
    assert calls[-1] == ('prepare', 'laplacian', 'breathing')
    assert ('folder', Path('/fixture')) in calls
