"""Native pointer variants construct events without sending host input."""

import pytest


def test_click_and_wheel_variants_are_explicit_native_requests():
    from pancake_conformance.macos_ui import MacOSUISession
    calls = []
    driver = object.__new__(MacOSUISession)
    driver._request = lambda command, **values: calls.append((command, values))
    driver.click("viewer", count=2)
    driver.click("frames", button="right")
    driver.scroll("viewer", 30, modifiers=("command",), units="line")
    assert calls == [
        ("click", {"selector": {"id": "viewer"}, "count": 2, "button": "left"}),
        ("click", {"selector": {"id": "frames"}, "count": 1, "button": "right"}),
        ("scroll", {"selector": {"id": "viewer"}, "dy": 30, "modifiers": ("command",), "units": "line"}),
    ]
    with pytest.raises(ValueError):
        driver.click("viewer", count=3)
