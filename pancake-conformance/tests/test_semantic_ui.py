"""Different labels, layout, and gestures must keep the same observed contract."""
from types import SimpleNamespace

import pytest


def test_semantic_action_uses_declared_native_sequence_and_observed_state():
    from pancake_conformance.ui import SemanticUI
    calls = []
    tree = {'nodes': [{'id': 'run-new-engine', 'role': 'AXButton', 'enabled': True,
                       'title': 'Combine', 'path': [4, 7]}]}
    native = SimpleNamespace(snapshot=lambda: tree,
                             click=lambda selector, **kwargs: calls.append(('click', selector)),
                             key=lambda key, modifiers=(): calls.append(('key', key, modifiers)))
    ui = SemanticUI(native, {'controls': {'stack.start': {'id': 'run-new-engine'}},
                             'actions': {'stack.run': [{'key': 'r', 'modifiers': ['control']}]}})
    assert ui.node('stack.start')['enabled'] is True
    ui.action('stack.run')
    assert calls == [('key', 'r', ('control',))]
    assert ui.snapshot()['nodes'][0]['title'] == 'Combine'
    assert 'completed' not in ui.snapshot()['nodes'][0]


def test_semantic_choices_map_native_labels_in_both_directions():
    from pancake_conformance.ui import SemanticUI
    calls = []
    tree = {'nodes': [{'id': 'motion', 'title': 'Move only', 'path': [2]}]}
    native = SimpleNamespace(snapshot=lambda: tree,
                             select=lambda selector, value, **kwargs: calls.append((selector, value)))
    ui = SemanticUI(native, {'controls': {'alignment': {'id': 'motion'}},
                             'choices': {'alignment': {'translation': 'Move only', 'off': 'Disabled'}}})
    assert ui.node('alignment')['title'] == 'translation'
    ui.select('alignment', 'off')
    assert calls == [({'id': 'motion'}, 'Disabled')]
    assert tree['nodes'][0]['title'] == 'Move only'


def test_semantic_observation_reads_actual_accessible_metadata_and_rejects_missing():
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'canvas', 'description': '{"selected_source": 2}', 'path': [5]}]}
    ui = SemanticUI(SimpleNamespace(snapshot=lambda: tree), {
        'observations': {'source_index': {'selector': {'id': 'canvas'}, 'attribute': 'description',
                                           'json': 'selected_source'}}})
    assert ui.observe('source_index') == 2
    tree['nodes'][0]['description'] = '{}'
    with pytest.raises((KeyError, AssertionError)):
        ui.observe('source_index')


def test_semantic_select_does_not_assert_success_from_action_only():
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'alignment', 'title': 'Still old', 'path': [1]}]}
    ui = SemanticUI(SimpleNamespace(snapshot=lambda: tree, select=lambda *a, **k: None),
                    {'choices': {'alignment': {'translation': 'Move only'}}})
    ui.select('alignment', 'translation')
    assert ui.node('alignment')['title'] != 'translation'


def test_semantic_native_operations_map_selectors():
    from pancake_conformance.ui import SemanticUI
    calls = []
    native = SimpleNamespace(**{name: (lambda *args, _name=name, **kwargs: calls.append((_name, args)))
                                 for name in ('focus', 'edit', 'drag', 'scroll', 'set_value')})
    ui = SemanticUI(native, {'controls': {'viewer': {'id': 'other-canvas'}}})
    ui.focus('viewer')
    ui.edit('viewer', 3)
    ui.drag('viewer', (0, 0), (1, 1))
    ui.scroll('viewer', 20)
    ui.set_value('viewer', 'x')
    assert all(args[0] == {'id': 'other-canvas'} for _, args in calls)


def test_wait_normalizes_supplied_snapshot_without_second_native_read():
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'real', 'enabled': True}]}
    native = SimpleNamespace(wait=lambda condition, **kwargs: condition(tree),
                             snapshot=lambda: pytest.fail('Unneeded second snapshot'))
    ui = SemanticUI(native, {'controls': {'stack.start': {'id': 'real'}}})
    assert ui.wait(lambda snapshot: snapshot['nodes'][0]['id'] == 'stack.start')


def test_method_selection_supports_dropdown_instead_of_reference_radio_layout():
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'engine', 'value': 'Detail blend', 'path': [3]}]}
    calls = []
    ui = SemanticUI(SimpleNamespace(snapshot=lambda: tree,
        select=lambda selector, value, **kwargs: calls.append((selector, value))), {
        'controls': {'method': {'id': 'engine'}},
        'choices': {'method': {'hybrid': 'Detail blend', 'laplacian': 'Pyramid'}},
        'actions': {'method.laplacian': [{'select': 'method', 'value': 'laplacian'}]},
        'observations': {'selected_method': {'selector': {'id': 'engine'}, 'attribute': 'value',
                                            'values': {'Detail blend': 'hybrid', 'Pyramid': 'laplacian'}}}})
    ui.action('method.laplacian')
    assert calls == [({'id': 'engine'}, 'Pyramid')]
    assert ui.observe('selected_method') == 'hybrid'


def test_reference_radio_selection_is_read_from_observed_controls():
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'method.hybrid', 'value': 1}, {'id': 'method.laplacian', 'value': 0}]}
    ui = SemanticUI(SimpleNamespace(snapshot=lambda: tree), {'observations': {'selected_method': {
        'selected': {'hybrid': {'id': 'method.hybrid'}, 'laplacian': {'id': 'method.laplacian'}}}}})
    assert ui.observe('selected_method') == 'hybrid'
    tree['nodes'][0]['value'] = 0
    with pytest.raises(AssertionError, match='one selected'):
        ui.observe('selected_method')


def test_list_observation_and_selection_are_target_declared_native_layout():
    from pancake_conformance.ui import SemanticUI
    calls = []
    tree = {'nodes': [{'id': 'tiles', 'path': [1]},
                       {'role': 'AXButton', 'title': 'Input one', 'path': [1, 0]},
                       {'role': 'AXButton', 'title': 'Input two', 'path': [1, 1]}]}
    native = SimpleNamespace(snapshot=lambda: tree, click=lambda selector, **kwargs: calls.append(selector))
    ui = SemanticUI(native, {'observations': {'frame_count': {'count': {'role': 'AXButton'}, 'within': {'id': 'tiles'}}},
                             'actions': {'frames.select_first': [{'click': {'within': {'id': 'tiles'}, 'role': 'AXButton', 'index': 0}}]}})
    assert ui.observe('frame_count') == 2
    ui.action('frames.select_first')
    assert calls == [{'path': [1, 0]}]


def test_method_workflow_accepts_dropdown_layout_and_other_display_labels():
    from contextlib import nullcontext
    from pancake_conformance.cases.interface import _method_alignment, METHODS, ALIGNMENTS
    from pancake_conformance.ui import SemanticUI
    tree = {'nodes': [{'id': 'stack.start', 'enabled': False}, {'id': 'export.start', 'enabled': False},
                       {'id': 'fusion-menu', 'value': 'Blend hybrid'}, {'id': 'motion-menu', 'value': 'Motion off'}]}
    def select(selector, value, **kwargs):
        next(node for node in tree['nodes'] if node['id'] == selector['id'])['value'] = value
    def wait(condition, **kwargs):
        assert condition(tree), kwargs.get('description')
    native = SimpleNamespace(snapshot=lambda: tree, select=select, wait=wait)
    config = {'controls': {'method': {'id': 'fusion-menu'}, 'alignment': {'id': 'motion-menu'}},
              'choices': {'method': {method: 'Blend '+method for method in METHODS},
                          'alignment': {mode: 'Motion '+mode for mode in ALIGNMENTS}},
              'actions': {'method.'+method: [{'select': 'method', 'value': method}] for method in METHODS},
              'observations': {'selected_method': {'selector': {'id': 'fusion-menu'}, 'attribute': 'value',
                  'values': {'Blend '+method: method for method in METHODS}}}}
    ui = SemanticUI(native, config)
    _method_alignment(SimpleNamespace(open_ui=lambda: nullcontext(ui)))
    assert ui.node('method')['value'] == METHODS[-1]


def test_settings_catalog_has_no_update_preferences():
    from pancake_conformance.cases.interface_settings import settings_cases
    cases = settings_cases()
    assert not any('update' in case.id for case in cases)
    assert next(case for case in cases if 'lightroom' in case.id).required_capabilities == ('lightroom',)
