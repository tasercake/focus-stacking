"""Map semantic UI contracts to real native selectors, gestures, and observations.

Mappings select operating-system controls; they never call target business code
or manufacture a postcondition. Cases must wait for observed state or files.
"""
from copy import deepcopy
import json
import re

from .macos_ui import find_node


class SemanticUI:
    """A native UI session with target-declared presentation details."""

    def __init__(self, native, contract=None):
        self.native = native
        self.contract = contract or {}

    def __getattr__(self, name):
        return getattr(self.native, name)

    def selector(self, value):
        selector = self.contract.get('controls', {}).get(value, {'id': value}) if isinstance(value, str) else value
        if 'within' in selector or 'text_pattern' in selector:
            tree = self.native.snapshot()
            within = find_node(tree, selector['within'])['path'] if 'within' in selector else []
            matches = [node for node in tree['nodes']
                       if node.get('path', [])[:len(within)] == within and len(node.get('path', [])) > len(within)
                       and ('role' not in selector or node.get('role') == selector['role'])]
            if 'text_pattern' in selector:
                matches = [node for node in matches if any(
                    re.search(selector['text_pattern'], str(child.get(key, '')))
                    for child in tree['nodes'] if child.get('path', [])[:len(node['path'])] == node['path']
                    for key in ('title', 'value', 'description'))]
            if 'index' in selector:
                assert len(matches) > selector['index'], 'Missing native list item'
                return {'path': matches[selector['index']]['path']}
            assert len(matches) == 1, f'Expected one native item: {selector}'
            return {'path': matches[0]['path']}
        return selector

    def normalize(self, snapshot):
        snapshot = deepcopy(snapshot)
        controls = self.contract.get('controls', {})
        for node in snapshot['nodes']:
            raw_id = node.get('id')
            if raw_id in controls and not all(node.get(key) == value for key, value in controls[raw_id].items()):
                node['_native_id'] = raw_id
                node['id'] = 'native:' + raw_id
            for identifier, selector in controls.items():
                if all(node.get(key) == value for key, value in selector.items()):
                    node['_native_id'] = node.get('id')
                    node['id'] = identifier
                    break
            choices = self.contract.get('choices', {}).get(node.get('id'), {})
            for attribute in ('title', 'value'):
                for semantic, displayed in choices.items():
                    if node.get(attribute) == displayed:
                        node[attribute] = semantic
        return snapshot

    def snapshot(self):
        return self.normalize(self.native.snapshot())

    def node(self, selector, *, timeout=5):
        try:
            return find_node(self.snapshot(), selector)
        except AssertionError:
            return self.wait(lambda snap: find_node(snap, selector), timeout=timeout,
                             description=f"UI control {selector}")

    def wait(self, condition, **kwargs):
        return self.native.wait(lambda snapshot: condition(self.normalize(snapshot)), **kwargs)

    def click(self, selector, **kwargs):
        return self.native.click(self.selector(selector), **kwargs)

    def focus(self, selector, **kwargs):
        return self.native.focus(self.selector(selector), **kwargs)

    def edit(self, selector, value, **kwargs):
        return self.native.edit(self.selector(selector), value, **kwargs)

    def drag(self, selector, start, end, **kwargs):
        return self.native.drag(self.selector(selector), start, end, **kwargs)

    def scroll(self, selector, amount, **kwargs):
        return self.native.scroll(self.selector(selector), amount, **kwargs)

    def set_value(self, selector, value, **kwargs):
        return self.native.set_value(self.selector(selector), value, **kwargs)

    def select(self, selector, value, **kwargs):
        displayed = self.contract.get('choices', {}).get(selector, {}).get(value, value)
        return self.native.select(self.selector(selector), displayed, **kwargs)

    def action(self, name):
        """Execute only native input, then let the case verify its outcome."""
        steps = self.contract.get('actions', {}).get(name, [{'click': name}])
        for step in steps:
            if 'click' in step:
                self.click(step['click'], **{'physical': False, **{key: value for key, value in step.items() if key != 'click'}})
            elif 'select' in step:
                self.select(step['select'], step['value'])
            elif 'key' in step:
                self.native.key(step['key'], tuple(step.get('modifiers', [])))
            else:
                raise ValueError(f'Unsupported native UI action: {step}')

    @staticmethod
    def _observed_node(snapshot, selector):
        matches = [node for node in snapshot['nodes'] if all(
            node.get(key) == value or (key == 'id' and node.get('_native_id') == value)
            for key, value in selector.items())]
        assert len(matches) == 1, f'Expected one observed UI element: {selector}'
        return matches[0]

    def observe(self, name, snapshot=None):
        """Read declared accessible text or JSON metadata without inference."""
        rule = self.contract.get('observations', {}).get(name)
        if rule is None:
            node = find_node(snapshot or self.snapshot(), name)
            return node.get('value', node.get('description'))
        tree = snapshot if snapshot is not None else self.native.snapshot()
        if 'selected' in rule:
            selected = [name for name, selector in rule['selected'].items()
                        if self._observed_node(tree, selector).get('value') in (1, True)]
            assert len(selected) == 1, f'Expected one selected {name}: {selected}'
            return selected[0]
        if 'count' in rule:
            within = self._observed_node(tree, rule['within'])['path'] if 'within' in rule else []
            return sum(all(node.get(key) == value for key, value in rule['count'].items())
                       and node.get('path', [])[:len(within)] == within
                       and len(node.get('path', [])) > len(within)
                       and (not rule.get('direct') or len(node['path']) == len(within) + 1) for node in tree['nodes'])
        node = self._observed_node(tree, rule['selector'])
        value = node[rule.get('attribute', 'value')]
        if 'json' in rule:
            value = json.loads(value)
            for key in rule['json'].split('.'):
                value = value[key]
        if 'pattern' in rule:
            match = re.search(rule['pattern'], str(value))
            assert match, f'Missing observable UI state: {name}'
            value = match.group(1) if match.groups() else match.group(0)
        if rule.get('type') == 'integer':
            value = int(value)
        return rule.get('values', {}).get(str(value), value)

    def __enter__(self):
        self.native.__enter__()
        return self

    def __exit__(self, *args):
        return self.native.__exit__(*args)
