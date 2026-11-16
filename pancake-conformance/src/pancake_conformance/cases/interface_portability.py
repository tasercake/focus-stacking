"""Retained-result ownership and Unicode filesystem boundaries via native UI."""
from __future__ import annotations

import shutil

from ..model import Case
from ..validators import assert_pixels_close, read_image, validate_image
from .interface import _export, _has, _menu, _node, _prepare, _stack

UNICODE_EXPORT_NAME = '焦点 café 𐐀.tif'


def _wait_for_result(ui, method_label):
    ui.wait(lambda snap: ui.observe('selected_result_method', snap) == method_label
            and _node(snap, 'export.start').get('enabled'),
            description=f'retained {method_label} result selected')


def _select_result(ui, method_label):
    ui.action('results.select.' + method_label)
    _wait_for_result(ui, method_label)


def _select_older_result(ui, current_label, older_label):
    _select_result(ui, older_label)


def validate_retained_exports(first, second, restored, expected_shape):
    old = read_image(first)
    assert old.ndim == 3 and old.shape[2] == expected_shape[2], 'Retained result has invalid channels'
    assert all(0 < size <= limit for size, limit in zip(old.shape[:2], expected_shape[:2], strict=True)), 'Retained crop exceeds source geometry'
    assert old.shape != tuple(expected_shape), 'Retained-result scenario did not exercise a cropped first result'
    before = validate_image(first, dtype='uint16', min_range=100)
    replacement = validate_image(second, shape=expected_shape, dtype='uint16', min_range=100)
    validate_image(restored, shape=old.shape, dtype='uint16', min_range=100)
    retained = assert_pixels_close(restored, first, mean_limit=0, max_limit=0)
    return {'first': before, 'second': replacement, 'retained': retained}


def _retained_results(ctx):
    fixture = ctx.fixture('translation')
    with ctx.open_ui(paths=fixture.paths) as ui:
        _prepare(ui, 'weighted_average', 'euclidean')
        ui.click('autocrop', physical=False)
        ui.wait(lambda snap: _node(snap, 'autocrop').get('value') == 1,
                description='first-result crop enabled')
        _stack(ui)
        ui.wait(lambda snap: ui.observe("result_count", snap) == 1, description='first retained result')
        first = _export(ui, ctx.directory / 'retained-before.tif')
        ctx.record_output(first, 'retained-before')
        _prepare(ui, 'hybrid', 'off')
        _stack(ui)
        _wait_for_result(ui, 'hybrid')
        _select_result(ui, 'hybrid')
        second = _export(ui, ctx.directory / 'replacement.tif')
        ctx.record_output(second, 'replacement')
        _select_older_result(ui, 'hybrid', 'weighted_average')
        restored = _export(ui, ctx.directory / 'retained-after.tif')
        ctx.record_output(restored, 'retained-after')
        ctx.note('retained_results', validate_retained_exports(first, second, restored, fixture.shape))
    ctx.assert_cli_parity(second, fixture, mean_limit=1, max_limit=257,
                          method='hybrid', bit_depth=16, output_format='tif')


def _unicode_paths(ctx):
    fixture = ctx.fixture('unicode')
    folder = ctx.directory / '输入 café'
    folder.mkdir()
    paths = []
    for source in fixture.paths:
        destination = folder / source.name
        shutil.copyfile(source, destination)
        paths.append(destination)
    with ctx.open_ui() as ui:
        # Establish alignment before native file panels can leave stale AX row proxies.
        # _prepare still verifies this selection after import, before stacking.
        ui.select('alignment', 'off')
        ui.click('import.files')
        ui.wait(lambda snap: _has(snap, 'open-panel'), description='native Unicode file import')
        ui.choose_file(paths[0])
        ui.wait(lambda snap: ui.observe("frame_count", snap) == 1, description='Unicode-named source imported')
        _menu(ui, 'import.folder')
        ui.wait(lambda snap: _has(snap, 'open-panel'), description='native Unicode folder import')
        ui.navigate_folder(folder)
        ui.click('OKButton', physical=False)
        ui.wait(lambda snap: ui.observe("frame_count", snap) == len(paths), description='Unicode folder deduplicated and imported')
        _prepare(ui, 'hybrid')
        _stack(ui)
        output = _export(ui, ctx.directory / UNICODE_EXPORT_NAME)
        ctx.record_output(output, 'unicode-gui')
        ctx.note('unicode_image', validate_image(output, shape=fixture.shape, dtype='uint16', min_range=100))
    ctx.assert_cli_parity(output, fixture, mean_limit=1, max_limit=257,
                          method='hybrid', bit_depth=16, output_format='tif')
    ctx.note('unicode_names', {'inputs': [path.name for path in paths], 'export': UNICODE_EXPORT_NAME})


def portability_cases():
    return [
        Case('interface.portability.retained-results', 'interface', _retained_results,
             'Cropped old result retains exact pixels after a different unaligned job and result reselection',
             ('cpu', 'native_gui')),
        Case('interface.portability.unicode-paths', 'interface', _unicode_paths,
             'Native Unicode file/folder import and CJK, accent, space and non-BMP export preserve pixels',
             ('cpu', 'native_gui')),
    ]
