"""First-run provisioning for a dedicated Tart guest; never controls host input."""
from __future__ import annotations

import fcntl
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

TART_VERSION = '2.41.1'
TART_SHA256 = 'e680a734febccfce7d4e910c1f7f13fc3b00f19a181c945e2d746de3214c32c2'
IMAGE = 'ghcr.io/cirruslabs/macos-tahoe-base@sha256:65c3133a633fda8753cf1f71f2d55727792d534a2125b0032466563dcc8e58fd'


def install_archive(archive, destination, digest):
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != digest:
        raise RuntimeError('Tart archive checksum mismatch')
    destination = Path(destination)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        with tarfile.open(archive) as stream:
            stream.extractall(temporary, filter='data')
        binary = Path(temporary) / 'tart.app/Contents/MacOS/tart'
        if not binary.is_file() or not (binary.parent.parent / 'embedded.provisionprofile').is_file():
            raise RuntimeError('Tart archive has no app bundle')
        os.replace(temporary, destination)
    return destination / 'tart.app/Contents/MacOS/tart'


def vnc_endpoint(log):
    match = re.search(r'vnc://\S+', log)
    if match is None:
        raise RuntimeError('Tart VNC endpoint is not ready')
    endpoint = urlsplit(match[0])
    if not ipaddress.ip_address(endpoint.hostname).is_loopback:
        raise RuntimeError('Tart VNC endpoint must use loopback')
    return f'{endpoint.hostname}::{endpoint.port}', endpoint.password


def label_position(labels, wanted, size):
    matches = [box for label, box in labels if ''.join(label.split()) == ''.join(wanted.split())]
    if len(matches) > 1:
        raise RuntimeError(f'Ambiguous guest label: {wanted}')
    if not matches:
        return None
    x, y, width, height = matches[0]
    return round((x + width / 2) * size[0]), round((1 - y - height / 2) * size[1])


class Bootstrap:
    def __init__(self, vm, cache=None):
        self.vm = vm
        self.cache = Path(cache or Path.home() / 'Library/Caches/pancake-conformance')
        self.managed = False

    def ensure_host_and_vm(self):
        vm = self.vm
        if not vm._tart:
            destination = self.cache / ('tart-' + TART_VERSION)
            binary = destination / 'tart.app/Contents/MacOS/tart'
            self.cache.mkdir(parents=True, exist_ok=True)
            with (self.cache / 'tart-install.lock').open('a') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                if not binary.is_file():
                    self.cache.mkdir(parents=True, exist_ok=True)
                    print(f'GUI VM: downloading Tart {TART_VERSION}', flush=True)
                    archive = self.cache / 'tart.tar.gz'
                    with urlopen(f'https://github.com/openai/tart/releases/download/{TART_VERSION}/tart.tar.gz', timeout=60) as source, archive.open('wb') as sink:
                        shutil.copyfileobj(source, sink)
                    binary = install_archive(archive, destination, TART_SHA256)
                    archive.unlink()
            vm._tart = str(binary)
        state = vm._execute([vm._tart, 'get', vm.name, '--format', 'json'], check=False, timeout=20)
        marker = self.cache / 'guests' / (vm.name + '.json')
        if state.returncode == 0 and not marker.exists():
            return  # Existing custom guests retain their explicit configuration.
        self.managed = True
        if state.returncode:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text('{"schema_version":1,"complete":false}\n')
            print('GUI VM: cloning pinned macOS image (first download is about 27 GB)', flush=True)
            # Disable Tart's pruning without changing the caller's process environment.
            vm._execute(['/usr/bin/env', 'TART_NO_AUTO_PRUNE=1', vm._tart, 'clone', IMAGE, vm.name], timeout=7200)
            vm._execute([vm._tart, 'set', vm.name, '--cpu', '4', '--memory', '8192', '--display', '1440x1000', '--no-display-refit', '--disk-size', '80'])


    def _check_boot(self):
        process = self.vm._process
        if process is not None and process.poll() is not None:
            raise RuntimeError(f'Tart exited while provisioning {self.vm.name}; inspect private Tart log')

    def prepare_guest(self):
        import json
        import time
        import shlex
        import paramiko
        vm = self.vm
        self._check_boot()
        marker = self.cache / 'guests' / (vm.name + '.json')
        state = json.loads(marker.read_text())
        if not vm._started and not state.get('complete'):
            self._restart()
        if vm._started:
            state['boot_log'] = str(vm.output / 'tart.log')
            marker.write_text(json.dumps(state))
        self.log_path = Path(state.get('boot_log', vm.output / 'tart.log'))
        key = self.cache / 'keys' / vm.name
        key.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not key.exists():
            vm._execute(['/usr/bin/ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', key])
        vm.config['ssh_identity'] = str(key)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            self._check_boot()
            address = vm._execute([vm._tart, 'ip', vm.name], check=False, timeout=10)
            try:
                vm._ip = str(ipaddress.ip_address(address.stdout.strip()))
            except ValueError:
                time.sleep(1)
                continue
            if vm._ssh('true', check=False, timeout=10).returncode == 0:
                break
            client = paramiko.SSHClient()
            known_hosts = self.cache / 'keys' / (vm.name + '.known_hosts')
            if known_hosts.exists():
                client.load_host_keys(str(known_hosts))
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(vm._ip, username=vm.user, password='admin', allow_agent=False,
                               look_for_keys=False, timeout=5, auth_timeout=5)
                client.save_host_keys(str(known_hosts))
                public = Path(str(key) + '.pub').read_text().strip()
                _, stdout, stderr = client.exec_command('umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys')
                stdout.channel.sendall(public + '\n')
                stdout.channel.shutdown_write()
                if stdout.channel.recv_exit_status():
                    raise RuntimeError('Could not install dedicated guest SSH key')
                break
            except (OSError, paramiko.SSHException):
                time.sleep(1)
            finally:
                client.close()
        else:
            raise RuntimeError('Managed GUI VM SSH provisioning exceeded 240s')
        vm._wait_for_ssh()
        vm._uid = vm._ssh('/usr/bin/id -u').stdout.strip()
        vm._wait_for_aqua(vm._uid)
        self._restore_sip()
        print('GUI VM: checking guest tools', flush=True)
        vm._ssh('mkdir -p ~/.local/bin; defaults write NSGlobalDomain AppleKeyboardUIMode -int 3; sudo -n pmset -a sleep 0 displaysleep 0')
        uv = shutil.which('uv')
        if not uv:
            raise RuntimeError('Host uv is required to provision GUI guest')
        # Copy the already trusted native host uv binary; no Homebrew or installer shell.
        with Path(uv).resolve().open('rb') as source:
            vm._ssh('cat > ~/.local/bin/uv && chmod 755 ~/.local/bin/uv', input=source.read(), timeout=180)
        version = str(vm.config.get('python', '3.12.14'))
        vm._ssh('~/.local/bin/uv python install ' + shlex.quote(version), timeout=300)
        if vm._ssh('/usr/bin/xcrun --find swiftc', check=False).returncode:
            raise RuntimeError('Pinned GUI base image lacks Swift command-line tools')

    def _configure_display(self):
        import json
        source = Path(__file__).with_name('guest_display.swift').read_text()
        self.vm._ssh('/usr/bin/xcrun swift -', input=source, timeout=180)
        response = self.vm._ssh('/usr/bin/xcrun swift - --check', input=source, timeout=180)
        result = json.loads(response.stdout)
        (self.vm.output / 'vm-display.json').write_text(json.dumps(result, indent=2) + '\n')
        if result != {'width': 1440, 'height': 1000, 'pixel_width': 2880, 'pixel_height': 2000}:
            raise RuntimeError('Guest display must be 1440x1000 with a 2880x2000 Retina framebuffer')

    def _restart(self, *, recovery=False):
        import json
        import subprocess
        import time
        vm = self.vm
        vm._execute([vm._tart, 'stop', vm.name], timeout=60, check=False)
        if vm._process is not None:
            vm._process.wait(timeout=30)
        if vm._boot_log:
            vm._boot_log.close()
        self.log_path = vm.output / ('tart-recovery.log' if recovery else 'tart.log')
        vm._boot_log = self.log_path.open('w')
        self.log_path.chmod(0o600)
        argv = [vm._tart, 'run', vm.name, '--no-graphics', '--vnc-experimental', '--no-clipboard', '--no-audio']
        if recovery:
            argv.append('--recovery')
        vm._process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=vm._boot_log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        vm._started = True
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if vm._process.poll() is not None:
                raise RuntimeError('Tart exited during managed guest restart')
            if 'vnc://' in self.log_path.read_text():
                break
            time.sleep(1)
        else:
            raise RuntimeError('Managed guest VNC did not become ready')
        if not recovery:
            marker = self.cache / 'guests' / (vm.name + '.json')
            state = json.loads(marker.read_text())
            state['boot_log'] = str(self.log_path)
            marker.write_text(json.dumps(state))

    def _restore_sip(self):
        vm = self.vm
        if 'enabled' in vm._ssh('/usr/bin/csrutil status').stdout:
            return
        print('GUI VM: enabling SIP through guest Recovery', flush=True)
        self._restart(recovery=True)
        screen = self.screen()
        try:
            for label in ('Options', 'Continue', 'Utilities', 'Terminal'):
                if not screen.click(label, wait=180):
                    raise RuntimeError('Guest Recovery control missing: ' + label)
            screen.wait_text('bash', wait=60)
            print('GUI VM: Recovery terminal ready', flush=True)
            screen.text('csrutil enable\n')
            screen.wait_text('full boot security')
            screen.text('y\n')
            screen.wait_text('Authorized user')
            screen.text(vm.user + '\n')
            screen.wait_text('Password')
            screen.text('admin\n')
            screen.wait_text('System Integrity Protection is on', wait=180)
            screen.wait_text('Restart the machine')
            print('GUI VM: SIP enabled; shutting down Recovery', flush=True)
            screen.text('halt\n')
            if vm._process is not None:
                vm._process.wait(timeout=60)
        finally:
            screen.close()
        self._restart()
        vm._wait_for_ssh()
        vm._wait_for_aqua(vm._uid)
        if 'enabled' not in vm._ssh('/usr/bin/csrutil status').stdout:
            raise RuntimeError('Managed guest SIP restoration did not take effect')

    def screen(self):
        return GuestScreen(self.log_path.read_text(), self.vm.output)

    def ensure_permissions(self):
        import json
        import plistlib
        import shlex
        import time
        vm = self.vm
        runtime = getattr(vm, 'guest_runtime', vm.guest_project)
        directory = vm.guest_root + '/.bootstrap'
        vm._ssh('mkdir -p ' + shlex.quote(directory))
        result_path = directory + '/permissions.json'
        script_path = directory + '/permissions.py'
        vm._write_guest(script_path, permission_probe(result_path))
        label = 'me.pancake-conformance.permissions'
        plist_path = directory + '/permissions.plist'
        vm._write_guest(plist_path, plistlib.dumps({
            'Label': label, 'ProgramArguments': [runtime + '/.venv/bin/python', script_path],
            'RunAtLoad': True, 'LimitLoadToSessionType': 'Aqua', 'ProcessType': 'Interactive',
            'EnvironmentVariables': {'PATH': vm.guest_path},
            'StandardOutPath': directory + '/stdout', 'StandardErrorPath': directory + '/stderr'}))
        domain = 'gui/' + vm._uid
        screen = None
        try:
            for _attempt in range(3):
                vm._ssh(shlex.join(['/bin/launchctl', 'bootout', domain + '/' + label]), check=False)
                vm._ssh('/bin/rm -f ' + shlex.quote(result_path))
                vm._ssh(shlex.join(['/bin/launchctl', 'bootstrap', domain, plist_path]))
                deadline = time.monotonic() + 180
                result = {}
                while time.monotonic() < deadline:
                    response = vm._ssh('/bin/cat ' + shlex.quote(result_path), check=False)
                    if response.returncode == 0:
                        result = json.loads(response.stdout)
                        break
                    if screen is None:
                        screen = self.screen()
                    # Approve only the expected Python request in this dedicated guest.
                    self._approve_prompt(screen)
                    time.sleep(1)
                (vm.output / 'vm-permissions.json').write_text(json.dumps(result, indent=2) + '\n')
                if permissions_ready(result):
                    if screen is None:
                        screen = self.screen()
                    # ScreenCapture may return success before a second consent
                    # dialog appears. Clear that dialog before native text input.
                    time.sleep(1)
                    for _ in range(3):
                        if not self._approve_prompt(screen):
                            break
                        time.sleep(1)
                    marker = self.cache / 'guests' / (vm.name + '.json')
                    state = json.loads(marker.read_text())
                    state['complete'] = True
                    marker.write_text(json.dumps(state))
                    vm._ssh('/usr/bin/osascript -e \'tell application "System Settings" to quit\'', check=False)
                    return
                if screen is None:
                    screen = self.screen()
                print('GUI VM: granting guest Python permissions through System Settings', flush=True)
                for pane, needed in (('Accessibility', not result.get('trust', {}).get('trusted')),
                                     ('ScreenCapture', not result.get('screen') or not result.get('screenshot'))):
                    if needed:
                        self._grant_checkbox(pane, screen)
            raise RuntimeError('GUI VM permissions failed after three probes; inspect vm-permissions.json and guest-bootstrap.png')
        finally:
            vm._ssh(shlex.join(['/bin/launchctl', 'bootout', domain + '/' + label]), check=False)
            if screen is not None:
                screen.close()

    def _approve_prompt(self, screen):
        labels, _ = screen.labels()
        text = ' '.join(label for label, _ in labels)
        if 'python3.12' in text and ('System Events' in text or 'screen' in text):
            return screen.click('Allow', wait=0)
        return False

    def _grant_checkbox(self, pane, screen):
        import shlex
        import time
        vm = self.vm
        vm._ssh(shlex.join(['/usr/bin/open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_' + pane]))
        # Pinned Tahoe layout; find the Python row by name, not by row number.
        script = '''tell application "System Events"
 tell process "System Settings"
  set listing to outline 1 of scroll area 1 of group 1 of scroll area 1 of group 1 of group 3 of splitter group 1 of group 1 of window 1
  repeat with i from 1 to count rows of listing
   if exists checkbox "python3.12" of UI element 1 of row i of listing then
    set box to checkbox "python3.12" of UI element 1 of row i of listing
    if value of box is 0 then click box
    return "found"
   end if
  end repeat
 end tell
end tell'''
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            response = vm._ssh('/usr/bin/osascript', input=script, check=False)
            if response.returncode == 0 and response.stdout.strip() == 'found':
                break
            time.sleep(1)
        else:
            raise RuntimeError(f'Guest Python checkbox missing in {pane}')
        time.sleep(1)
        labels, _ = screen.labels()
        text = ' '.join(label for label, _ in labels)
        if 'Modify Settings' in text:
            screen.text('admin')
            if not screen.click('Modify Settings'):
                raise RuntimeError('Guest permission authentication button missing')
        screen.click('Quit & Reopen', wait=1)
        screen.click('Later', wait=1)


class GuestScreen:
    """OCR and input on Tart's private VNC endpoint, never the host desktop."""
    def __init__(self, log, directory):
        endpoint, password = vnc_endpoint(log)
        from vncdotool import api
        self.endpoint, self.password = endpoint, password
        self.client = api.connect(endpoint, password=password, timeout=5)
        self.path = Path(directory) / 'guest-bootstrap.png'

    def _capture(self):
        from vncdotool import api
        # Tart changes framebuffer size during boot. Reconnect for a full frame;
        # retaining vncdotool's old framebuffer can leave a black or corrupt image.
        self.client.disconnect()
        self.client = api.connect(self.endpoint, password=self.password, timeout=5)
        try:
            self.client.captureScreen(str(self.path))
            return True
        except TimeoutError:
            return False

    def labels(self):
        import Foundation
        import Vision
        from PIL import Image
        if not self._capture():
            return [], (1, 1)
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(
            Foundation.NSURL.fileURLWithPath_(str(self.path.resolve())), {})
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1)
        request.setRecognitionLanguages_(['en-US'])
        success, error = handler.performRequests_error_([request], None)
        if not success:
            raise RuntimeError(f'Guest OCR failed: {error}')
        labels = []
        for result in request.results():
            box = result.boundingBox()
            labels.append((str(result.topCandidates_(1)[0].string()),
                           (box.origin.x, box.origin.y, box.size.width, box.size.height)))
        with Image.open(self.path) as picture:
            return labels, picture.size

    def click(self, label, *, wait=30):
        import time
        deadline = time.monotonic() + wait
        while True:
            labels, size = self.labels()
            position = label_position(labels, label, size)
            if position:
                self.client.mouseMove(*position)
                self.client.mousePress(1)
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(1)

    def wait_text(self, text, *, wait=60):
        import time
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            labels, _ = self.labels()
            if text.casefold() in ' '.join(label for label, _ in labels).casefold():
                return
            time.sleep(1)
        raise RuntimeError('Guest screen did not show expected text: ' + text)

    def text(self, value):
        for character in value:
            self.client.keyPress('enter' if character == '\n' else character)

    def close(self):
        self.client.disconnect()


def permission_probe(result_path):
    return '''import ctypes,json,pathlib,subprocess
from pancake_conformance.macos_ui import native_helper
result={}
result['screen']=bool(ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics').CGRequestScreenCaptureAccess())
result['trust']=json.loads(subprocess.run([str(native_helper())],input='{"command":"trust"}\\n',text=True,capture_output=True,check=True).stdout)['result']
try:
    process=subprocess.run(['/usr/bin/osascript','-e','tell application "System Events" to key code 53'],capture_output=True,text=True,timeout=120)
    result['automation']=process.returncode==0
except subprocess.TimeoutExpired:
    result['automation']=False
process=subprocess.run(['/usr/sbin/screencapture','-x',%r+'.png'],capture_output=True,timeout=30)
result['screenshot']=process.returncode==0
pathlib.Path(%r).write_text(json.dumps(result))
''' % (result_path, result_path)


def permissions_ready(result):
    trust = result.get('trust', {})
    return all(result.get(key) is True for key in ('screen', 'automation', 'screenshot')) and all(
        trust.get(key) is True for key in ('trusted', 'post_event_access'))
