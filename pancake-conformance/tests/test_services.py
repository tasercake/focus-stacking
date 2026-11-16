"""Service fixture and adapter contracts use real files and local HTTP."""
import hashlib
import importlib.util
from types import SimpleNamespace
import urllib.error
import urllib.request

import pytest


def services():
    assert importlib.util.find_spec("pancake_conformance.cases.services") is not None, "Service cases missing"
    from pancake_conformance.cases import services
    return services


def test_http_fixture_serves_bytes_errors_and_records_requests():
    payload = b"real local payload"
    with services().http_fixture({"/asset": (200, {"Content-Type": "application/octet-stream"}, payload),
                                  "/error": (503, {}, b"Unavailable")}) as server:
        request = urllib.request.Request(server.url + "/asset?query=1", headers={"Accept": "test/asset"})
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.read() == payload
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(server.url + "/error", timeout=2)
        assert error.value.code == 503
    assert [item["path"] for item in server.requests] == ["/asset?query=1", "/error"]
    assert server.requests[0]["headers"]["accept"] == "test/asset"


def test_download_check_rejects_wrong_content_and_incomplete_progress(tmp_path):
    payload = b"a complete verified update payload"
    path = tmp_path / "payload"
    path.write_bytes(payload)
    values = {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
              "progress": [[5, len(payload)], [len(payload), len(payload)]]}
    result = SimpleNamespace(ok=True, error="", values=values)
    services().assert_download(result, payload)
    path.write_bytes(b"changed")
    with pytest.raises(AssertionError, match="content"):
        services().assert_download(result, payload)
    path.write_bytes(payload)
    result.values = {**values, "progress": [[5, len(payload)]]}
    with pytest.raises(AssertionError, match="complete"):
        services().assert_download(result, payload)




def test_service_catalog_covers_policy_network_integrity_and_source_install():
    cases = services().service_cases()
    ids = {case.id for case in cases}
    assert len(ids) == len(cases)
    assert all(case.suite == "cli" for case in cases)
    for name in ("version", "release-policy", "release-empty", "release-errors", "download",
                 "download-no-length", "download-errors", "download-cancel", "source-install"):
        assert f"cli.service.{name}" in ids


def test_fixture_server_freezes_payload_contract_without_ephemeral_port():
    routes = {"/releases": (200, {"Content-Type": "application/json"}, b"[]")}
    contexts = [SimpleNamespace(notes={}), SimpleNamespace(notes={})]
    for context in contexts:
        with services().fixture_server(context, routes) as base_url:
            with urllib.request.urlopen(base_url + "/releases", timeout=2) as response:
                assert response.read() == b"[]"
    assert contexts[0].notes["fixtures"] == contexts[1].notes["fixtures"]
    frozen = contexts[0].notes["fixtures"]["service_http"][0]["/releases"]
    assert frozen["sha256"] == hashlib.sha256(b"[]").hexdigest()
    assert frozen["status"] == 200
