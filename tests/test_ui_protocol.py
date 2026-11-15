"""Checks for the external macOS accessibility transport."""
import json
import subprocess


def test_native_helper_reports_accessibility_trust(tmp_path):
    from stack_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    result = subprocess.run([str(helper)], input=json.dumps({"command": "trust"}) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert isinstance(response["result"]["trusted"], bool)


def test_native_helper_rejects_unknown_command(tmp_path):
    from stack_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    result = subprocess.run([str(helper)], input=json.dumps({"command": "not-a-command"}) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "Unknown command" in response["error"]


def test_native_helper_returns_error_for_missing_application(tmp_path):
    from stack_conformance.macos_ui import native_helper

    helper = native_helper(tmp_path)
    request = {"command": "snapshot", "pid": 2147483646}
    result = subprocess.run([str(helper)], input=json.dumps(request) + "\n", text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "application" in response["error"].lower()


def test_ui_identifier_contract_is_unique():
    from stack_conformance.adapters.chimpstackr_ui import IDENTIFIER_CONTRACT

    assert len(IDENTIFIER_CONTRACT) == len(set(IDENTIFIER_CONTRACT))
    assert {"main.window", "stack.start", "export.start", "viewer", "alignment", "method.hybrid"} <= set(IDENTIFIER_CONTRACT)


def test_native_destination_check_rejects_same_leaf_in_other_directory():
    import pytest
    from pathlib import Path
    from stack_conformance.macos_ui import assert_directory_breadcrumbs

    destination = Path('/private/tmp/run-123/case')
    assert_directory_breadcrumbs(['case', 'run-123', 'tmp', 'private', 'Macintosh HD'], destination)
    with pytest.raises(AssertionError, match='native destination'):
        assert_directory_breadcrumbs(['case', 'run-456', 'tmp', 'private', 'Macintosh HD'], destination)


def test_open_session_takes_desktop_lease_before_spawning(tmp_path):
    import os
    import sys
    import pytest
    from stack_conformance.desktop import DesktopLease
    from stack_conformance.macos_ui import open_session

    marker = tmp_path / 'spawned'
    command = [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("spawned")', str(marker)]
    with DesktopLease():
        with pytest.raises(RuntimeError, match='Native desktop is in use'):
            session = open_session(command, cwd=tmp_path, env=os.environ, directory=tmp_path / 'case')
            session.close()
    assert not marker.exists()


def test_native_snapshot_distinguishes_running_process_from_missing_app_registration(tmp_path):
    import sys
    from stack_conformance.macos_ui import native_helper

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
    from stack_conformance.macos_ui import MacOSUISession

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
    from stack_conformance.macos_ui import MacOSUISession

    class AlreadySelectedDriver(MacOSUISession):
        def __init__(self):
            self.directory = tmp_path

        def _request(self, command, **values):
            assert command == 'snapshot', 'Selecting the current value must not open another popup'
            return {'nodes': [{'id': 'alignment', 'role': 'AXMenuButton', 'title': 'Off', 'path': [0]}]}

    AlreadySelectedDriver().select('alignment', 'Off')


def test_native_path_readiness_waits_for_resolved_selected_suggestion():
    from pathlib import Path
    from stack_conformance.macos_ui import native_path_ready

    target = Path('/private/tmp/run/case')
    typed_only = {'nodes': [{'id': 'PathTextField', 'role': 'AXTextField', 'value': str(target)}]}
    assert not native_path_ready(typed_only, target)
    resolved = {'nodes': [*typed_only['nodes'],
                         {'path': [0, 1], 'role': 'AXRow', 'selected': True},
                         {'path': [0, 1, 0, 0], 'role': 'AXList', 'id': str(target), 'description': 'path'}]}
    assert native_path_ready(resolved, target)
    assert not native_path_ready(resolved, Path('/private/tmp/other-run/case'))
