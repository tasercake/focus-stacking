"""Linux native accessibility sessions on a private X11 desktop.

AT-SPI supplies observations/actions; XTest (xdotool) supplies real keyboard and
pointer input. No application imports or in-process control channel is used.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time

from .macos_ui import MacOSUISession


@contextmanager
def isolated_desktop(directory, environment):
    """Own an X server, window manager and accessibility bus for this run."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for command in ('Xvfb', 'openbox', 'xdotool', 'xprop', 'dbus-daemon'):
        if not shutil.which(command):
            raise RuntimeError(f'Linux GUI tests require {command}; see docs/linux.md')
    processes = []
    streams = []
    try:
        env = dict(environment)
        for key in ('AT_SPI_BUS_ADDRESS', 'DBUS_SESSION_BUS_ADDRESS', 'DBUS_STARTER_ADDRESS',
                    'DBUS_STARTER_BUS_TYPE', 'SESSION_MANAGER', 'WAYLAND_DISPLAY'):
            env.pop(key, None)
        runtime = directory.resolve() / 'runtime'
        runtime.mkdir(mode=0o700, exist_ok=True)
        env['XDG_RUNTIME_DIR'] = str(runtime)
        log = (directory / 'desktop.log').open('w')
        streams.append(log)
        read_fd, write_fd = os.pipe()
        try:
            server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1440x1000x24', '-nolisten', 'tcp', '-ac'],
                                      pass_fds=(write_fd,), stdout=log, stderr=log, start_new_session=True)
            processes.append(server)
            os.close(write_fd)
            write_fd = None
            with selectors.DefaultSelector() as poller:
                poller.register(read_fd, selectors.EVENT_READ)
                if not poller.select(15):
                    raise RuntimeError('Xvfb did not start; inspect desktop.log')
            display = os.read(read_fd, 32).decode().strip()
            if not display.isdigit():
                raise RuntimeError('Xvfb failed to allocate a display; inspect desktop.log')
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)
        env.update(DISPLAY=':' + display, QT_QPA_PLATFORM='xcb', QT_LINUX_ACCESSIBILITY_ALWAYS_ON='1',
                   NO_AT_BRIDGE='0', XDG_CURRENT_DESKTOP='', DESKTOP_SESSION='', QT_QPA_PLATFORMTHEME='generic', PANCAKE_CONFORMANCE_LINUX_DESKTOP='1')
        # D-Bus activation inherits the daemon's startup environment. Start it
        # only after selecting the private display and service home, otherwise
        # file managers and accessibility services could attach to the host.
        service_home = directory.resolve() / 'home'
        service_home.mkdir(exist_ok=True)
        env.update(HOME=str(service_home), XDG_CONFIG_HOME=str(service_home / 'config'),
                   XDG_CACHE_HOME=str(service_home / 'cache'), XDG_DATA_HOME=str(service_home / 'data'))
        bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address'],
                               stdout=subprocess.PIPE, stderr=log, text=True, env=env, start_new_session=True)
        processes.append(bus)
        env['DBUS_SESSION_BUS_ADDRESS'] = bus.stdout.readline().strip()
        wm = subprocess.Popen(['openbox', '--sm-disable'], env=env, stdout=log, stderr=log, start_new_session=True)
        processes.append(wm)
        # The EWMH supporting-window property appears once Openbox owns this display.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            check = subprocess.run(['xprop', '-root', '_NET_SUPPORTING_WM_CHECK'], env=env, capture_output=True, text=True)
            if 'window id #' in check.stdout:
                break
            if wm.poll() is not None:
                raise RuntimeError('Openbox failed to start; inspect desktop.log')
            time.sleep(.05)
        else:
            raise RuntimeError('Openbox did not claim its display; inspect desktop.log')
        yield env
    finally:
        for process in reversed(processes):
            MacOSUISession._reap(process)
            if process.stdout:
                process.stdout.close()
        for stream in streams:
            stream.close()


class LinuxUISession(MacOSUISession):
    def __init__(self, process, directory, environment):
        self.process, self.pid, self.directory = process, process.pid, Path(directory)
        self.environment = environment
        self._trace = (self.directory / 'ui-actions.jsonl').open('a')
        self._stderr = (self.directory / 'ui-driver.stderr').open('a')
        helper = Path(__file__).with_name('native_linux.py')
        self._helper = subprocess.Popen([environment.get('PANCAKE_ATSPI_PYTHON', '/usr/bin/python3'), '-u', str(helper)],
                                        env={k: v for k, v in environment.items() if k not in ("PYTHONPATH", "COVERAGE_PROCESS_START")}, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self._stderr, text=True, bufsize=1, start_new_session=True)
        try:
            self._request('trust')
        except BaseException:
            self._reap(self._helper)
            self._trace.close()
            self._stderr.close()
            raise

    def __enter__(self):
        # Do not cache Qt's provisional, empty AT-SPI application during startup.
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(self.pid), '--name', '.'],
                                    env=self.environment, capture_output=True, text=True)
            if result.returncode == 0:
                break
            if self.process.poll() is not None:
                self.close()
                raise RuntimeError('GUI exited before publishing its window')
            time.sleep(.1)
        return super().__enter__()

    def click(self, selector, **kwargs):
        wanted = self._selector(selector)
        if wanted.get('role') == 'AXMenuItem':
            def matches(snap):
                return any(all(node.get(k) == v for k, v in wanted.items())
                           and all(n > 0 for n in node['size']) for node in snap['nodes'])
            snapshot = self.snapshot()
            if not matches(snapshot):
                # Qt publishes menu contents only while their real popup is open.
                menus = [n for n in snapshot['nodes'] if n['role'] == 'AXMenuBarItem']
                for menu in menus:
                    super().click({'path': menu['path']})
                    snapshot = self.snapshot()
                    if matches(snapshot):
                        break
                    self.key('escape')
                else:
                    raise AssertionError(f'Menu item is not published: {wanted}')
        # Qt's synchronous AT-SPI action can block inside a modal dialog's exec().
        # XTest delivers the actual click without blocking accessibility replies.
        return super().click(selector, **{**kwargs, 'physical': True})

    def _close_processes(self):
        if self.process.poll() is None and self._helper.poll() is None:
            try:
                self.key('escape')
            except (RuntimeError, TimeoutError):
                pass
        return super()._close_processes()

    def select(self, selector, value, *, timeout=5):
        if self.node(selector).get('value') == value:
            return
        self.click(selector)
        item = self.wait(lambda snap: next((node for node in snap['nodes']
                         if node['role'] in ('AXMenuItem', 'AXRow', 'AXStaticText')
                         and (node.get('title') == value or node.get('value') == value)
                         and all(n > 0 for n in node['size'])), None),
                         timeout=timeout, description=f'visible popup option {value}')
        self.click({'path': item['path']})
        self.wait(lambda snap: any(node.get('value') == value and
                  all(node.get(k) == v for k, v in self._selector(selector).items()) for node in snap['nodes']),
                  timeout=timeout, description=f'committed popup selection {value}')

    def _file_path(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.directory.parent.resolve()):
            raise ValueError('File dialog path must stay inside case sandbox')
        self._request('file_path', path=str(path))

    def navigate_folder(self, folder):
        folder = Path(folder).resolve()
        if not folder.is_dir():
            raise ValueError('File dialog directory must exist')
        # Directory pickers accept the named directory on confirmation. Leave
        # that final click to the case so cancellation/acceptance stays observable.
        self._file_path(folder)

    def choose_file(self, path):
        if not Path(path).is_file():
            raise ValueError('Open input must exist')
        self._file_path(path)
        self.key('return')
        self.wait(lambda snap: not any(node.get('id') == 'open-panel' for node in snap['nodes']), description='file imported')

    def save_file(self, path):
        path = Path(path).resolve()
        if path.exists():
            raise ValueError('Conformance export must not overwrite an existing file')
        self.wait(lambda snap: any(n.get('id') == 'save-panel' for n in snap['nodes']), description='Save panel')
        self._file_path(path)
        self.key('return')
        self.wait(lambda snap: path.is_file() and not any(n.get('id') == 'save-panel' for n in snap['nodes']),
                  description='export written inside sandbox')
        return path
