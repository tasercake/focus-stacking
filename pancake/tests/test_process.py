import sys
import os
import signal
import threading
import time

import pytest


def test_process_records_output_failure_and_artifacts(tmp_path):
    from pancake.process import ProcessRunner
    result = ProcessRunner().run([sys.executable, "-c", "import sys; print('hello'); print('bad',file=sys.stderr); sys.exit(3)"],
                                 cwd=tmp_path, env={}, directory=tmp_path)
    assert result.returncode == 3
    assert result.stdout.strip() == "hello"
    assert result.stderr.strip() == "bad"
    assert (tmp_path / "command.json").is_file()
    assert (tmp_path / "stdout.txt").read_text() == result.stdout


def test_process_timeout_is_bounded_and_reported(tmp_path):
    from pancake.process import ProcessRunner
    result = ProcessRunner().run([sys.executable, "-c", "import time; time.sleep(30)"],
                                 cwd=tmp_path, env={}, directory=tmp_path, timeout=0.05)
    assert result.timed_out
    assert result.returncode != 0
    assert result.duration < 5


def test_abort_reaps_target_that_ignores_termination(tmp_path):
    from pancake.process import ProcessRunner
    ready = tmp_path / "ready"
    script = "import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path('ready').write_text(str(os.getpid())); time.sleep(30)"
    def interrupt():
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        os.kill(os.getpid(), signal.SIGINT)
    worker = threading.Thread(target=interrupt, daemon=True)
    worker.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            ProcessRunner().run([sys.executable, "-c", script], cwd=tmp_path,
                                env={}, directory=tmp_path, timeout=30)
        pid = int(ready.read_text())
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    finally:
        worker.join(timeout=6)
        if ready.exists():
            try:
                os.killpg(int(ready.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
