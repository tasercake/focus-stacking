"""Settings contract checks need no desktop or target implementation."""

import pytest


def test_settings_catalog_covers_persistence_updates_about_and_lightroom():
    from pancake_conformance.cases.interface_settings import settings_cases

    cases = settings_cases()
    identifiers = {case.id for case in cases}
    assert len(identifiers) == len(cases)
    assert all(case.suite == 'interface' for case in cases)
    assert identifiers == {'interface.settings.persistence',
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

    node = {'id': 'about.open', 'role': 'AXButton', 'title': 'Application information', 'path': [0, 1]}
    assert about_item({'nodes': [node]}) is node
    with pytest.raises(AssertionError, match='one UI element'):
        about_item({'nodes': [node, {**node, 'path': [0, 2]}]})


def test_status_contract_requires_rendered_text_not_identifier_or_label():
    from pancake_conformance.cases.interface_settings import status_text

    assert status_text({'value': 'Open packaged app to set up Lightroom Classic.'})
    with pytest.raises(AssertionError, match='status text'):
        status_text({'id': 'settings.lightroom.status', 'description': 'settings.lightroom.status'})


def test_status_contract_accepts_rendered_description_when_accessible_name_hides_value():
    from pancake_conformance.cases.interface_settings import status_text

    rendered = 'Open the packaged app to set up Lightroom Classic.'
    assert status_text({'value': 'Lightroom plugin status', 'description': rendered}) == rendered
    assert status_text({'value': 'Lightroom plugin status', 'help': rendered}) == rendered
    with pytest.raises(AssertionError, match='status text'):
        status_text({'id': 'settings.lightroom.status', 'value': 'settings.lightroom.status', 'description': 'settings.lightroom.status'})
