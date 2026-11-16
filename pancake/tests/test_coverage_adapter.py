"""Coverage is measured through real child processes, not app unit tests."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_observer_serializes_nonfinite_metrics_without_changing_source_values(tmp_path, monkeypatch):
    import math
    import numpy as np
    from pancake.adapters.coverage_startup import chimpstackr_observer as observer

    events = tmp_path / 'events.jsonl'
    monkeypatch.setattr(observer, '_events_path', str(events), raising=False)
    metrics = {'success': float('nan'), 'values': np.array([float('inf'), -float('inf'), 2.5])}
    observer._write('metric_fixture', metrics=metrics)
    record = json.loads(events.read_text(), parse_constant=lambda value: pytest.fail(value))
    assert record['metrics'] == {'success': 'NaN', 'values': ['Infinity', '-Infinity', 2.5]}
    assert math.isnan(metrics['success']) and np.isposinf(metrics['values'][0])


def test_session_covers_branches_and_never_imported_files(tmp_path):
    from pancake.coverage import CoverageSession

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
    from pancake.coverage import CoverageSession

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
    from pancake.coverage import CoverageSession

    source = tmp_path / 'app'
    source.mkdir()
    (source / 'entry.py').write_text('VALUE = 1\n')
    session = CoverageSession(source, tmp_path / 'reports')
    with pytest.raises(RuntimeError, match='No target coverage data'):
        session.finalize()


def test_invalid_source_is_rejected(tmp_path):
    from pancake.coverage import CoverageSession

    with pytest.raises(ValueError, match='source directory'):
        CoverageSession(tmp_path / 'absent', tmp_path / 'reports')


def test_chimpstackr_argument_mapping_is_shell_free_and_explicit(tmp_path):
    from pancake.adapters.chimpstackr import ChimpStackrAdapter

    adapter = ChimpStackrAdapter(tmp_path, '/python')
    args = adapter.stack_arguments({
        'inputs': [Path('frame one.png'), Path('frame two.png')],
        'output': Path('output file.tif'), 'method': 'hybrid', 'device': 'cpu',
        'align': True, 'alignment_mode': 'breathing', 'alignment_ref': 'middle',
        'bit_depth': 16, 'auto_crop': True, 'max_precision': False,
    })
    assert args[:5] == ['--input', 'frame one.png', 'frame two.png', '--output', 'output file.tif']
    assert '--cpu' in args and '--gpu' not in args
    assert '--align' in args and '--auto-crop' in args
    assert '--max-precision' not in args
    assert args[args.index('--alignment-mode') + 1] == 'breathing'
    assert adapter.command(args) == ['/python', '-m', 'src.cli', *args]
    assert adapter.source_root == tmp_path / 'src'


def test_chimpstackr_adapter_rejects_unknown_options_and_devices(tmp_path):
    from pancake.adapters.chimpstackr import ChimpStackrAdapter

    adapter = ChimpStackrAdapter(tmp_path, '/python')
    base = {'inputs': ['one.png', 'two.png'], 'output': 'out.png'}
    with pytest.raises(ValueError, match='Unknown stack options'):
        adapter.stack_arguments({**base, 'kernal_size': 5})
    with pytest.raises(ValueError, match='Unknown device'):
        adapter.stack_arguments({**base, 'device': 'metal'})
    with pytest.raises(ValueError, match='inputs must be'):
        adapter.stack_arguments({**base, 'inputs': 'one.png'})


def test_chimpstackr_adapter_environment_and_gui_bootstrap(tmp_path):
    from pancake.adapters.chimpstackr import ChimpStackrAdapter

    adapter = ChimpStackrAdapter(tmp_path, '/python')
    original = {'PYTHONPATH': 'original'}
    events = tmp_path / 'run' / 'events.jsonl'
    env = adapter.environment(original, events_path=events)
    assert env['CHIMPSTACKR_CONFORMANCE_TARGET_ROOT'] == str(tmp_path)
    assert env['CHIMPSTACKR_CONFORMANCE_EVENTS'] == str(events)
    assert original == {'PYTHONPATH': 'original'}
    assert adapter.gui_command(['--settings-root', '/settings']) == [
        '/python', '-m', 'pancake.adapters.chimpstackr_ui',
        '--target-root', str(tmp_path), '--settings-root', '/settings',
    ]


def test_observer_reports_completed_backend_and_crop_without_replacing_target(tmp_path):
    from pancake.adapters.chimpstackr import ChimpStackrAdapter

    # Tiny independent protocol fixture tests observer mechanics, not ChimpStackr behavior.
    source = tmp_path / 'target'
    api_dir = source / 'src' / 'algorithms'
    api_dir.mkdir(parents=True)
    api = api_dir / 'API.py'
    api.write_text('''
class Shape:
    shape = (8, 10, 3)
class Config:
    gpu_mode = "gpu"
    use_gpu = True
    stacking_method = "hybrid"
class LaplacianPyramid:
    def __init__(self):
        self.config = Config()
        self.output_image = None
        self.image_paths = ["one.png", "two.png"]
        self.alignment_transforms = {}
    def _gpu_run_inner(self, success):
        if success:
            self.output_image = Shape()
            return True
        return False
    def stack_images(self, success):
        self.output_image = None
        if not self._gpu_run_inner(success):
            self.output_image = Shape()
    def auto_crop_output(self):
        return (1, 2, 3, 4)
app = LaplacianPyramid()
app.stack_images(True)
app.auto_crop_output()
app.stack_images(False)
''')
    events = tmp_path / 'events.jsonl'
    adapter = ChimpStackrAdapter(source, sys.executable)
    subprocess.run([sys.executable, str(api)], env=adapter.environment(os.environ, events), check=True)
    records = [json.loads(line) for line in events.read_text().splitlines()]
    completed = [record for record in records if record['event'] == 'stack_complete']
    assert [record['actual_backend'] for record in completed] == ['gpu', 'cpu']
    assert all(record['requested_backend'] == 'gpu' for record in completed)
    assert all(record['output_shape'] == [8, 10, 3] for record in completed)
    assert [record['bounds'] for record in records if record['event'] == 'crop_complete'] == [[1, 2, 3, 4]]
    assert any(record['event'] == 'backend_fallback' for record in records)


def test_instrumentation_is_inactive_without_opt_in(tmp_path):
    from pancake.coverage import startup_environment

    env = startup_environment(os.environ)
    env.pop('COVERAGE_PROCESS_START', None)
    env.pop('CHIMPSTACKR_CONFORMANCE_EVENTS', None)
    result = subprocess.run(
        [sys.executable, '-c', 'import sys; print(sys.getprofile()); print("coverage" in sys.modules)'],
        env=env, capture_output=True, text=True, check=True,
    )
    assert result.stdout.splitlines() == ['None', 'False']


def test_observer_reports_measurement_and_cache_reuse_without_private_cache_access(tmp_path):
    from pancake.adapters.chimpstackr import ChimpStackrAdapter

    root = tmp_path / 'target'
    (root / 'src').mkdir(parents=True)
    source = root / 'src' / 'compute.py'
    source.write_text('''
class Decision:
    use_gpu = True
    mode = "auto"
    reason = "measured"
    device = "Device"
    speedup = 2.0
cache = None
def measure(method):
    return {"gpu": [[1., 2.]], "cpu": [[2., 4.]]}
def measurement(method):
    global cache
    if cache is None:
        cache = measure(method)
    return cache
def decide(mode):
    return Decision()
measurement("hybrid")
measurement("hybrid")
decide("auto")
''')
    events = tmp_path / 'events.jsonl'
    adapter = ChimpStackrAdapter(root, sys.executable)
    subprocess.run([sys.executable, str(source)], env=adapter.environment(os.environ, events), check=True)
    records = [json.loads(line) for line in events.read_text().splitlines()]
    assert len([record for record in records if record['event'] == 'measurement_complete']) == 1
    lookups = [record for record in records if record['event'] == 'measurement_lookup']
    assert [record['cache_hit'] for record in lookups] == [False, True]
    assert [record['calibration_performed'] for record in lookups] == [True, False]
    assert [record['actual_backend'] for record in records if record['event'] == 'device_decision'] == ['gpu']


def test_foreign_thread_hook_collects_coverage_without_python_thread_bootstrap(tmp_path):
    from pancake.coverage import CoverageSession

    source = tmp_path / 'target'
    source.mkdir()
    (source / 'worker.py').write_text('def work(flag):\n    if flag:\n        return 11\n    return 22\n')
    api_dir = source / 'src' / 'algorithms'
    api_dir.mkdir(parents=True)
    (api_dir / 'API.py').write_text('''
class Output:
    shape = (8, 10, 3)
class Engine:
    output_image = None
    image_paths = []
    def stack_images(self):
        self.output_image = Output()
        return 22
''')
    launcher = tmp_path / 'launch.py'
    launcher.write_text('''
import _thread
import sys
import threading
from chimpstackr_observer import observe_current_thread
from src.algorithms.API import Engine
import worker
finished = threading.Event()
failures = []
def launch():
    original_trace, original_profile = sys.gettrace(), sys.getprofile()
    try:
        with observe_current_thread():
            assert worker.work(True) == 11
            assert worker.work(False) == 22
            assert Engine().stack_images() == 22
        try:
            with observe_current_thread():
                raise ValueError('preserved exception')
        except ValueError as exc:
            assert str(exc) == 'preserved exception'
        else:
            raise AssertionError('Instrumentation suppressed exception')
        assert sys.gettrace() is original_trace
        assert sys.getprofile() is original_profile
    except BaseException as exc:
        failures.append(repr(exc))
    finally:
        finished.set()
_thread.start_new_thread(launch, ())
assert finished.wait(10)
assert not failures, failures
''')
    session = CoverageSession(source, tmp_path / 'coverage')
    from pancake.adapters.chimpstackr import ChimpStackrAdapter
    events = tmp_path / 'events.jsonl'
    env = ChimpStackrAdapter(source).environment(session.environment(os.environ), events)
    env['PYTHONPATH'] += os.pathsep + str(source)
    result = subprocess.run([sys.executable, str(launcher)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    session.finalize()
    report = json.loads((tmp_path / 'coverage' / 'coverage.json').read_text())
    worker = next(data for name, data in report['files'].items() if Path(name).name == 'worker.py')
    assert worker['summary']['covered_lines'] == worker['summary']['num_statements'] == 4
    assert worker['summary']['covered_branches'] == worker['summary']['num_branches'] == 2
    completed = [json.loads(line) for line in events.read_text().splitlines() if json.loads(line)['event'] == 'stack_complete']
    assert len(completed) == 1 and completed[0]['actual_backend'] == 'cpu'
def test_reference_runtime_records_actual_qt_version_without_a_gui():
    import PySide6
    from PySide6 import QtCore
    from pancake.adapters.chimpstackr import runtime_info
    details = runtime_info()
    assert details["pyside"] == PySide6.__version__
    assert details["qt"] == QtCore.qVersion()
    assert details["qt_build"] == QtCore.QLibraryInfo.build()
    assert QtCore.QCoreApplication.instance() is None


def test_reference_runtime_missing_dependencies_has_setup_action(monkeypatch):
    import sys
    import pytest
    from pancake.adapters.chimpstackr import runtime_info
    monkeypatch.setitem(sys.modules, "PySide6", None)
    with pytest.raises(RuntimeError, match="uv sync --extra chimpstackr"):
        runtime_info()
