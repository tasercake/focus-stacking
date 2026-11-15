"""Optional coverage collector for instrumented reference targets.

Portable scenarios never import this module. A Python adapter opts into it.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path


STARTUP_DIRECTORY = Path(__file__).parent / 'adapters' / 'coverage_startup'


def startup_environment(base: Mapping[str, str]) -> dict[str, str]:
    """Enable the opt-in target startup hook without changing parent state."""
    env = dict(base)
    previous = env.get('PYTHONPATH')
    env['PYTHONPATH'] = str(STARTUP_DIRECTORY.resolve()) + (os.pathsep + previous if previous else '')
    return env


class CoverageSession:
    """Measure every Python file below a declared target source directory."""

    def __init__(self, source_root: str | Path, output_dir: str | Path):
        self.source_root = Path(source_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        if not self.source_root.is_dir():
            raise ValueError(f'Coverage source directory does not exist: {self.source_root}')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.output_dir / 'coverage.ini'
        self.data_path = self.output_dir / '.coverage'
        self.config_path.write_text(
            '[run]\n'
            'branch = True\n'
            'parallel = True\n'
            'concurrency = multiprocessing,thread\n'
            'sigterm = True\n'
            f'source = {self.source_root}\n'
            f'data_file = {self.data_path}\n'
            'omit =\n'
            '\n[report]\n'
            'exclude_lines =\n'
            'partial_branches =\n'
            'skip_empty = False\n'
            'skip_covered = False\n',
            encoding='utf-8',
        )

    def environment(self, base_env: Mapping[str, str]) -> dict[str, str]:
        env = startup_environment(base_env)
        env['COVERAGE_PROCESS_START'] = str(self.config_path)
        return env

    def finalize(self) -> dict[str, object]:
        """Combine child data, write complete reports and expose both ratios."""
        from coverage import Coverage

        shards = list(self.output_dir.glob('.coverage.*'))
        if not shards and not self.data_path.exists():
            raise RuntimeError('No target coverage data was recorded; target startup hook did not run')
        collector = Coverage(config_file=str(self.config_path))
        collector.combine(data_paths=[str(self.output_dir)], strict=False)
        collector.load()
        if not collector.get_data().measured_files():
            raise RuntimeError('No target coverage data was recorded; no target source file executed')
        collector.json_report(outfile=str(self.output_dir / 'coverage.json'))
        collector.xml_report(outfile=str(self.output_dir / 'coverage.xml'))
        collector.html_report(directory=str(self.output_dir / 'html'))
        report = json.loads((self.output_dir / 'coverage.json').read_text(encoding='utf-8'))
        totals = report['totals']
        summary: dict[str, object] = {
            'line_covered': totals['covered_lines'],
            'line_total': totals['num_statements'],
            'line_percent': 100.0 * totals['covered_lines'] / totals['num_statements'] if totals['num_statements'] else 100.0,
            'branch_covered': totals['covered_branches'],
            'branch_total': totals['num_branches'],
            'branch_percent': 100.0 * totals['covered_branches'] / totals['num_branches'] if totals['num_branches'] else 100.0,
            'source_file_count': len(report['files']),
            'json': str(self.output_dir / 'coverage.json'),
            'xml': str(self.output_dir / 'coverage.xml'),
            'html': str(self.output_dir / 'html' / 'index.html'),
            'missing': {
                name: {'lines': data['missing_lines'], 'branches': data.get('missing_branches', [])}
                for name, data in report['files'].items()
                if data['missing_lines'] or data.get('missing_branches')
            },
        }
        (self.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        return summary
