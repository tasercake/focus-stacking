"""Portable execution-device and decoded-image equivalence contracts.

Execution evidence is a language-neutral JSON contract. Cases know neither
Python internals nor OpenCL implementation functions.
"""
from functools import partial

from ..model import Case
from ..validators import assert_incomplete, assert_pixels_close, read_image, validate_image

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


def _decode_rejected(ctx):
    fixture = ctx.fixture('focus')
    corrupt = ctx.directory / 'corrupt.png'
    corrupt.write_bytes(b'not a PNG image')
    result = ctx.stack([fixture.paths[0], corrupt, fixture.paths[1]], method='weighted_average', device='gpu')
    assert_incomplete(result, corrupt)


def _corrupt_matrix(ctx, method, mode):
    from .coverage_algorithms import _partial_corrupt
    _partial_corrupt(ctx, method, align=mode != 'stack',
                     mode='translation' if mode == 'stack' else mode, device='gpu')


def _exposure_precision(ctx, count):
    fixture = ctx.fixture('precision16')
    paths = [fixture.paths[i % len(fixture.paths)] for i in range(count)]
    cpu = ctx.stack(paths, method='exposure_fusion', device='cpu', bit_depth=16, output_format='tif')
    gpu = ctx.stack(paths, method='exposure_fusion', device='gpu', bit_depth=16, output_format='tif')
    require_backend(cpu, 'cpu')
    require_backend(gpu, 'gpu')
    for output in (cpu.output, gpu.output):
        validate_image(output, dtype='uint16', shape=fixture.shape, genuine_16bit=True)
        assert_pixels_close(output, fixture.truth_path, mean_limit=1, max_limit=1)
    ctx.note('identity_parity', assert_pixels_close(cpu.output, gpu.output, mean_limit=1, max_limit=1))


def _exposure_mixed_dimensions(ctx):
    import numpy as np
    import tifffile
    fixture = ctx.fixture('precision16')
    source = read_image(fixture.truth_path)
    paths = []
    for i in range(4):
        image = np.rint(source.astype(float)/257).astype(np.uint8) if i == 0 else source[1:-1, 1:-1]
        path = ctx.directory / f'mixed-{i}.tif'
        tifffile.imwrite(path, image, photometric='rgb', metadata=None)
        paths.append(path)
    cpu = ctx.stack(paths, method='exposure_fusion', align=True, alignment_mode='translation', device='cpu', bit_depth=16, output_format='tif')
    gpu = ctx.stack(paths, method='exposure_fusion', align=True, alignment_mode='translation', device='gpu', bit_depth=16, output_format='tif')
    require_backend(cpu, 'cpu')
    require_backend(gpu, 'gpu')
    validate_image(gpu.output, shape=fixture.shape, dtype='uint16', genuine_16bit=True)
    # Mixed-source Mertens weights amplify float rounding at isolated pixels.
    # Identity remains bounded to one 16-bit value in the separate gradient tests.
    ctx.note('mixed_source_precision_parity', assert_pixels_close(gpu.output, cpu.output, mean_limit=1, max_limit=32))


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
    for method in ('hybrid', 'weighted_average', 'depth_map', 'exposure_fusion'):
        cases.append(Case(f'devices.gpu.precision16.{method}', 'devices',
                          partial(_parity, method=method, fixture_name='precision16', bit_depth=16, output_format='tif'),
                          'GPU retains genuine 16-bit input precision and CPU parity'))
    cases.append(Case('devices.gpu.high_precision', 'devices',
                      partial(_parity, method='hybrid', fixture_name='breathing', align=True,
                              alignment_mode='breathing', max_precision=True),
                      'High-precision GPU request produces CPU-equivalent pixels'))
    cases.append(Case('devices.gpu.corrupt_input_rejected', 'devices', _decode_rejected,
                      'Corrupt input fails the complete job without backend fallback'))
    from .algorithms import _zero_regions, _exposure_constant_mix
    cases.append(Case('devices.gpu.weighted.zero_regions', 'devices', partial(_zero_regions, device='gpu'),
                      'Zero-weight regions preserve deterministic source color'))
    for count in (4, 9):
        cases.append(Case(f'devices.gpu.exposure_constant_mix.{count}', 'devices', partial(_exposure_constant_mix, count=count, device='gpu'),
                          'Analytic equal-weight fusion preserves low bits through batch tree'))
    for count in (2, 4, 9):
        cases.append(Case(f'devices.gpu.exposure_precision.{count}', 'devices', partial(_exposure_precision, count=count),
                          'Independent full-precision identity and CPU/GPU parity'))
    for method in METHODS:
        for mode in ('stack', 'translation', 'euclidean', 'similarity', 'affine', 'breathing'):
            cases.append(Case(f'devices.gpu.corrupt.{method}.{mode}', 'devices', partial(_corrupt_matrix, method=method, mode=mode),
                              'Corrupt requested input rejects complete job and retains existing export'))
    cases.append(Case('devices.gpu.exposure_mixed_dimensions', 'devices', _exposure_mixed_dimensions,
                      'Later sixteen-bit sources retain precision when resized or padded against an eight-bit first frame'))
    from dataclasses import replace
    return [replace(case, required_capabilities=("backend_evidence", "gpu" if ".gpu." in case.id else "cpu"))
            if ".auto." not in case.id else case for case in cases]
