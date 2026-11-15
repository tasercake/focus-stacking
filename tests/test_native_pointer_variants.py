"""Native pointer variants construct events without sending host input."""
from pathlib import Path
import subprocess

import pytest


def test_click_and_wheel_variants_are_explicit_native_requests():
    from stack_conformance.macos_ui import MacOSUISession
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


def test_native_pointer_constructor_preserves_click_count_and_button(tmp_path):
    from stack_conformance import macos_ui
    source = Path(macos_ui.__file__).with_name("native_macos.swift").read_text()
    assert "func pointerEvent(" in source, "Native pointer constructor is missing"
    start = source.index("func pointerEvent(")
    end = source.index("\nfunc pointer(", start)
    script = tmp_path / "pointer-construction.swift"
    script.write_text('import AppKit\nimport ApplicationServices\n'
                      'let inputSource = CGEventSource(stateID: .privateState)\n' + source[start:end] + '''
let event = pointerEvent(CGPoint(x:123,y:456), .rightMouseDown, button:.right, count:2)!
assert(event.location == CGPoint(x:123,y:456))
assert(event.getIntegerValueField(.mouseEventButtonNumber) == 1)
assert(event.getIntegerValueField(.mouseEventClickState) == 2)
print("pointer variants preserved")
''')
    result = subprocess.run(["swift", str(script)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "pointer variants preserved"


def test_focus_guard_polls_fresh_os_attribute_instead_of_cached_workspace(tmp_path):
    from stack_conformance import macos_ui
    source = Path(macos_ui.__file__).with_name("native_macos.swift").read_text()
    assert "func targetIsFrontmost(" in source, "Fresh OS focus query is missing"
    function = source.split("func targetIsFrontmost(", 1)[1].split("\nfunc execute(", 1)[0]
    script = tmp_path / "focus-construction.swift"
    script.write_text('import Foundation\ntypealias AXUIElement = Int\n'
                      'var active = false\nvar polls = 0\n'
                      'func attribute(_ element:Int,_ name:String)->AnyObject? { polls += 1; return NSNumber(value:active) }\n'
                      'func targetIsFrontmost(' + function + '''
assert(!targetIsFrontmost(0))
active = true
assert(targetIsFrontmost(0))
assert(polls == 2)
print("fresh focus")
''')
    result = subprocess.run(["swift", str(script)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "fresh focus"
