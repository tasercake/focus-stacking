"""Reference-only translation of canonical update-service requests.

The endpoint assignment is an opt-in request hook. Download, release parsing,
version comparison, integrity checks and cancellation use unchanged target code.
No installation helper is generated or launched.
"""
import hashlib
from pathlib import Path


def _version(value):
    if value is None:
        return None
    major, minor, patch, stable, commits = value
    return {"major": major, "minor": minor, "patch": patch,
            "prerelease": not bool(stable), "commits": commits}


def _asset(value):
    if value is None:
        return None
    return {"name": value.name, "url": value.url, "size": value.size, "sha256": value.sha256}


def dispatch(operation, arrays, options):
    from src import updater

    if operation == "service.updates.version":
        return {}, {"versions": [{"source": text, "version": _version(updater.parse_version(text)),
                                   "display": updater.display_version(text)}
                                  for text in options.get("versions", [])],
                    "current": updater.current_version(), "current_display": updater.display_version()}
    if operation == "service.updates.check":
        previous = updater.API
        try:
            if options.get("endpoint"):
                updater.API = options["endpoint"]
            release = updater.check(include_prerelease=options.get("include_prerelease", False),
                                    current=options.get("current_version"))
        finally:
            updater.API = previous
        value = None if release is None else {
            "tag": release.tag, "version": _version(release.version), "title": release.title,
            "notes": release.notes, "page": release.page, "prerelease": release.prerelease,
            "assets": [_asset(asset) for asset in release.assets], "native_asset": _asset(release.asset())}
        return {}, {"release": value}
    if operation == "service.updates.download":
        value = options["asset"]
        asset = updater.Asset(value["name"], value["url"], value.get("size", 0), value.get("sha256", ""))
        progress = []
        done = 0

        def on_progress(completed, total):
            nonlocal done
            done = completed
            progress.append([completed, total])

        threshold = options.get("cancel_after")
        def cancelled():
            return done >= threshold

        callback = on_progress if options.get("progress", True) or threshold is not None else None
        path = Path(updater.download(asset, options["destination"], progress=callback,
                                    cancelled=cancelled if threshold is not None else None,
                                    chunk=options.get("chunk_bytes", 1 << 20)))
        payload = path.read_bytes()
        return {}, {"path": str(path), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                    "progress": progress}
    if operation == "service.updates.installation":
        supported = updater.can_install()
        kind, target = updater.install_target()
        refusal = ""
        if not supported:
            try:
                updater.prepare_install(options.get("download", ""))
            except updater.UpdateError as error:
                refusal = str(error)
        return {}, {"supported": supported, "kind": kind, "target": target, "refusal": refusal}
    raise ValueError(f"Unsupported service operation: {operation}")
