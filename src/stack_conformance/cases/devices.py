"""Portable execution-device and decoded-image equivalence contracts.

Execution evidence is a language-neutral JSON contract. Cases know neither
Python internals nor OpenCL implementation functions.
"""
from functools import partial

from ..model import Case
from ..validators import assert_pixels_close, read_image, validate_image

METHODS = ('laplacian', 'hybrid', 'weighted_average', 'depth_map', 'exposure_fusion')
ALIGNMENT_FIXTURES = {'translation': 'translation', 'euclidean': 'rotation',
                      'similarity': 'similarity', 'affine': 'affine', 'breathing': 'breathing'}


def require_backend(result, expected=None):
    assert result.returncode == 0, result.stderr
    events = result.diagnostics.get('events', [])
    errors = [event for event in events if event.get('event') == 'observer_error']
    assert not errors, f'observer_error: {errors}'
    completed = [event for event in events if event.get('event') == 'stack_complete']
    assert completed, 'Target did not provide completed execution diagnostics'
    event = completed[-1]
    assert event.get('completed') is True, 'Stack did not complete'
    actual = event.get('actual_backend')
    assert actual in ('cpu', 'gpu'), f'Unknown completed backend: {actual}'
    if expected is not None:
        assert actual == expected, f'Expected {expected} execution, observed {actual}'
    assert event.get('actual_backend_by_stage', {}).get('fusion', actual) == actual
    return event


def _single(ctx, method, device):
    fixture = ctx.fixture('focus')
    result = ctx.stack(fixture, method=method, device=device)
    # Small cold-cache frames use CPU in automatic mode; no calibration needed.
    expected = 'cpu' if device == 'auto' else device
    event = require_backend(result, expected)
    assert event.get('requested_backend') == device, f'Requested backend lost: {event}'
    if device == 'cpu':
        assert not any(item.get('event') == 'backend_fallback' for item in result.diagnostics['events']), 'Forced CPU attempted GPU'
    ctx.note('image', validate_image(result.output, shape=fixture.shape, dtype='uint8', min_range=20))
    ctx.note('execution', event)


def _parity(ctx, method, fixture_name='focus', **options):
    fixture = ctx.fixture(fixture_name)
    cpu = ctx.stack(fixture, method=method, device='cpu', **options)
    gpu = ctx.stack(fixture, method=method, device='gpu', **options)
    require_backend(cpu, 'cpu')
    event = require_backend(gpu, 'gpu')
    dtype = 'uint16' if options.get('bit_depth') == 16 else 'uint8'
    ctx.note('image', validate_image(gpu.output, shape=fixture.shape, dtype=dtype, min_range=20,
                                    genuine_16bit=dtype == 'uint16'))
    first, second = read_image(cpu.output), read_image(gpu.output)
    if dtype == 'uint16':
        # Error units remain 8-bit code levels, not 16-bit integer levels.
        first, second = first.astype(float) / 257.0, second.astype(float) / 257.0
    aligned = bool(options.get('align'))
    slabbed = bool(options.get('slab_size'))
    mean_limit = (0.6 if method == 'depth_map' else 0.5) if aligned else 0.3
    fraction_limit = (0.05 if method == 'depth_map' else 0.02) if aligned else 0.01
    if slabbed:
        mean_limit = 0.75 if method == 'depth_map' else 0.5
        fraction_limit = 0.05
    max_limit = None
    if method == 'laplacian' and fixture_name in ('focus', 'deep'):
        # Reference OpenCL uses exact sRGB curves; CPU LAB uses OpenCV's
        # approximation. Small CLAHE tiles amplify that known difference.
        # Frozen generated fixtures measured MAE .565/.736, p99 4/3, max 10/9.
        mean_limit, fraction_limit, max_limit = 0.8, 0.05, 12.0
    ctx.note('parity', assert_pixels_close(second, first, mean_limit=mean_limit,
                                          max_limit=max_limit, fraction_limit=fraction_limit, threshold=2.0))
    ctx.note('gpu_execution', event)
    if options.get('max_precision'):
        assert event['actual_backend_by_stage']['alignment_estimation'] == 'cpu', 'Maximum precision must retain CPU alignment refinement'


def _gpu_index(ctx, index):
    fixture = ctx.fixture('focus')
    normal = ctx.stack(fixture, method='hybrid', device='gpu', gpu_id=0)
    selected = ctx.stack(fixture, method='hybrid', device='gpu', gpu_id=index)
    initial = require_backend(normal, 'gpu')
    event = require_backend(selected, 'gpu')
    # Current reference normalizes indices to valid device range. On the
    # one-device macOS reference, negative/high indices select that same GPU.
    assert event.get('device') == initial.get('device'), 'Reference device index normalization changed'
    ctx.note('parity', assert_pixels_close(selected.output, normal.output, mean_limit=0, max_limit=0))
    ctx.note('normalized_index', index)


def _decode_fallback(ctx):
    fixture = ctx.fixture('focus')
    corrupt = ctx.directory / 'corrupt.png'
    corrupt.write_bytes(b'not a PNG image')
    valid = [fixture.paths[0], fixture.paths[1]]
    reference = ctx.stack(valid, method='weighted_average', device='cpu')
    fallback = ctx.stack([valid[0], corrupt, valid[1]], method='weighted_average', device='gpu')
    require_backend(reference, 'cpu')
    event = require_backend(fallback, 'cpu')
    assert event.get('requested_backend') == 'gpu'
    assert any(item.get('event') == 'backend_fallback' for item in fallback.diagnostics['events']), 'GPU decode failure did not report CPU fallback'
    ctx.note('image', validate_image(fallback.output, shape=fixture.shape, dtype='uint8', min_range=20))
    ctx.note('parity', assert_pixels_close(fallback.output, reference.output, mean_limit=0, max_limit=0))
    ctx.note('compatibility', 'GPU rejects corrupt frame; weighted CPU fallback skips it and preserves valid-frame result')


def _measured_auto(ctx):
    from PIL import Image

    fixture = ctx.fixture('focus')
    paths = []
    for index, source in enumerate(fixture.paths[:2]):
        path = ctx.directory / f'calibration-input-{index}.png'
        with Image.open(source) as image:
            image.resize((1100, 1000), Image.Resampling.BILINEAR).save(path)
        paths.append(path)
    cold = ctx.stack(paths, method='hybrid', device='auto', measure=True)
    first = require_backend(cold)
    assert first.get('requested_backend') == 'auto'
    events = cold.diagnostics['events']
    measured = [item for item in events if item.get('event') == 'measurement_complete']
    assert len(measured) == 1 and measured[0].get('completed') is True, 'Cold large-frame run did not complete calibration'
    assert any(item.get('event') == 'measurement_lookup' and item.get('calibration_performed') for item in events), 'Calibration result was not used'
    warm = ctx.stack(paths, method='hybrid', device='auto', measure=True)
    second = require_backend(warm)
    assert second['actual_backend'] == first['actual_backend'], 'Same measured workload changed selected backend'
    warm_events = warm.diagnostics['events']
    assert not any(item.get('event') == 'measurement_complete' for item in warm_events), 'Warm run repeated calibration'
    assert any(item.get('event') == 'measurement_lookup' and item.get('cache_hit') and item.get('available') for item in warm_events), 'Warm run did not reuse measurement'
    ctx.note('image', validate_image(warm.output, shape=(1000, 1100, 3), dtype='uint8', min_range=20))
    ctx.note('parity', assert_pixels_close(warm.output, cold.output, mean_limit=0, max_limit=0))
    ctx.note('measured_backend', first['actual_backend'])


def device_cases():
    cases = []
    for method in METHODS:
        cases.append(Case(f'devices.cpu.{method}', 'devices', partial(_single, method=method, device='cpu'),
                          'Explicit CPU selection completes without GPU fallback'))
        cases.append(Case(f'devices.gpu.stack.{method}', 'devices', partial(_parity, method=method),
                          'Strict GPU completion and CPU/GPU fusion equivalence'))
        cases.append(Case(f'devices.auto.cold.{method}', 'devices', partial(_single, method=method, device='auto'),
                          'Automatic cold-cache selection for small generated stack'))
        cases.append(Case(f'devices.gpu.aligned.{method}', 'devices',
                          partial(_parity, method=method, fixture_name='translation', align=True, alignment_mode='translation'),
                          'Alignment and fusion complete on GPU with CPU-equivalent image'))
    for mode, fixture in ALIGNMENT_FIXTURES.items():
        cases.append(Case(f'devices.gpu.alignment.{mode}', 'devices',
                          partial(_parity, method='hybrid', fixture_name=fixture, align=True, alignment_mode=mode),
                          'GPU pipeline agrees with CPU for supported transform model'))
    for method in METHODS[:-1]:
        cases.append(Case(f'devices.gpu.slabs.{method}', 'devices',
                          partial(_parity, method=method, fixture_name='deep', slab_size=4, slab_overlap=1),
                          'Overlapping GPU slabs agree with CPU slabs'))
    for method in ('hybrid', 'weighted_average', 'depth_map'):
        cases.append(Case(f'devices.gpu.precision16.{method}', 'devices',
                          partial(_parity, method=method, fixture_name='precision16', bit_depth=16, output_format='tif'),
                          'GPU retains genuine 16-bit input precision and CPU parity'))
    for index, name in ((0, 'zero'), (-10, 'negative'), (9999, 'above_range')):
        cases.append(Case(f'devices.gpu.index.{name}', 'devices', partial(_gpu_index, index=index),
                          'Single-device reference normalizes index and completes on real GPU'))
    cases.append(Case('devices.gpu.high_precision', 'devices',
                      partial(_parity, method='hybrid', fixture_name='breathing', align=True,
                              alignment_mode='breathing', max_precision=True),
                      'CPU maximum-precision alignment with GPU fusion is reported accurately'))
    cases.append(Case('devices.gpu.decode_fallback', 'devices', _decode_fallback,
                      'Real corrupt-frame GPU failure completes through CPU fallback'))
    cases.append(Case('devices.auto.measured_cache_reuse', 'devices', _measured_auto,
                      'Large generated inputs trigger real calibration and warm cache reuse'))
    return cases
