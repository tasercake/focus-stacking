"""Thin reference-target launch and instrumentation adapter.

Only this adapter knows ChimpStackr's Python module names. Portable cases use
configured commands and canonical stack settings instead.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import sys

from stack_conformance.coverage import startup_environment


_VALUE_OPTIONS = (
    'method', 'kernel_size', 'pyramid_levels', 'scale_factor', 'alignment_ref',
    'alignment_mode', 'max_scale_step', 'slab_size', 'slab_overlap', 'gpu_id',
    'quality', 'bit_depth',
)
_FLAG_OPTIONS = ('align', 'max_precision', 'quality_report', 'auto', 'auto_crop', 'measure', 'rotation_scale')


class ChimpStackrAdapter:
    def __init__(self, target_root: str | Path, python_executable: str | Path = sys.executable):
        self.target_root = Path(target_root).resolve()
        self.python_executable = str(python_executable)
        self.source_root = self.target_root / 'src'

    def command(self, args: Sequence[str]) -> list[str]:
        return [self.python_executable, '-m', 'src.cli', *map(str, args)]

    def gui_command(self, args: Sequence[str] = ()) -> list[str]:
        return [self.python_executable, '-m', 'stack_conformance.adapters.chimpstackr_ui',
                '--target-root', str(self.target_root), *map(str, args)]

    def environment(self, base_env: Mapping[str, str], events_path: str | Path | None = None) -> dict[str, str]:
        env = startup_environment(base_env)
        env['CHIMPSTACKR_CONFORMANCE_TARGET_ROOT'] = str(self.target_root)
        if events_path is not None:
            path = Path(events_path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            env['CHIMPSTACKR_CONFORMANCE_EVENTS'] = str(path)
        return env

    def stack_arguments(self, options: Mapping[str, object]) -> list[str]:
        options = dict(options)
        if 'alignment_reference' in options:
            options['alignment_ref'] = options.pop('alignment_reference')
        unknown = set(options) - set(_VALUE_OPTIONS) - set(_FLAG_OPTIONS) - {'inputs', 'output', 'device'}
        if unknown:
            raise ValueError(f'Unknown stack options: {", ".join(sorted(unknown))}')
        inputs = options.get('inputs')
        if isinstance(inputs, (str, bytes)) or not isinstance(inputs, Sequence) or not inputs:
            raise ValueError('inputs must be a nonempty sequence of paths')
        if options.get('output') is None:
            raise ValueError('output path is required')
        args = ['--input', *map(str, inputs), '--output', str(options['output'])]
        for name in _VALUE_OPTIONS:
            if options.get(name) is not None:
                args.extend(['--' + name.replace('_', '-'), str(options[name])])
        for name in _FLAG_OPTIONS:
            if options.get(name):
                args.append('--' + name.replace('_', '-'))
        device = options.get('device', 'auto')
        if device not in ('cpu', 'gpu', 'auto'):
            raise ValueError(f'Unknown device: {device}')
        if device != 'auto':
            args.append('--' + str(device))
        return args
