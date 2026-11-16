"""Public preferences and app information through native accessibility only."""
from __future__ import annotations

from ..macos_ui import find_node
from ..model import Case
from .interface import _close_settings, _settings


def checkbox_state(snapshot, identifier):
    node = find_node(snapshot, identifier)
    value = node.get('value')
    assert isinstance(value, (int, bool)) and value in (0, 1), f'{identifier} has no observable checkbox state: {value}'
    return bool(value)


def about_item(snapshot):
    return find_node(snapshot, 'about.open')


def status_text(node):
    for key in ('value', 'title', 'description', 'help'):
        value = node.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != node.get('id'):
            return value.strip()
    raise AssertionError('Lightroom panel has no rendered status text')


def _open_preferences(ui):
    ui.action('settings.open')
    ui.wait(lambda snap: any(node.get('id') == 'settings.theme' for node in snap['nodes']),
            description='preferences opened by keyboard shortcut')


def _lightroom_status(ctx):
    with ctx.open_ui() as ui:
        _open_preferences(ui)
        text = status_text(ui.node('settings.lightroom.status'))
        action = ui.node('settings.lightroom.action')
        label = str(action.get('title') or action.get('value') or '').strip()
        assert label, 'Lightroom action has no readable label'
        assert 'enabled' in action, 'Lightroom action does not expose enabled state'
        # This is a read-only panel contract. No install, repair, removal or
        # Lightroom-launch control is activated by the conformance case.
        ctx.note('lightroom_status', {'text': text, 'action': label, 'enabled': bool(action['enabled'])})
        _close_settings(ui)


def _about(ctx):
    with ctx.open_ui() as ui:
        ui.action('about.open')
        ui.wait(lambda snap: any(node.get('id') == 'about.window' for node in snap['nodes']),
                description='application information opened')
        version = ui.observe('about.version')
        assert isinstance(version, str) and version.strip(), 'Application version is not readable'
        ui.action('dialog.close')
        ui.wait(lambda snap: not any(node.get('id') == 'about.window' for node in snap['nodes']),
                description='application information closed')
        ctx.note('about', {'version': version})


def settings_cases():
    return [
        Case('interface.settings.persistence', 'interface', _settings,
             'Theme and processing choices persist across restart; fresh profile remains isolated'),
        Case('interface.settings.lightroom-status', 'interface', _lightroom_status,
             'Lightroom status and action state are readable without changing installation', ('lightroom',)),
        Case('interface.about', 'interface', _about,
             'Application information exposes a readable version and closes', ('about',)),
    ]
