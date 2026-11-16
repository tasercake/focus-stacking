"""Language-neutral update-service contracts with real local HTTP fixtures."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from types import SimpleNamespace
import threading
from urllib.parse import urlsplit

from ..model import Case


@contextmanager
def http_fixture(routes, *, ctx=None):
    requests = []
    if ctx is not None:
        inventory = {path: {"status": status, "headers": {name: str(value) for name, value in headers.items()},
                            "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
                     for path, (status, headers, body) in sorted(routes.items())}
        ctx.notes.setdefault("fixtures", {}).setdefault("service_http", []).append(inventory)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({"path": self.path, "headers": {name.lower(): value for name, value in self.headers.items()}})
            status, headers, body = routes.get(urlsplit(self.path).path, (404, {}, b"Not found"))
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, str(value))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(url=f"http://127.0.0.1:{server.server_port}", requests=requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if ctx is not None:
            ctx.notes.setdefault("service_http_requests", []).append(requests)


@contextmanager
def fixture_server(ctx, routes):
    """Serve `(status, headers, bytes)` routes and freeze their payload hashes."""
    with http_fixture(routes, ctx=ctx) as server:
        yield server.url


def _ok(result):
    assert result.ok, result.error
    return result.values


def _failed(result):
    assert not result.ok, "Invalid update operation unexpectedly succeeded"
    assert result.error, "Failed update operation has no diagnostic"


def assert_download(result, expected, *, progress=True, total=None):
    values = _ok(result)
    path = Path(values["path"])
    assert path.read_bytes() == expected, "Downloaded content changed"
    assert values["bytes"] == len(expected)
    assert values["sha256"] == hashlib.sha256(expected).hexdigest()
    observed = values["progress"]
    if progress:
        assert observed and observed[-1][0] == len(expected), "Download progress did not complete"
        assert all(first[0] < second[0] for first, second in zip(observed, observed[1:], strict=False))
        assert all(item[1] == (len(expected) if total is None else total) for item in observed), "Download total changed"
    else:
        assert observed == [], "Disabled progress produced callbacks"
    return path


def _versions(ctx):
    values = _ok(ctx.probe("service.updates.version", options={"versions": [
        "v1.2.3", "1", "1.2", "v2.0.0-rc1", "v2.0.0beta2", "v1.2.3-4-gabcdef-dirty",
        "v3.0.0.dirty", "vword", "not-a-version", "", None]}))
    items = values["versions"]
    assert items[0]["version"] == {"major": 1, "minor": 2, "patch": 3, "prerelease": False, "commits": 0}
    assert items[1]["version"]["minor"] == items[1]["version"]["patch"] == 0
    assert items[2]["version"]["patch"] == 0
    assert items[3]["version"]["prerelease"] is items[4]["version"]["prerelease"] is True
    assert items[5]["version"]["commits"] == 4 and items[5]["display"] == "1.2.3 (dev build abcdef)"
    assert items[6]["version"]["major"] == 3
    assert all(item["version"] is None for item in items[7:])
    assert items[7]["display"] == "vword"
    assert values["current"] and values["current_display"]
    ctx.note("version_contract", values)


def _release(tag, **options):
    return {"tag_name": tag, **options}


def _check(ctx, server, **options):
    return ctx.probe("service.updates.check", options={"endpoint": server.url + "/releases", **options})


def _release_policy(ctx):
    asset_name = ctx.target.fixtures.get("native_update_asset", "FocusStacker-macOS.dmg")
    feeds = [
        _release("v10.0.0", draft=True),
        _release("v3.0.0-rc1", prerelease=True, name="Preview", body="Preview notes"),
        _release("unparseable"),
        _release("v2.0.0", name="Stable", body="Release notes", html_url="https://example.invalid/release",
                 assets=[{"name": asset_name, "browser_download_url": "https://example.invalid/mac", "size": 17,
                          "digest": "sha256:" + "a" * 64},
                         {"name": "readme.txt", "browser_download_url": "https://example.invalid/readme", "digest": "md5:abc"}]),
    ]
    routes = {"/releases": (200, {"Content-Type": "application/json"}, json.dumps(feeds).encode())}
    with http_fixture(routes, ctx=ctx) as server:
        stable = _ok(_check(ctx, server, current_version="1.0.0"))["release"]
        preview = _ok(_check(ctx, server, current_version="1.0.0", include_prerelease=True))["release"]
        current = _ok(_check(ctx, server, current_version="2.0.0"))["release"]
        newer = _ok(_check(ctx, server, current_version="9.0.0"))["release"]
        invalid = _ok(_check(ctx, server, current_version="invalid"))["release"]
    assert stable["tag"] == "v2.0.0" and stable["title"] == "Stable"
    assert stable["notes"] == "Release notes" and stable["page"] == "https://example.invalid/release"
    assert not stable["prerelease"] and stable["assets"][0]["sha256"] == "a" * 64
    assert stable["assets"][1]["sha256"] == "" and stable["assets"][1]["size"] == 0
    assert stable["native_asset"] == stable["assets"][0]
    assert preview["tag"] == "v3.0.0-rc1" and preview["prerelease"] is True
    assert preview["native_asset"] is None
    assert current is newer is invalid is None
    assert len(server.requests) == 5
    assert all("per_page=10" in request["path"] for request in server.requests)
    assert all(request["headers"].get("user-agent") and request["headers"].get("accept") for request in server.requests)
    ctx.note("release_policy", {"stable": stable, "preview": preview})


def _release_empty(ctx):
    for feed in ([], [_release("bad"), _release("v2", draft=True), _release("v3-rc1", prerelease=True)]):
        with http_fixture({"/releases": (200, {}, json.dumps(feed).encode())}, ctx=ctx) as server:
            assert _ok(_check(ctx, server, current_version="1.0.0"))["release"] is None
    with http_fixture({"/releases": (200, {}, json.dumps([_release("v2.0.0")]).encode())}, ctx=ctx) as server:
        result = _ok(_check(ctx, server, current_version="1.0.0"))["release"]
        assert result["title"] == result["tag"] and result["notes"] == "" and result["assets"] == []
        assert result["page"].startswith("https://")


def _release_errors(ctx):
    for status, body in ((503, b"Service unavailable"), (200, b"{not valid json")):
        with http_fixture({"/releases": (status, {}, body)}, ctx=ctx) as server:
            _failed(_check(ctx, server, current_version="1.0.0"))
            assert len(server.requests) == 1


PAYLOAD = bytes(range(256)) * 17 + b"verified update payload"


def _download_options(ctx, server, **options):
    destination = ctx.directory / "downloads"
    destination.mkdir(exist_ok=True)
    asset = {"name": "update-payload.bin", "url": server.url + "/asset", "size": len(PAYLOAD),
             "sha256": hashlib.sha256(PAYLOAD).hexdigest()}
    asset.update(options.pop("asset", {}))
    return {"asset": asset, "destination": str(destination), "chunk_bytes": 127, **options}


def _download(ctx):
    with http_fixture({"/asset": (200, {"Content-Length": len(PAYLOAD)}, PAYLOAD)}, ctx=ctx) as server:
        options = _download_options(ctx, server)
        options["asset"]["sha256"] = options["asset"]["sha256"].upper()
        path = assert_download(ctx.probe("service.updates.download", options=options), PAYLOAD)
        assert server.requests[0]["headers"]["accept"] == "application/octet-stream"
    ctx.note("download_sha256", hashlib.sha256(path.read_bytes()).hexdigest())


def _download_no_length(ctx):
    with http_fixture({"/asset": (200, {}, PAYLOAD)}, ctx=ctx) as server:
        for size, progress in ((len(PAYLOAD), True), (0, True), (0, False)):
            options = _download_options(ctx, server, asset={"size": size}, progress=progress)
            assert_download(ctx.probe("service.updates.download", options=options), PAYLOAD, total=size, progress=progress)


def _download_errors(ctx):
    with http_fixture({"/asset": (200, {}, PAYLOAD), "/missing": (404, {}, b"Missing")}, ctx=ctx) as server:
        options = _download_options(ctx, server, asset={"sha256": ""})
        _failed(ctx.probe("service.updates.download", options=options))
        assert server.requests == [], "Missing checksum caused an unverified download"
        options = _download_options(ctx, server, asset={"sha256": "0" * 64})
        _failed(ctx.probe("service.updates.download", options=options))
        assert not (Path(options["destination"]) / options["asset"]["name"]).exists(), "Checksum failure retained unverified file"
        options = _download_options(ctx, server, asset={"url": server.url + "/missing"})
        _failed(ctx.probe("service.updates.download", options=options))
        # A directory at the intended output name is a real local I/O error.
        options = _download_options(ctx, server)
        (Path(options["destination"]) / options["asset"]["name"]).mkdir()
        _failed(ctx.probe("service.updates.download", options=options))


def _download_cancel(ctx):
    with http_fixture({"/asset": (200, {"Content-Length": len(PAYLOAD)}, PAYLOAD)}, ctx=ctx) as server:
        for threshold in (0, 127):
            options = _download_options(ctx, server, cancel_after=threshold)
            _failed(ctx.probe("service.updates.download", options=options))
            partial = Path(options["destination"]) / options["asset"]["name"]
            assert partial.read_bytes() == PAYLOAD[:threshold], "Cancelled download changed completed bytes"


def _source_install(ctx):
    values = _ok(ctx.probe("service.updates.installation", options={"download": str(ctx.directory / "not-installed.bin")}))
    assert values["supported"] is False and values["kind"] is None and values["target"] is None
    assert values["refusal"], "Source checkout did not explain self-update refusal"


def service_cases():
    return [Case(f"cli.service.{name}", "cli", run, description) for name, run, description in (
        ("version", _versions, "Semantic versions, prereleases and development build labels remain comparable"),
        ("release-policy", _release_policy, "Real release feed honors draft, prerelease and current-version policy"),
        ("release-empty", _release_empty, "Empty release feed and missing optional metadata remain valid"),
        ("release-errors", _release_errors, "HTTP and malformed release feeds fail with diagnostics"),
        ("download", _download, "Real streamed download verifies content and uppercase checksum"),
        ("download-no-length", _download_no_length, "Downloads tolerate absent length and optional progress reporting"),
        ("download-errors", _download_errors, "Missing or wrong checksum, network and filesystem errors prevent verified download"),
        ("download-cancel", _download_cancel, "User cancellation stops before download and between real chunks"),
        ("source-install", _source_install, "Source checkout refuses self-installation without staging or launch"),
    )]
