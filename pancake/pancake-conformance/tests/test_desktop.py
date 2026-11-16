import pytest


def test_desktop_lease_rejects_concurrent_sessions_and_releases(tmp_path):
    from pancake.desktop import DesktopLease
    path = tmp_path / "desktop.lock"
    with DesktopLease(path):
        with pytest.raises(RuntimeError, match="desktop.*use"):
            DesktopLease(path).acquire()
    with DesktopLease(path):
        pass


def test_desktop_lease_releases_on_exception(tmp_path):
    from pancake.desktop import DesktopLease
    path = tmp_path / "desktop.lock"
    with pytest.raises(ValueError):
        with DesktopLease(path):
            raise ValueError("test failure")
    lease = DesktopLease(path).acquire()
    lease.release()
    lease.release()
