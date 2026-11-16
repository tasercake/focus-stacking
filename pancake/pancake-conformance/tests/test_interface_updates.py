def test_update_cases_cover_release_skip_no_update_and_network_error():
    from pancake.cases.interface_updates import update_cases
    cases = update_cases()
    assert {case.id for case in cases} == {
        "interface.updates.available", "interface.updates.current", "interface.updates.network-error"}
    assert all(case.suite == "interface" for case in cases)


def test_release_fixture_uses_canonical_http_payload_and_future_version():
    from pancake.cases.interface_updates import release_payload
    payload = release_payload()
    assert payload[0]["tag_name"] == "v999.0.0"
    assert not payload[0]["draft"] and not payload[0]["prerelease"]
    assert "Conformance release notes" in payload[0]["body"]


def test_native_dialog_contract_accepts_window_title_and_rendered_message():
    from pancake.cases.interface_updates import dialog_present, current_message
    assert dialog_present({"nodes": [{"role": "AXWindow", "title": "Software Update"}]})
    assert current_message({"nodes": [{"role": "AXStaticText", "value": "ChimpStackr 1.2.3 is the newest version."}]})
    assert not current_message({"nodes": [{"role": "AXStaticText", "value": "Checking for updates…"}]})
