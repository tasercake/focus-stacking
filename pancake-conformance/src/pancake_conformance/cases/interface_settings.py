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
    items = [node for node in snapshot['nodes']
             if node.get('role') == 'AXMenuItem' and node.get('title', '').casefold().startswith('about ')]
    assert len(items) == 1, f'Expected one application About menu item; found {len(items)}'
    return items[0]


def status_text(node):
    for key in ('value', 'title', 'description', 'help'):
        value = node.get(key)
        if isinstance(value, str) and value.strip() and value.strip().casefold() != 'lightroom plugin status':
            return value.strip()
    raise AssertionError('Lightroom panel has no rendered status text')


def _open_preferences(ui):
    ui.key(',', ('command',))
    ui.wait(lambda snap: any(node.get('id') == 'settings.theme' for node in snap['nodes']),
            description='preferences opened by keyboard shortcut')


def _updates_off(snapshot):
    assert not checkbox_state(snapshot, 'settings.auto_updates'), 'Settings case requires automatic updates disabled'


def _update_preferences(ctx):
    with ctx.open_ui(settings_id='update-preferences') as ui:
        _open_preferences(ui)
        snapshot = ui.snapshot()
        _updates_off(snapshot)
        original = checkbox_state(snapshot, 'settings.prereleases')
        ui.click('settings.prereleases', physical=False)
        ui.wait(lambda snap: checkbox_state(snap, 'settings.prereleases') != original,
                description='pre-release preference changed')
        _updates_off(ui.snapshot())
        _close_settings(ui)
    with ctx.open_ui(settings_id='update-preferences') as ui:
        _open_preferences(ui)
        snapshot = ui.snapshot()
        _updates_off(snapshot)
        assert checkbox_state(snapshot, 'settings.prereleases') != original, 'Pre-release preference did not persist'
        ui.click('settings.prereleases', physical=False)
        ui.wait(lambda snap: checkbox_state(snap, 'settings.prereleases') == original,
                description='pre-release preference restored')
        _updates_off(ui.snapshot())
        _close_settings(ui)
    ctx.note('update_preferences', {'automatic_updates': False, 'prerelease_round_trip': True})


def _lightroom_status(ctx):
    with ctx.open_ui() as ui:
        _open_preferences(ui)
        text = status_text(ui.node('settings.lightroom.status'))
        action = ui.node('settings.lightroom.action')
        label = str(action.get('title') or action.get('value') or '').strip()
        assert label in ('Install Plugin', 'Update Plugin', 'Repair Installation',
                         'Open Lightroom Classic', 'Check Again', 'Try Again'), f'Unknown Lightroom action: {label}'
        assert 'enabled' in action, 'Lightroom action does not expose enabled state'
        # This is a read-only panel contract. No install, repair, removal or
        # Lightroom-launch control is activated by the conformance case.
        ctx.note('lightroom_status', {'text': text, 'action': label, 'enabled': bool(action['enabled'])})
        _close_settings(ui)


def _about_visible(snapshot):
    return any(node.get('role') in ('AXWindow', 'AXDialog', 'AXSheet')
               and node.get('title', '').casefold().startswith('about ')
               for node in snapshot['nodes'])


def _about(ctx):
    with ctx.open_ui() as ui:
        item = about_item(ui.snapshot())
        ui.click({'path': item['path']}, physical=False)
        ui.wait(_about_visible, description='application About dialog')
        snapshot = ui.snapshot()
        versions = [value.strip() for node in snapshot['nodes'] for key in ('title', 'value')
                    if isinstance((value := node.get(key)), str)
                    and value.strip().startswith('Version ') and value.strip() != 'Version']
        assert versions, 'About dialog has no readable application version'
        assert any(node.get('role') == 'AXButton' and node.get('title') == 'Close'
                   and node.get('enabled') for node in snapshot['nodes']), 'About dialog has no enabled Close control'
        ui.click({'role': 'AXButton', 'title': 'Close'})
        ui.wait(lambda snap: not _about_visible(snap), description='About dialog closed')
        ctx.note('about', {'version': versions[0]})


def settings_cases():
    return [
        Case('interface.settings.persistence', 'interface', _settings,
             'Theme and processing choices persist across restart; fresh profile remains isolated'),
        Case('interface.settings.update-preferences', 'interface', _update_preferences,
             'Pre-release preference toggles and persists while automatic network checks stay disabled'),
        Case('interface.settings.lightroom-status', 'interface', _lightroom_status,
             'Lightroom status and action state are readable without changing installation'),
        Case('interface.about', 'interface', _about,
             'Native About menu opens readable version information and closes'),
    ]
