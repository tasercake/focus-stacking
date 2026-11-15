"""Read-only reference instrumentation, enabled solely through environment.

Profiles function boundaries; never wraps, replaces or calls app operations.
Coverage uses tracing and remains independent from this profiling callback.
"""
from contextlib import contextmanager
import json
import math
import os
import sys
import threading
import time

_states = {}
_estimators = {}
_measured_lookups = set()
_lock = threading.Lock()
_installed = False


def _plain(value):
    if isinstance(value, float) and not math.isfinite(value):
        # Diagnostic values remain explicit without emitting invalid JSON tokens.
        return 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if type(value).__module__.startswith('numpy') and hasattr(value, 'tolist'):
        return _plain(value.tolist())
    return str(value)


def _write(event, **fields):
    record = {'schema_version': 1, 'event': event, 'pid': os.getpid(),
              'time_ns': time.time_ns(), **fields}
    payload = json.dumps(_plain(record), allow_nan=False, separators=(',', ':')) + '\n'
    with _lock, open(_events_path, 'a', encoding='utf-8') as stream:
        stream.write(payload)


def _parameters(instance):
    config = getattr(instance, 'config', None)
    return dict(vars(config)) if config is not None and hasattr(config, '__dict__') else {}


def _requested(instance):
    config = getattr(instance, 'config', None)
    mode = getattr(config, 'gpu_mode', None)
    if mode in ('cpu', 'gpu', 'auto'):
        return mode
    return 'gpu' if getattr(config, 'use_gpu', False) else 'cpu'


def _profile(frame, event, value):
    if event not in ('call', 'return'):
        return
    filename = frame.f_code.co_filename
    if filename not in _filenames:
        return
    try:
        name = frame.f_code.co_name
        instance = frame.f_locals.get('self')
        if filename == _compute_filename:
            if name == 'measure':
                if event == 'call':
                    caller = frame.f_back
                    if caller is not None and caller.f_code.co_filename == _compute_filename and caller.f_code.co_name == 'measurement':
                        _measured_lookups.add(id(caller))
                else:
                    _write('measurement_complete', algorithm=frame.f_locals.get('method'),
                           completed=isinstance(value, dict), measurement=value)
            elif name == 'measurement' and event == 'return':
                performed = id(frame) in _measured_lookups
                _measured_lookups.discard(id(frame))
                _write('measurement_lookup', algorithm=frame.f_locals.get('method'),
                       available=value is not None, cache_hit=value is not None and not performed,
                       calibration_performed=performed)
            elif name == 'decide' and event == 'return' and value is not None:
                _write('device_decision', requested_backend=getattr(value, 'mode', None),
                       actual_backend='gpu' if getattr(value, 'use_gpu', False) else 'cpu',
                       device=getattr(value, 'device', None), reason=getattr(value, 'reason', None),
                       speedup=getattr(value, 'speedup', None))
        elif filename == _api_filename and instance is not None:
            key = id(instance)
            if name in ('stack_images', 'align_and_stack_images'):
                if event == 'call':
                    _states[key] = {'gpu_completed': False, 'gpu_alignment': False,
                                    'aligned': name == 'align_and_stack_images', 'device': None}
                    _write('stack_start', algorithm=getattr(getattr(instance, 'config', None), 'stacking_method', None),
                           requested_backend=_requested(instance), effective_parameters=_parameters(instance),
                           input_order=getattr(instance, 'image_paths', []))
                else:
                    state = _states.get(key, {})
                    output = getattr(instance, 'output_image', None)
                    completed = output is not None
                    backend = ('gpu' if state.get('gpu_completed') else 'cpu') if completed else None
                    aligned = state.get('aligned', False)
                    _write('stack_complete', completed=completed,
                           algorithm=getattr(getattr(instance, 'config', None), 'stacking_method', None),
                           requested_backend=_requested(instance), actual_backend=backend,
                           actual_backend_by_stage={
                               'fusion': backend,
                               'alignment_estimation': ('cpu+gpu' if state.get('gpu_alignment') else 'cpu') if aligned else 'not_requested',
                               'warping': backend if aligned else 'not_requested',
                           }, device=state.get('device'),
                           output_shape=list(output.shape) if completed else None,
                           effective_parameters=_parameters(instance),
                           input_order=getattr(instance, 'image_paths', []),
                           alignment_transforms=getattr(instance, 'alignment_transforms', {}),
                           sequential_transforms=getattr(instance, '_breathing_transforms', None))
            elif name == '_gpu_run_inner' and event == 'return':
                state = _states.get(key)
                if state is not None:
                    gpu = frame.f_locals.get('gpu')
                    if value is True and getattr(instance, 'output_image', None) is not None:
                        state['gpu_completed'] = True
                        state['device'] = getattr(gpu, 'name', None)
                    elif value is False:
                        _write('backend_fallback', stage='fusion', requested_backend='gpu', actual_backend='cpu')
            elif name == '_gpu_estimation_on' and event == 'return':
                estimator = getattr(getattr(instance, 'Algorithm', None), 'gpu_estimation', None)
                if estimator is not None and key in _states:
                    _estimators[id(estimator)] = key
            elif name == 'auto_crop_output' and event == 'return':
                _write('crop_complete', bounds=value)
        elif filename == _ocl_filename and name == 'find_transform_ecc' and event == 'return' and value is not None:
            key = _estimators.get(id(instance))
            if key in _states:
                _states[key]['gpu_alignment'] = True
        elif filename == _cli_filename and name == 'main' and event == 'return':
            result = frame.f_locals.get('result')
            args = frame.f_locals.get('args')
            if result is not None and frame.f_locals.get('success'):
                _write('export_complete', path=getattr(args, 'output', None),
                       shape=list(result.shape), dtype=str(result.dtype))
    except Exception as exc:
        # Instrumentation must not change the target's success, failure or image.
        # A missing/invalid event remains a conformance failure in the runner.
        try:
            _write('observer_error', message=f'{type(exc).__name__}: {exc}')
        except Exception:
            pass


def install():
    global _installed, _events_path, _api_filename, _ocl_filename, _cli_filename, _compute_filename, _filenames
    if _installed:
        return
    _events_path = os.environ['CHIMPSTACKR_CONFORMANCE_EVENTS']
    root = os.path.realpath(os.environ['CHIMPSTACKR_CONFORMANCE_TARGET_ROOT'])
    _api_filename = os.path.join(root, 'src', 'algorithms', 'API.py')
    _ocl_filename = os.path.join(root, 'src', 'algorithms', 'stacking_algorithms', 'ocl.py')
    _cli_filename = os.path.join(root, 'src', 'cli.py')
    _compute_filename = os.path.join(root, 'src', 'compute.py')
    _filenames = {_api_filename, _ocl_filename, _cli_filename, _compute_filename}
    _installed = True
    sys.setprofile(_profile)
    threading.setprofile(_profile)
    _write('observer_ready', target_root=root)


@contextmanager
def observe_current_thread():
    """Attach opt-in instrumentation to a native-created worker thread.

    Qt starts workers without Python's threading bootstrap. Reuse the public
    threading trace installer and restore prior hooks when the callback exits.
    This context neither invokes nor changes a target operation.
    """
    previous_trace, previous_profile = sys.gettrace(), sys.getprofile()
    tracing_installed = profiling_installed = False
    try:
        if os.environ.get('COVERAGE_PROCESS_START') and previous_trace is None:
            trace = threading.gettrace()
            if trace is not None:
                sys.settrace(trace)
                tracing_installed = True
        if os.environ.get('CHIMPSTACKR_CONFORMANCE_EVENTS'):
            if not _installed:
                install()
            sys.setprofile(_profile)
            profiling_installed = True
        yield
    finally:
        if profiling_installed:
            sys.setprofile(previous_profile)
        if tracing_installed:
            sys.settrace(previous_trace)
