"""Settings contract checks need no desktop or target implementation."""
from contextlib import nullcontext
from types import SimpleNamespace

import pytest


def test_settings_catalog_covers_persistence_updates_about_and_lightroom():
    from pancake_conformance.cases.interface_settings import settings_cases

    cases = settings_cases()
    identifiers = {case.id for case in cases}
    assert len(identifiers) == len(cases)
    assert all(case.suite == 'interface' for case in cases)
    assert identifiers == {'interface.settings.persistence', 'interface.settings.update-preferences',
                           'interface.settings.lightroom-status', 'interface.about'}


def test_checkbox_contract_rejects_missing_or_unobservable_state():
    from pancake_conformance.cases.interface_settings import checkbox_state

    assert checkbox_state({'nodes': [{'id': 'switch', 'value': 1}]}, 'switch') is True
    assert checkbox_state({'nodes': [{'id': 'switch', 'value': 0}]}, 'switch') is False
    with pytest.raises(AssertionError, match='observable checkbox state'):
        checkbox_state({'nodes': [{'id': 'switch', 'title': 'Include pre-releases'}]}, 'switch')
    with pytest.raises(AssertionError, match='Expected one UI element'):
        checkbox_state({'nodes': []}, 'switch')


def test_about_selection_is_case_independent_and_rejects_ambiguity():
    from pancake_conformance.cases.interface_settings import about_item

    node = {'role': 'AXMenuItem', 'title': 'About example', 'path': [0, 1]}
    assert about_item({'nodes': [node]}) is node
    with pytest.raises(AssertionError, match='one application About'):
        about_item({'nodes': [node, {**node, 'path': [0, 2]}]})


def test_status_contract_requires_rendered_text_not_identifier_or_label():
    from pancake_conformance.cases.interface_settings import status_text

    assert status_text({'value': 'Open packaged app to set up Lightroom Classic.'})
    with pytest.raises(AssertionError, match='status text'):
        status_text({'id': 'settings.lightroom.status', 'description': 'Lightroom plugin status'})


def test_update_preferences_refuses_enabled_network_checks():
    from pancake_conformance.cases.interface_settings import settings_cases

    clicks = []
    snapshot = {'nodes': [{'id': 'settings.theme', 'title': 'Match system'},
                          {'id': 'settings.auto_updates', 'value': 1},
                          {'id': 'settings.prereleases', 'value': 0}]}
    ui = SimpleNamespace(key=lambda *a, **k: None,
                         wait=lambda condition, **kwargs: condition(snapshot),
                         snapshot=lambda: snapshot,
                         click=lambda selector, **kwargs: clicks.append(selector))
    ctx = SimpleNamespace(open_ui=lambda **kwargs: nullcontext(ui), note=lambda *a: None)
    case = next(case for case in settings_cases() if case.id == 'interface.settings.update-preferences')
    with pytest.raises(AssertionError, match='automatic updates'):
        case.run(ctx)
    assert 'settings.auto_updates' not in clicks
    assert 'settings.prereleases' not in clicks


def test_status_contract_accepts_rendered_description_when_accessible_name_hides_value():
    from pancake_conformance.cases.interface_settings import status_text

    rendered = 'Open the packaged app to set up Lightroom Classic.'
    assert status_text({'value': 'Lightroom plugin status', 'description': rendered}) == rendered
    assert status_text({'value': 'Lightroom plugin status', 'help': rendered}) == rendered
    with pytest.raises(AssertionError, match='status text'):
        status_text({'value': 'Lightroom plugin status', 'description': 'Lightroom plugin status'})
