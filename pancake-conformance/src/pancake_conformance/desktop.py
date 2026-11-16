"""Exclusive desktop ownership for native UI sessions, across CLI processes."""
import fcntl
import os
from pathlib import Path
import tempfile


class DesktopLease:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(tempfile.gettempdir()) / f"pancake-conformance-desktop-{os.getuid()}.lock"
        self._stream = None

    def acquire(self):
        if self._stream is not None:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+")
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            stream.close()
            raise RuntimeError("Native desktop is in use by another conformance session") from exc
        stream.seek(0)
        stream.truncate()
        stream.write(str(os.getpid()) + "\n")
        stream.flush()
        self._stream = stream
        return self

    def release(self):
        if self._stream is not None:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()
