"""Bounded external process execution with complete failure artifacts."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from .model import ProcessResult


class ProcessRunner:
    @staticmethod
    def _stop(child):
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            return child.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return child.communicate(timeout=5)

    def run(self, command, *, cwd, env, directory, timeout=120):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        command = list(map(str, command))
        (directory / "command.json").write_text(json.dumps({"argv": command, "cwd": str(cwd),
                                                          "timeout": timeout}, indent=2))
        start = time.monotonic()
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, errors="replace", start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stdout, stderr = self._stop(child)
        except BaseException:
            stdout, stderr = self._stop(child)
            (directory / "stdout.txt").write_text(stdout)
            (directory / "stderr.txt").write_text(stderr)
            raise
        result = ProcessResult(command, child.returncode, stdout, stderr, time.monotonic() - start, timed_out)
        (directory / "stdout.txt").write_text(stdout)
        (directory / "stderr.txt").write_text(stderr)
        return result
