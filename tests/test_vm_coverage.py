"""Real host/guest coverage is united after source-root normalization."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def source_tree(root):
    root.mkdir()
    (root / 'entry.py').write_text('import sys\nif sys.argv[1] == "yes":\n    VALUE = 1\nelse:\n    VALUE = 2\n')
    (root / 'untouched.py').write_text('NEVER_IMPORTED = 3\n')
    return root


def run_source(session, root, choice):
    subprocess.run([sys.executable, str(root / 'entry.py'), choice],
                   env=session.environment(os.environ), check=True)
    return sorted(session.output_dir.glob('.coverage.*'))


def test_host_guest_union_normalizes_paths_before_branch_merge(tmp_path):
    from coverage import CoverageData
    from stack_conformance.coverage import CoverageSession, source_provenance

    host_root = source_tree(tmp_path / 'host-src')
    guest_root = source_tree(tmp_path / 'guest-src')
    host = CoverageSession(host_root, tmp_path / 'host-coverage')
    guest = CoverageSession(guest_root, tmp_path / 'guest-coverage')
    run_source(host, host_root, 'yes')
    files = run_source(guest, guest_root, 'no')
    provenance = source_provenance(guest_root, target_commit='pinned-commit')
    imported = host.import_data(files, source_root=str(guest_root), provenance=provenance,
                                expected_target_commit='pinned-commit')
    assert imported['data_file_count'] == len(files)
    summary = host.finalize()
    assert summary['source_file_count'] == 2
    assert summary['line_covered'] == 4 and summary['line_total'] == 5
    assert summary['branch_covered'] == summary['branch_total'] == 2
    assert summary['imports'][0]['source_sha256'] == provenance['source_sha256']
    report = json.loads((tmp_path / 'host-coverage' / 'coverage.json').read_text())
    assert {Path(name).name for name in report['files']} == {'entry.py', 'untouched.py'}
    assert next(data for name, data in report['files'].items() if name.endswith('untouched.py'))['missing_lines'] == [1]
    data = CoverageData(basename=str(host.data_path))
    data.read()
    assert all(Path(name).is_relative_to(host_root) for name in data.measured_files())
    assert not any(str(guest_root) in name for name in report['files'])


def test_coverage_import_rejects_changed_source_and_wrong_commit(tmp_path):
    from stack_conformance.coverage import CoverageSession, source_provenance

    host_root = source_tree(tmp_path / 'host')
    guest_root = source_tree(tmp_path / 'guest')
    host = CoverageSession(host_root, tmp_path / 'host-data')
    guest = CoverageSession(guest_root, tmp_path / 'guest-data')
    files = run_source(guest, guest_root, 'yes')
    provenance = source_provenance(guest_root, target_commit='wrong')
    with pytest.raises(ValueError, match='commit'):
        host.import_data(files, source_root=str(guest_root), provenance=provenance,
                         expected_target_commit='expected')
    (guest_root / 'entry.py').write_text('VALUE = 999\n')
    with pytest.raises(ValueError, match='source'):
        host.import_data(files, source_root=str(guest_root), provenance=source_provenance(guest_root))
    assert not list(host.output_dir.glob('.coverage.vm-*'))


def test_coverage_import_rejects_unmapped_file_and_line_only_data(tmp_path):
    from coverage import CoverageData
    from stack_conformance.coverage import CoverageSession, source_provenance

    root = source_tree(tmp_path / 'source')
    session = CoverageSession(root, tmp_path / 'merged')
    outside = CoverageData(basename=str(tmp_path / 'outside-data'))
    outside.add_arcs({str(tmp_path / 'different.py'): [(-1, 1), (1, -1)]})
    outside.write()
    with pytest.raises(ValueError, match='outside'):
        session.import_data([outside.data_filename()], source_root=str(root), provenance=source_provenance(root))
    lines = CoverageData(basename=str(tmp_path / 'line-data'))
    lines.add_lines({str(root / 'entry.py'): [1, 2, 3]})
    lines.write()
    with pytest.raises(ValueError, match='branch'):
        session.import_data([lines.data_filename()], source_root=str(root), provenance=source_provenance(root))


def test_source_provenance_is_root_independent_and_detects_inventory_change(tmp_path):
    from stack_conformance.coverage import source_provenance, validate_source_provenance

    host = source_tree(tmp_path / 'host')
    guest = source_tree(tmp_path / 'guest')
    assert source_provenance(host) == source_provenance(guest)
    provenance = source_provenance(guest)
    validate_source_provenance(host, provenance)
    (guest / 'extra.py').write_text('EXTRA = 1\n')
    with pytest.raises(ValueError, match='source'):
        validate_source_provenance(host, source_provenance(guest))


def test_coverage_session_rejects_host_source_drift_during_run(tmp_path):
    from stack_conformance.coverage import CoverageSession

    root = source_tree(tmp_path / 'source')
    session = CoverageSession(root, tmp_path / 'data')
    run_source(session, root, 'yes')
    (root / 'entry.py').write_text('VALUE = 9\n')
    with pytest.raises(ValueError, match='changed'):
        session.finalize()


def test_explicit_unsupported_only_run_reports_zero_without_fabricating_execution(tmp_path):
    from stack_conformance.coverage import CoverageSession

    root = source_tree(tmp_path / 'source')
    session = CoverageSession(root, tmp_path / 'coverage')
    summary = session.finalize(allow_empty=True)
    assert summary['source_file_count'] == 2
    assert summary['line_covered'] == 0 and summary['line_total'] == 5
    assert summary['branch_covered'] == 0 and summary['branch_total'] == 2
    assert summary['execution_present'] is False
    assert summary['coverage_unavailable_reason'] == 'No supported target cases executed'
    report = json.loads((tmp_path / 'coverage' / 'coverage.json').read_text())
    assert all(not data['executed_lines'] for data in report['files'].values())


def test_empty_instrumented_child_is_not_normal_target_execution(tmp_path):
    from stack_conformance.coverage import CoverageSession

    root = source_tree(tmp_path / 'source')
    session = CoverageSession(root, tmp_path / 'coverage')
    subprocess.run([sys.executable, '-c', 'pass'], env=session.environment(os.environ), check=True)
    with pytest.raises(RuntimeError, match='no target source file executed'):
        session.finalize()


def test_coverage_environment_disables_compile_time_numba_notifications_only(tmp_path):
    from stack_conformance.coverage import CoverageSession

    root = source_tree(tmp_path / 'source')
    session = CoverageSession(root, tmp_path / 'coverage')
    original = {'NUMBA_JIT_COVERAGE': '1', 'NUMBA_DISABLE_JIT': '0'}
    environment = session.environment(original)
    assert environment['NUMBA_JIT_COVERAGE'] == '0'
    assert environment['NUMBA_DISABLE_JIT'] == '0'
    assert original == {'NUMBA_JIT_COVERAGE': '1', 'NUMBA_DISABLE_JIT': '0'}
