"""CLI correctness does not require reference diagnostics or file policies."""
from types import SimpleNamespace

from pancake_conformance.cases import cli


def test_output_parent_can_be_created_by_target(tmp_path):
    output = tmp_path / 'missing-parent/output.png'
    calls = []
    context = SimpleNamespace(directory=tmp_path, fixture=lambda name: SimpleNamespace(paths=[]),
        target=SimpleNamespace(stack_arguments=lambda paths, path, options: calls.append(path) or []),
        command=lambda args: SimpleNamespace(returncode=0, stderr='', stdout='', output=output))
    from PIL import Image
    output.parent.mkdir()
    Image.new('RGB', (5, 7), (20, 50, 90)).save(output)
    cli._output_failure(context)
    assert calls == [output]


def test_jpeg_precision_checks_actual_depth_without_fixed_warning_words(tmp_path):
    from PIL import Image
    output = tmp_path / 'image.jpg'
    Image.new('RGB', (5, 7), (20, 50, 90)).save(output)
    context = SimpleNamespace(fixture=lambda name: None,
        stack=lambda *a, **k: SimpleNamespace(returncode=0, stderr='JPEG stores 8 bpc', output=output))
    cli._jpeg_precision_warning(context)


def test_quality_and_progress_use_declared_formats_in_either_stream(tmp_path):
    from PIL import Image
    output = tmp_path / 'image.png'
    Image.new('RGB', (5, 7), (20, 50, 90)).save(output)
    context = SimpleNamespace(fixture=lambda name: None,
        target=SimpleNamespace(stack={'observations': {'quality_report': r'"quality":\s*0\.9',
                                                        'progress': r'"complete":\s*true'}}),
        stack=lambda *a, **k: SimpleNamespace(returncode=0, stderr='',
            stdout='{"quality": 0.9, "complete": true}', output=output))
    cli._progress(context)


def test_partly_unreadable_inputs_can_be_rejected_cleanly(tmp_path):
    from pancake_conformance.cases.coverage_cli import _partial_malformed
    result = SimpleNamespace(returncode=2, stderr='Cannot decode input: 000-invalid-0.png',
                             diagnostics={}, output=tmp_path/'output.png')
    context = SimpleNamespace(directory=tmp_path, fixture=lambda name: SimpleNamespace(paths=[]),
                               stack=lambda *args, **kwargs: result)
    _partial_malformed(context, 'png')
