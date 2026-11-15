"""Optional coverage collector for instrumented reference targets.

Portable scenarios never import this module. A Python adapter opts into it.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid


STARTUP_DIRECTORY = Path(__file__).parent / 'adapters' / 'coverage_startup'


def source_provenance(source_root: str | Path, target_commit: str | None = None) -> dict[str, object]:
    """Fingerprint every Python source file without embedding machine paths."""
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError(f'Coverage source directory does not exist: {root}')
    files = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(root.rglob('*.py')) if path.is_file()}
    digest = hashlib.sha256()
    for name, checksum in files.items():
        digest.update(name.encode('utf-8') + b'\0' + checksum.encode('ascii') + b'\n')
    manifest: dict[str, object] = {'schema_version': 1, 'source_sha256': digest.hexdigest(), 'files': files}
    if target_commit is not None:
        manifest['target_commit'] = target_commit
    return manifest


def validate_source_provenance(source_root: str | Path, provenance: Mapping,
                               expected_target_commit: str | None = None) -> dict[str, object]:
    """Reject foreign source inventory/content or a different pinned revision."""
    expected = source_provenance(source_root)
    if provenance.get('schema_version') != 1:
        raise ValueError('Unsupported coverage source provenance schema')
    if provenance.get('files') != expected['files'] or provenance.get('source_sha256') != expected['source_sha256']:
        raise ValueError('Coverage source content or source file inventory differs from pinned host source')
    if expected_target_commit is not None and provenance.get('target_commit') != expected_target_commit:
        raise ValueError(f'Coverage target commit differs: expected {expected_target_commit}, got {provenance.get("target_commit")}')
    return expected


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
        self.provenance = source_provenance(self.source_root)
        self.imports: list[dict[str, object]] = []
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

    def import_data(self, data_paths, *, source_root: str,
                    provenance: Mapping, expected_target_commit: str | None = None) -> dict[str, object]:
        """Normalize verified guest paths before uniting line/arc data.

        Original downloaded databases remain untouched. A new normalized shard
        joins the ordinary host data only after all inputs validate.
        """
        from coverage import CoverageData

        self._verify_source_unchanged()
        validate_source_provenance(self.source_root, provenance, expected_target_commit)
        foreign_root = PurePosixPath(source_root)
        if not foreign_root.is_absolute() or '..' in foreign_root.parts:
            raise ValueError('Guest coverage source_root must be an absolute normalized path')
        paths = [Path(path).resolve() for path in data_paths]
        if not paths:
            raise ValueError('No guest coverage data files were provided')
        records = []
        measured = set()
        for path in paths:
            if not path.is_file():
                raise ValueError(f'Guest coverage data file does not exist: {path}')
            data = CoverageData(basename=str(path), read_only=True)
            data.read()
            if not data.has_arcs():
                raise ValueError(f'Guest coverage data does not contain branch arcs: {path}')
            mapping = {}
            for filename in data.measured_files():
                try:
                    relative = PurePosixPath(filename).relative_to(foreign_root)
                except ValueError as exc:
                    raise ValueError(f'Guest coverage file is outside declared source root: {filename}') from exc
                if '..' in relative.parts or relative.as_posix() not in self.provenance['files']:
                    raise ValueError(f'Guest coverage file is outside pinned source inventory: {filename}')
                mapping[filename] = str(self.source_root / Path(*relative.parts))
                measured.add(mapping[filename])
            records.append((data, mapping))
        normalized_path = self.output_dir / f'.coverage.vm-{uuid.uuid4().hex}'
        normalized = CoverageData(basename=str(normalized_path))
        try:
            for data, mapping in records:
                normalized.update(data, map_path=mapping.__getitem__)
            normalized.write()
        except BaseException:
            normalized_path.unlink(missing_ok=True)
            raise
        record = {'data_file_count': len(paths), 'measured_file_count': len(measured),
                  'source_sha256': provenance['source_sha256'],
                  'target_commit': provenance.get('target_commit'),
                  'guest_source_root': str(foreign_root), 'host_source_root': str(self.source_root)}
        self.imports.append(record)
        (self.output_dir / 'coverage-imports.json').write_text(json.dumps(self.imports, indent=2) + '\n', encoding='utf-8')
        return record

    def _verify_source_unchanged(self):
        if source_provenance(self.source_root) != self.provenance:
            raise ValueError('Target source changed during coverage collection')

    def finalize(self, *, allow_empty: bool = False) -> dict[str, object]:
        """Combine measured execution; explicit unsupported-only runs may be empty."""
        from coverage import Coverage, CoverageData

        self._verify_source_unchanged()
        shards = list(self.output_dir.glob('.coverage.*'))
        if not shards and not self.data_path.exists():
            if not allow_empty:
                raise RuntimeError('No target coverage data was recorded; target startup hook did not run')
            empty = CoverageData(basename=str(self.data_path))
            empty.add_arcs({str(self.source_root / name): [] for name in self.provenance['files']})
            empty.touch_files([str(self.source_root / name) for name in self.provenance['files']])
            empty.write()
        collector = Coverage(config_file=str(self.config_path))
        collector.combine(data_paths=[str(self.output_dir)], strict=False)
        collector.load()
        data = collector.get_data()
        execution_present = any(data.lines(name) for name in data.measured_files())
        if not execution_present and not allow_empty:
            raise RuntimeError('No target coverage data was recorded; no target source file executed')
        if not execution_present and not data.has_arcs():
            # Some empty child databases contain source inventory but no mode.
            # Rebuild an explicitly empty branch database; never invent arcs.
            data.erase()
            data.add_arcs({str(self.source_root / name): [] for name in self.provenance['files']})
            data.touch_files([str(self.source_root / name) for name in self.provenance['files']])
            data.write()
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
            'source_sha256': self.provenance['source_sha256'],
            'imports': self.imports,
            'execution_present': bool(execution_present),
            'json': str(self.output_dir / 'coverage.json'),
            'xml': str(self.output_dir / 'coverage.xml'),
            'html': str(self.output_dir / 'html' / 'index.html'),
            'missing': {
                name: {'lines': data['missing_lines'], 'branches': data.get('missing_branches', [])}
                for name, data in report['files'].items()
                if data['missing_lines'] or data.get('missing_branches')
            },
        }
        if not execution_present:
            summary['coverage_unavailable_reason'] = 'No supported target cases executed'
        (self.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        return summary
