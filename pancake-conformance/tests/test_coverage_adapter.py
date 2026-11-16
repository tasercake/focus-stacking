"""Coverage is measured through real child processes, not app unit tests."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_session_covers_branches_and_never_imported_files(tmp_path):
    from pancake_conformance.coverage import CoverageSession

    source = tmp_path / 'app'
    source.mkdir()
    (source / 'entry.py').write_text(
        'import sys\n'
        'if len(sys.argv) > 1:\n'
        '    print("argument")\n'
        'else:\n'
        '    print("empty")\n'
    )
    (source / 'untouched.py').write_text('VALUE = 1\n')
    session = CoverageSession(source, tmp_path / 'reports')
    env = session.environment(os.environ)
    for args in ([], ['x']):
        subprocess.run([sys.executable, str(source / 'entry.py'), *args], env=env, check=True)
    summary = session.finalize()
    report = json.loads((tmp_path / 'reports' / 'coverage.json').read_text())
    records = {Path(name).name: data for name, data in report['files'].items()}
    assert set(records) == {'entry.py', 'untouched.py'}
    assert records['entry.py']['summary']['covered_branches'] == 2
    assert records['untouched.py']['missing_lines'] == [1]
    assert summary['line_total'] == 5
    assert summary['line_covered'] == 4
    assert summary['branch_total'] == summary['branch_covered'] == 2
    assert summary['source_file_count'] == 2
    assert (tmp_path / 'reports' / 'html' / 'index.html').is_file()
    assert (tmp_path / 'reports' / 'coverage.xml').is_file()
    assert not list((tmp_path / 'reports').glob('.coverage.*.*'))



def test_environment_does_not_mutate_parent_and_preserves_pythonpath(tmp_path):
    from pancake_conformance.coverage import CoverageSession

    source = tmp_path / 'app'
    source.mkdir()
    original = {'PYTHONPATH': '/existing', 'KEEP': 'value'}
    session = CoverageSession(source, tmp_path / 'reports')
    env = session.environment(original)
    assert original == {'PYTHONPATH': '/existing', 'KEEP': 'value'}
    assert env['KEEP'] == 'value'
    assert env['PYTHONPATH'].endswith(os.pathsep + '/existing')
    assert Path(env['COVERAGE_PROCESS_START']).is_file()



def test_finalize_without_child_data_fails_explicitly(tmp_path):
    from pancake_conformance.coverage import CoverageSession

    source = tmp_path / 'app'
    source.mkdir()
    (source / 'entry.py').write_text('VALUE = 1\n')
    session = CoverageSession(source, tmp_path / 'reports')
    with pytest.raises(RuntimeError, match='No target coverage data'):
        session.finalize()



def test_invalid_source_is_rejected(tmp_path):
    from pancake_conformance.coverage import CoverageSession

    with pytest.raises(ValueError, match='source directory'):
        CoverageSession(tmp_path / 'absent', tmp_path / 'reports')
