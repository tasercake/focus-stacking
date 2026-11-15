"""Native update workflows against an isolated, deterministic HTTP service."""
import json

from ..model import Case
from .interface import _menu
from .interface_settings import _open_preferences, checkbox_state


def release_payload():
    return [{"tag_name": "v999.0.0", "name": "Conformance release", "draft": False,
             "prerelease": False, "body": "# Conformance release notes\nGenerated local test release.",
             "html_url": "https://example.invalid/conformance-release", "assets": []}]


def dialog_present(snapshot):
    return any(node.get("role") == "AXWindow" and node.get("title") == "Software Update"
               for node in snapshot["nodes"])


def current_message(snapshot):
    return any(node.get("role") == "AXStaticText" and str(node.get("value", "")).endswith(" is the newest version.")
               for node in snapshot["nodes"])


def _check(ui):
    _menu(ui, "Check for Updates…")


def _routes(payload, status=200):
    return {"/releases": (status, {"Content-Type": "application/json"}, json.dumps(payload).encode())}


def _available(ctx):
    from .services import fixture_server
    with fixture_server(ctx, _routes(release_payload())) as base:
        with ctx.open_ui(service_endpoints={"updates": base + "/releases"}) as ui:
            _check(ui)
            ui.wait(dialog_present, description="new release dialog")
            assert ui.node("updates.download").get("title") == "Download…"
            assert not ui.node("updates.auto").get("value"), "Automatic checks must start disabled"
            # Native text browser exposes rendered content; no markdown implementation is assumed.
            ui.wait(lambda snap: "Conformance release notes" in json.dumps(snap), description="rendered release notes")
            _check(ui)
            assert sum(node.get("role") == "AXWindow" and node.get("title") == "Software Update"
                       for node in ui.snapshot()["nodes"]) == 1
            ui.click("updates.auto", physical=False)
            ui.wait(lambda snap: checkbox_state(snap, "updates.auto"), description="automatic updates enabled")
            ui.click("updates.auto", physical=False)
            ui.wait(lambda snap: not checkbox_state(snap, "updates.auto"), description="automatic updates restored")
            ui.click("updates.skip", physical=False)
            ui.wait(lambda snap: not dialog_present(snap), description="release skipped")
            # Manual checks must still show a deliberately skipped version.
            _check(ui)
            ui.wait(dialog_present, description="manual check bypasses skipped version")
            ui.click("updates.later", physical=False)
            ui.wait(lambda snap: not dialog_present(snap), description="release reminder dismissed")
            _open_preferences(ui)
            assert not checkbox_state(ui.snapshot(), "settings.auto_updates")
            from .interface import _close_settings
            _close_settings(ui)
    ctx.note("updates", {"manual_skip_bypass": True, "duplicate_dialog_prevented": True,
                         "automatic_checks_restored": False})


def _message(ctx, *, network_error):
    from .services import fixture_server
    with fixture_server(ctx, _routes([], 503 if network_error else 200)) as base:
        with ctx.open_ui(service_endpoints={"updates": base + "/releases"}) as ui:
            _check(ui)
            expected = "Couldn't check for updates" if network_error else "You're up to date"
            ui.wait((lambda snap: expected in json.dumps(snap)) if network_error else current_message,
                    description=expected)
            if network_error:
                ui.wait(lambda snap: "Check your internet connection and try again." in json.dumps(snap),
                        description="actionable update error")
            ui.click({"role": "AXButton", "title": "OK"}, physical=False)
            ui.wait(lambda snap: not any(node.get("role") == "AXButton" and node.get("title") == "OK"
                                        for node in snap["nodes"]), description="update message closed")


def update_cases():
    return [Case("interface.updates.available", "interface", _available,
                 "Local release notes, duplicate suppression, skip, manual retry and preference toggle", ("native_gui",)),
            Case("interface.updates.current", "interface", lambda ctx: _message(ctx, network_error=False),
                 "Successful empty release feed shows native up-to-date message", ("native_gui",)),
            Case("interface.updates.network-error", "interface", lambda ctx: _message(ctx, network_error=True),
                 "HTTP failure shows actionable native update error and remains usable", ("native_gui",))]
