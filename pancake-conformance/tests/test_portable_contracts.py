"""Behavior contracts must permit independent implementations."""
from types import SimpleNamespace

from pancake_conformance.cli import catalog
from pancake_conformance.context import CaseContext
from pancake_conformance.model import Case, ProcessResult
from pancake_conformance.runner import run_cases
from pancake_conformance.target import TargetSpec


def test_delivery_and_backend_strategy_are_not_portable_cases():
    identifiers = {case.id for case in catalog()}
    assert not any('updates' in name or '.service.' in name for name in identifiers)
    assert not any('measured_cache' in name or '.cache.' in name or '.index.' in name for name in identifiers)


def test_stack_does_not_inject_engine_tuning(tmp_path):
    ctx = CaseContext(TargetSpec('independent', tmp_path, ('stacker',)), tmp_path / 'case')
    ctx.command = lambda args: ProcessResult(args, 1, '', 'fixture', 0)
    result = ctx.stack([tmp_path / 'input.png'])
    assert result.command == ['--input', str(tmp_path / 'input.png'), '--output', str(result.output)]
    assert ctx.notes['requests'][0]['options'] == {}


def test_stack_uses_only_declared_defaults_and_explicit_options(tmp_path):
    target = TargetSpec('independent', tmp_path, ('stacker',), stack={
        'defaults': {'method': 'hybrid'}, 'options': {'method': '--fusion'}})
    ctx = CaseContext(target, tmp_path / 'case')
    ctx.command = lambda args: ProcessResult(args, 1, '', 'fixture', 0)
    assert ctx.stack([]).command[-2:] == ['--fusion', 'hybrid']
    assert ctx.stack([], method='laplacian').command[-2:] == ['--fusion', 'laplacian']


def test_unrequested_backend_does_not_need_internal_diagnostics():
    from pancake_conformance.cases.devices import require_backend
    assert require_backend(SimpleNamespace(returncode=0, stderr='', diagnostics={})) == {}


def test_backend_proof_does_not_constrain_internal_stages():
    from pancake_conformance.cases.devices import require_backend
    event = {'event': 'stack_complete', 'completed': True, 'actual_backend': 'gpu',
             'actual_backend_by_stage': {'fusion': 'cpu'}}
    assert require_backend(SimpleNamespace(returncode=0, stderr='', diagnostics={'events': [event]}), 'gpu') == event


def test_host_missing_capability_is_unsupported_and_does_not_execute(tmp_path):
    def forbidden(ctx):
        raise AssertionError('Unsupported case executed')
    cases = [Case('optional.feature', 'interface', forbidden, required_capabilities=('optional_feature',))]
    results = run_cases(cases, target=TargetSpec('minimal', tmp_path, ('unused',)), output=tmp_path / 'run')
    assert results[0].status == 'unsupported'
    assert 'optional_feature' in results[0].reason
