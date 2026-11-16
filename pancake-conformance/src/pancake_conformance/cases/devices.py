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
    if not completed and expected is None:
        return {}
    assert completed, 'Target did not provide completed execution diagnostics'
    event = completed[-1]
    assert event.get('completed') is True, 'Stack did not complete'
    actual = event.get('actual_backend')
    if expected is not None:
        assert actual in ('cpu', 'gpu'), f'Unknown completed backend: {actual}'
        assert actual == expected, f'Expected {expected} execution, observed {actual}'

    return event


def _single(ctx, method, device):
    fixture = ctx.fixture('focus')
    result = ctx.stack(fixture, method=method, device=device)
    expected = None if device == 'auto' else device
    event = require_backend(result, expected)
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


def device_cases():
    cases = []
    for method in METHODS:
        cases.append(Case(f'devices.cpu.{method}', 'devices', partial(_single, method=method, device='cpu'),
                          'Explicit CPU selection completes without GPU fallback'))
        cases.append(Case(f'devices.gpu.stack.{method}', 'devices', partial(_parity, method=method),
                          'Strict GPU completion and CPU/GPU fusion equivalence'))
        cases.append(Case(f'devices.auto.cold.{method}', 'devices', partial(_single, method=method, device='auto'),
                          'Automatic execution produces valid output without a prescribed backend'))
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
    cases.append(Case('devices.gpu.high_precision', 'devices',
                      partial(_parity, method='hybrid', fixture_name='breathing', align=True,
                              alignment_mode='breathing', max_precision=True),
                      'High-precision GPU request produces CPU-equivalent pixels'))
    from dataclasses import replace
    return [replace(case, required_capabilities=("backend_evidence", "gpu" if ".gpu." in case.id else "cpu"))
            if ".auto." not in case.id else case for case in cases]
