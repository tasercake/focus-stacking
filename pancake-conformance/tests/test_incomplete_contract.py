"""Adversarial self-tests of the portable corrupt-input oracle."""
from types import SimpleNamespace

import pytest

from pancake_conformance.validators import assert_incomplete


@pytest.mark.parametrize('fault', ['success', 'wrong-diagnostic', 'publication', 'completion', 'fallback'])
def test_incomplete_oracle_rejects_false_success(tmp_path, fault):
    bad = tmp_path / 'bad.png'
    output = tmp_path / 'output.png'
    result = SimpleNamespace(returncode=0 if fault == 'success' else 1,
                             stderr='decode failed: ' + ('other.png' if fault == 'wrong-diagnostic' else str(bad)),
                             output=output, diagnostics={'events': []})
    if fault == 'publication':
        output.write_bytes(b'partial')
    if fault == 'completion':
        result.diagnostics['events'] = [{'event': 'stack_complete', 'completed': True}]
    if fault == 'fallback':
        result.diagnostics['events'] = [{'event': 'backend_fallback'}]
    with pytest.raises(AssertionError):
        assert_incomplete(result, bad)


def test_incomplete_oracle_checks_existing_output_bytes(tmp_path):
    bad = tmp_path / 'bad.png'
    output = tmp_path / 'output.png'
    output.write_bytes(b'original')
    result = SimpleNamespace(returncode=1, stderr=str(bad), output=output, diagnostics={'events': []})
    assert_incomplete(result, bad, retained=b'original')
    output.write_bytes(b'damaged')
    with pytest.raises(AssertionError, match='damaged'):
        assert_incomplete(result, bad, retained=b'original')
