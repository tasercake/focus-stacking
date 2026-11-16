"""VM results retain evidence and unsupported cases never become passes."""
from copy import deepcopy

import pytest


def record(identifier, suite='interface', status='passed', **extra):
    return {'id': identifier, 'suite': suite, 'status': status, 'duration': 0.2,
            'error': '', 'notes': {}, 'outputs': {}, 'execution_environment': 'host', 'reason': '', **extra}


def test_merge_preserves_selected_order_contract_outputs_and_environment(tmp_path):
    from pancake_conformance.vm_results import merge_case_results

    guest_root = '/Users/admin/pancake-conformance/artifacts/vm-run'
    guest = record('interface.export', outputs={'gui': 'gui.tif'},
                   notes={'fixtures': {'focus': {'inputs': [{'name': 'a.png', 'sha256': 'a' * 64}]}},
                          'requests': [{'options': {'method': 'hybrid'}}],
                          'artifact': guest_root + '/cases/interface.export/gui.tif'})
    original = deepcopy(guest)
    merged = merge_case_results([record('algorithms.hybrid', 'algorithms')], [guest],
                                ['interface.export', 'algorithms.hybrid'],
                                artifact_path_map={guest_root: str(tmp_path)},
                                source_provenance={'source_sha256': 'b' * 64, 'target_commit': 'pin'})
    assert [result.id for result in merged] == ['interface.export', 'algorithms.hybrid']
    assert [result.execution_environment for result in merged] == ['vm', 'host']
    assert merged[0].outputs == {'gui': 'gui.tif'}
    assert merged[0].notes['fixtures'] == original['notes']['fixtures']
    assert merged[0].notes['requests'] == original['notes']['requests']
    assert merged[0].notes['artifact'] == str(tmp_path / 'cases/interface.export/gui.tif')
    assert guest == original


def test_merge_rejects_missing_duplicate_and_extra_results():
    from pancake_conformance.vm_results import merge_case_results

    with pytest.raises(ValueError, match='missing'):
        merge_case_results([], [], ['one'])
    with pytest.raises(ValueError, match='duplicate'):
        merge_case_results([record('one')], [record('one')], ['one'])
    with pytest.raises(ValueError, match='extra'):
        merge_case_results([record('one')], [], [])


def test_unsupported_is_partial_with_reason_and_no_output_evidence(tmp_path):
    from pancake_conformance.vm_results import baseline_artifacts, merge_case_results, result_counts, result_status

    guest = record('interface.gpu', status='unsupported', duration=0,
                   reason='VM does not expose physical GPU')
    merged = merge_case_results([record('algorithms.cpu', 'algorithms')], [guest],
                                ['algorithms.cpu', 'interface.gpu'])
    assert result_counts(merged) == {'passed': 1, 'failed': 0, 'unsupported': 1}
    assert result_status(merged) == 'partial'
    assert merged[1].reason == 'VM does not expose physical GPU'
    assert baseline_artifacts(merged[1], tmp_path) == {}
    with pytest.raises(ValueError, match='reason'):
        merge_case_results([], [record('unsupported', status='unsupported', duration=0)], ['unsupported'])
    with pytest.raises(ValueError, match='outputs'):
        merge_case_results([], [record('unsupported', status='unsupported', duration=0,
                                      reason='no GPU', outputs={'bad': 'fake.png'})], ['unsupported'])


def test_baseline_artifacts_are_resolved_inside_downloaded_case(tmp_path):
    from pancake_conformance.vm_results import baseline_artifacts, merge_case_results

    folder = tmp_path / 'cases' / 'interface.export'
    folder.mkdir(parents=True)
    image = folder / 'gui.tif'
    image.write_bytes(b'actual exported image')
    result = merge_case_results([], [record('interface.export', outputs={'gui': 'gui.tif'})], ['interface.export'])[0]
    assert baseline_artifacts(result, tmp_path) == {'gui': image.resolve()}
    result.outputs['gui'] = '../escape.tif'
    with pytest.raises(ValueError, match='escape'):
        baseline_artifacts(result, tmp_path)
    result.outputs['gui'] = '/absolute.tif'
    with pytest.raises(ValueError, match='relative'):
        baseline_artifacts(result, tmp_path)
    result.outputs['gui'] = 'missing.tif'
    with pytest.raises(ValueError, match='missing'):
        baseline_artifacts(result, tmp_path)


def test_status_preserves_failure_and_incomplete_priority():
    from pancake_conformance.vm_results import merge_case_results, result_status

    results = merge_case_results([record('bad', status='failed', error='wrong output')], [], ['bad'])
    assert result_status(results) == 'failed'
    assert result_status([], complete=False) == 'incomplete'


def test_merge_rejects_different_host_and_guest_source_provenance():
    from pancake_conformance.vm_results import merge_case_results

    with pytest.raises(ValueError, match='source'):
        merge_case_results([], [], [], source_provenance={
            'host': {'source_sha256': 'a', 'target_commit': 'pin', 'files': {}},
            'guest': {'source_sha256': 'b', 'target_commit': 'pin', 'files': {}},
        })


def test_guest_native_success_remains_pending_until_host_verification():
    from pancake_conformance.vm_results import merge_case_results, result_counts, result_status

    guest = record('interface.parity', status='pending', outputs={'gui': 'gui.tif'},
                   notes={'host_verification_pending': True, 'host_parity_requests': [{'method': 'hybrid'}]})
    merged = merge_case_results([], [guest], ['interface.parity'])
    assert merged[0].status == 'pending'
    assert merged[0].outputs == {'gui': 'gui.tif'}
    assert merged[0].notes['host_verification_pending'] is True
    assert result_counts(merged) == {'passed': 0, 'failed': 0, 'unsupported': 0, 'pending': 1}
    assert result_status(merged) == 'pending-host-verification'
    assert result_status(merged, complete=False) == 'incomplete'
    merged[0].status = 'passed'
    merged[0].notes['host_verification_pending'] = False
    assert result_counts(merged) == {'passed': 1, 'failed': 0, 'unsupported': 0}
    assert result_status(merged) == 'passed'


def test_pending_cannot_hide_failure_or_omit_explicit_verification_flag():
    from pancake_conformance.vm_results import merge_case_results, result_status

    with pytest.raises(ValueError, match='host_verification_pending'):
        merge_case_results([], [record('pending', status='pending')], ['pending'])
    merged = merge_case_results([record('bad', status='failed', error='wrong pixels')],
                                [record('pending', status='pending', notes={'host_verification_pending': True,
                                                                            'host_parity_requests': [{'method': 'hybrid'}]})],
                                ['bad', 'pending'])
    assert result_status(merged) == 'failed'


def test_passed_guest_cannot_hide_unresolved_host_verification():
    from pancake_conformance.vm_results import merge_case_results

    with pytest.raises(ValueError, match='passed.*host_verification_pending'):
        merge_case_results([], [record('inconsistent', status='passed',
                                      notes={'host_verification_pending': True,
                                             'host_parity_requests': [{'method': 'hybrid'}]})], ['inconsistent'])


@pytest.mark.parametrize('requests', [None, [], {}, 'one request'])
def test_pending_requires_nonempty_explicit_host_parity_request_list(requests):
    from pancake_conformance.vm_results import merge_case_results

    notes = {'host_verification_pending': True}
    if requests is not None:
        notes['host_parity_requests'] = requests
    with pytest.raises(ValueError, match='host_parity_requests'):
        merge_case_results([], [record('pending', status='pending', notes=notes)], ['pending'])


@pytest.mark.parametrize('status', ['passed', 'pending'])
def test_success_or_pending_verdict_rejects_nonempty_error(status):
    from pancake_conformance.vm_results import merge_case_results

    notes = ({'host_verification_pending': True,
              'host_parity_requests': [{'method': 'hybrid'}]} if status == 'pending' else {})
    with pytest.raises(ValueError, match='(?i)error|contradict'):
        merge_case_results([], [record('inconsistent', status=status,
                                      error='AssertionError: wrong pixels', notes=notes)], ['inconsistent'])
