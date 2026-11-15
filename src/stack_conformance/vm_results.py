"""Merge external execution evidence without treating unsupported work as pass."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
import math
from pathlib import Path
import re

from .model import CaseResult

_FINAL_STATUSES = ('passed', 'failed', 'unsupported')
_STATUSES = (*_FINAL_STATUSES, 'pending')


def _records(value):
    return value.get('cases', []) if isinstance(value, Mapping) else value


def _remap(value, paths):
    if isinstance(value, dict):
        return {key: _remap(item, paths) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_remap(item, paths) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for old, new in paths:
            if value == old or value.startswith(old + '/'):
                return new + value[len(old):]
    return value


def _source_metadata(provenance):
    if not provenance:
        return {}
    if 'host' in provenance and 'guest' in provenance:
        host, guest = provenance['host'], provenance['guest']
        if any(host.get(key) != guest.get(key) for key in ('source_sha256', 'files')):
            raise ValueError('Host and guest source provenance differ')
        if host.get('target_commit') is not None and host.get('target_commit') != guest.get('target_commit'):
            raise ValueError('Host and guest source target commit differs')
        provenance = guest
    return {key: provenance[key] for key in ('source_sha256', 'target_commit') if key in provenance}


def merge_case_results(host_results, guest_results, ordered_selected_ids, *,
                       artifact_path_map=None, source_provenance=None) -> list[CaseResult]:
    """Preserve selected order, contracts and relative outputs across hosts.

    Inputs may be CaseResult instances, JSON case records or complete reports.
    A plain source manifest must already be validated against the pinned host;
    a {'host': ..., 'guest': ...} pair is also checked here. This function never
    executes a case or marks missing/unsupported work as passed.
    """
    selected = [case if isinstance(case, str) else case.id for case in ordered_selected_ids]
    if len(selected) != len(set(selected)):
        raise ValueError('duplicate selected case identifiers')
    source = _source_metadata(source_provenance)
    paths = sorted(((str(old).rstrip('/'), str(new).rstrip('/'))
                    for old, new in (artifact_path_map or {}).items()), key=lambda item: len(item[0]), reverse=True)
    merged = {}
    for environment, records in (('host', _records(host_results)), ('vm', _records(guest_results))):
        for record in records:
            data = asdict(record) if isinstance(record, CaseResult) else deepcopy(dict(record))
            identifier = data.get('id', '')
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', identifier):
                raise ValueError(f'Unsafe case identifier: {identifier}')
            if identifier in merged:
                raise ValueError(f'duplicate host/guest case result: {identifier}')
            status = data.get('status')
            if status not in _STATUSES:
                raise ValueError(f'Unknown case status: {status}')
            duration = float(data.get('duration', 0))
            if not math.isfinite(duration) or duration < 0:
                raise ValueError(f'Invalid duration for case {identifier}')
            notes = _remap(deepcopy(data.get('notes') or {}), paths)
            outputs = deepcopy(data.get('outputs') or {})
            if not isinstance(notes, dict) or not isinstance(outputs, dict):
                raise ValueError(f'Invalid evidence for case {identifier}')
            reason = str(data.get('reason') or '')
            error = str(data.get('error') or '')
            if status == 'passed' and notes.get('host_verification_pending'):
                raise ValueError(f'passed case cannot retain host_verification_pending: {identifier}')
            if status == 'pending':
                if notes.get('host_verification_pending') is not True:
                    raise ValueError(f'Pending case requires notes.host_verification_pending=True: {identifier}')
                requests = notes.get('host_parity_requests')
                if not isinstance(requests, list) or not requests:
                    raise ValueError(f'Pending case requires nonempty host_parity_requests list: {identifier}')
            if status == 'unsupported':
                reason = reason or error or str(notes.get('unsupported_reason') or '')
                if not reason:
                    raise ValueError(f'Unsupported case requires explicit reason: {identifier}')
                if outputs:
                    raise ValueError(f'Unsupported case cannot contain executed outputs: {identifier}')
            if environment == 'vm' and source:
                notes['target_source'] = deepcopy(source)
            merged[identifier] = CaseResult(id=identifier, suite=str(data.get('suite') or ''), status=status,
                                            duration=duration, error=error, notes=notes, outputs=outputs,
                                            execution_environment=environment, reason=reason)
    missing = set(selected) - set(merged)
    extra = set(merged) - set(selected)
    if missing or extra:
        raise ValueError(f'Result inventory mismatch: missing={sorted(missing)}, extra={sorted(extra)}')
    return [merged[identifier] for identifier in selected]


def baseline_artifacts(result: CaseResult, download_root: str | Path) -> dict[str, Path]:
    """Resolve fetched exports inside their case directory without path escape."""
    if result.status == 'unsupported':
        if result.outputs:
            raise ValueError('Unsupported case cannot have baseline outputs')
        return {}
    root = Path(download_root).resolve()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', result.id):
        raise ValueError(f'Unsafe case identifier: {result.id}')
    case_dir = (root / 'cases' / result.id).resolve()
    if not case_dir.is_relative_to(root):
        raise ValueError('Case artifact directory escapes downloaded root')
    resolved = {}
    for name, relative in result.outputs.items():
        if not isinstance(relative, (str, Path)) or Path(relative).is_absolute():
            raise ValueError(f'Baseline output must use a relative artifact path: {relative}')
        path = (case_dir / relative).resolve()
        if not path.is_relative_to(case_dir):
            raise ValueError(f'Baseline output escapes case directory: {relative}')
        if not path.is_file():
            raise ValueError(f'Baseline output is missing: {path}')
        resolved[name] = path
    return resolved


def result_counts(results) -> dict[str, int]:
    counts = dict.fromkeys(_FINAL_STATUSES, 0)
    for result in results:
        if result.status not in _STATUSES:
            raise ValueError(f'Unknown case status: {result.status}')
        counts[result.status] = counts.get(result.status, 0) + 1
    return counts


def result_status(results, *, complete=True) -> str:
    counts = result_counts(results)
    if counts['failed']:
        return 'failed'
    if not complete:
        return 'incomplete'
    if counts.get('pending'):
        return 'pending-host-verification'
    return 'partial' if counts['unsupported'] else 'passed'
