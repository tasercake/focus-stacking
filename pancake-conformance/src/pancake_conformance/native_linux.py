"""JSON-lines AT-SPI/XTest transport, executed by the system GI Python."""
import json
import os
import subprocess
import sys
import time

import gi

gi.require_version('Atspi', '2.0')
from gi.repository import Atspi, GLib  # noqa: E402

TRANSIENTS = []


ROLES = {'application': 'AXApplication', 'frame': 'AXWindow', 'dialog': 'AXWindow',
         'alert': 'AXWindow', 'window': 'AXWindow', 'file chooser': 'AXWindow',
         'push button': 'AXButton', 'toggle button': 'AXCheckBox', 'check box': 'AXCheckBox',
         'radio button': 'AXRadioButton', 'combo box': 'AXPopUpButton', 'label': 'AXStaticText',
         'text': 'AXTextField', 'entry': 'AXTextField', 'spin button': 'AXIncrementor',
         'list': 'AXList', 'list item': 'AXRow', 'table': 'AXList', 'table cell': 'AXRow',
         'menu': 'AXMenu', 'menu bar': 'AXMenuBar', 'menu item': 'AXMenuItem',
         'check menu item': 'AXMenuItem', 'radio menu item': 'AXMenuItem',
         'popup menu': 'AXMenu', 'canvas': 'AXImage', 'scroll pane': 'AXScrollArea'}


def xdo(*args):
    return subprocess.run(['xdotool', *map(str, args)], check=True, capture_output=True, text=True).stdout.strip()


def tree(pid):
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(False)
    desktop = Atspi.get_desktop(0)
    apps = []
    for i in range(desktop.get_child_count()):
        candidate = desktop.get_child_at_index(i)
        if candidate is not None and candidate.get_process_id() == pid and candidate.get_child_count() > 0:
            apps.append(candidate)
    if not apps:
        return [], {}
    nodes, objects = [], {}

    def visit(obj, path):
        if len(path) > 30 or len(nodes) > 5000:
            return
        try:
            if len(path) <= 2:
                obj.clear_cache()
            role = obj.get_role_name()
            state = obj.get_state_set()
            showing = state.contains(Atspi.StateType.SHOWING)
            if not showing and role not in ('application', 'popup menu', 'menu', 'menu bar', 'menu item', 'check menu item', 'radio menu item'):
                return
            title, identifier = obj.get_name(), obj.get_accessible_id()
            ext = obj.get_extents(Atspi.CoordType.SCREEN) if 'Component' in obj.get_interfaces() else None
            interfaces = obj.get_interfaces()
            value = title
            if 'Text' in interfaces:
                value = Atspi.Text.get_text(obj, 0, -1)
            if 'Value' in interfaces:
                value = obj.get_current_value()
                value = int(value) if value == int(value) else value
            if role in ('check box', 'toggle button', 'radio button', 'check menu item', 'radio menu item'):
                value = int(state.contains(Atspi.StateType.CHECKED))
            if role in ('menu', 'menu item') and obj.get_parent() and obj.get_parent().get_role_name() == 'menu bar':
                mapped_role = 'AXMenuBarItem'
            else:
                mapped_role = ROLES.get(role, 'AXGroup')
            if role == 'dialog' and 'file name' in ' '.join(
                    (obj.get_child_at_index(i).get_name() or '').lower() for i in range(obj.get_child_count())):
                identifier = 'save-panel' if 'save' in title.lower() else 'open-panel'
            node = {'path': path, 'id': identifier or '', 'role': mapped_role,
                    'title': title, 'value': value, 'description': obj.get_description(),
                    'enabled': state.contains(Atspi.StateType.ENABLED),
                    'position': [ext.x, ext.y] if ext else [0, 0],
                    'size': [ext.width, ext.height] if ext and showing else [0, 0]}
            if role in ('dialog', 'alert', 'file chooser'):
                node['subrole'] = 'AXDialog'
            nodes.append(node)
            objects[tuple(path)] = obj
            for index in range(obj.get_child_count()):
                child = obj.get_child_at_index(index)
                if child:
                    visit(child, path + [index])
        except GLib.Error:
            return
    for index, app in enumerate(apps):
        visit(app, [index])
    # Unparented native popups may be announced as events without appearing in
    # the application's child list (Qt context menus use this AT-SPI pattern).
    for index, source in enumerate(TRANSIENTS):
        try:
            if (source.get_process_id() == pid and source.get_role_name() in ('popup menu', 'menu')
                    and source.get_state_set().contains(Atspi.StateType.SHOWING)
                    and source not in objects.values()):
                visit(source, [len(apps), index])
        except GLib.Error:
            continue
    # File chooser dialogs are standard toolkit controls, identified by their
    # accessible File name entry, never target-specific widget knowledge.
    for node in nodes:
        if node['role'] == 'AXWindow' and node.get('subrole') == 'AXDialog':
            descendants = [n for n in nodes if n['path'][:len(node['path'])] == node['path']]
            message = next((n['value'] for n in descendants
                            if n['role'] == 'AXStaticText' and n.get('value')), '')
            for child in descendants:
                child['dialog_message'] = message
            if any(n['role'] == 'AXTextField' and n['title'].startswith(('File name', 'Directory:')) for n in descendants):
                node['id'] = 'save-panel' if any(n['title'] == 'Save' for n in descendants) else 'open-panel'
                for n in descendants:
                    if n['role'] == 'AXButton' and n['title'] in ('Open', 'Save', 'Choose', 'Select Folder'):
                        n['id'] = 'OKButton'
                    if n['role'] == 'AXButton' and n['title'] == 'Cancel':
                        n['id'] = 'CancelButton'
    return nodes, objects


def execute(request):
    command, pid = request['command'], request['pid']
    if command == 'trust':
        return {'trusted': True}
    nodes, objects = tree(pid)
    if command == 'snapshot':
        try:
            active = xdo('getactivewindow')
            frontmost = int(xdo('getwindowpid', active)) == pid
        except (ValueError, subprocess.CalledProcessError):
            frontmost = False
        return {'nodes': nodes, 'pid': pid, 'frontmost': frontmost}
    if command == 'raise':
        windows = xdo('search', '--pid', pid).splitlines()
        if windows:
            xdo('windowactivate', '--sync', windows[-1])
        return None
    if command == 'key':
        mods = [{'command': 'ctrl', 'option': 'alt', 'control': 'ctrl'}.get(m, m) for m in request.get('modifiers', [])]
        key = {'return': 'Return', 'tab': 'Tab', 'escape': 'Escape', 'right': 'Right', 'left': 'Left',
               'up': 'Up', 'down': 'Down', 'space': 'space', 'backspace': 'BackSpace'}.get(request['key'], request['key'])
        xdo('key', '--clearmodifiers', '+'.join([*mods, key]))
        return None
    if command == 'text':
        # xdotool's XKB mapping supports Unicode, including non-BMP code points.
        xdo('type', '--clearmodifiers', '--delay', '1', '--', request['text'])
        return None
    if command == 'screenshot':
        # Read X11 pixels directly, keeping the transport free of Python imaging dependencies.
        # ImageMagick is not required: GDK takes the actual root-window pixels.
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        root = Gdk.get_default_root_window()
        Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height()).savev(request['path'], 'png', [], [])
        return None
    if command == 'file_path':
        entries = [n for n in nodes if n['role'] == 'AXTextField' and n['title'].startswith(('File name', 'Directory:')) and all(n['size'])]
        if len(entries) != 1:
            raise RuntimeError(f'Expected one file-name entry, found {len(entries)}')
        entry = objects[tuple(entries[0]['path'])]
        if not entry.set_text_contents(request['path']):
            raise RuntimeError('File dialog rejected path')
        if Atspi.Text.get_text(entry, 0, -1) != request['path']:
            raise RuntimeError('File dialog did not retain the requested path')
        entry.grab_focus()
        return None
    selector = request.get('selector', {})
    matches = [n for n in nodes if all(n.get(k) == v for k, v in selector.items())
               and (command != 'click' or all(length > 0 for length in n['size']))]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one accessible control for {selector}; found {len(matches)}')
    node = matches[0]
    obj = objects[tuple(node['path'])]
    if command == 'focus':
        return obj.grab_focus()
    if command == 'set':
        return obj.set_text_contents(str(request['value']))
    if command == 'press':
        actions = [obj.get_action_name(i) for i in range(obj.get_n_actions())]
        if not actions or not obj.do_action(0):
            raise RuntimeError(f'Control has no successful native action: {node}')
        return None
    x, y = node['position']
    w, h = node['size']
    if w <= 0 or h <= 0:
        raise RuntimeError(f'Control is not visible: {node}')
    def point(position):
        return round(x + position[0] * w), round(y + position[1] * h)
    if command == 'click':
        xdo('mousemove', '--sync', *point(request.get('position', [.5, .5])))
        xdo('click', '--repeat', request.get('count', 1), '--delay', 80, 3 if request.get('button') == 'right' else 1)
    elif command == 'drag':
        start, end = point(request['start']), point(request['end'])
        xdo('mousemove', '--sync', *start)
        xdo('mousedown', 1)
        try:
            for i in range(1, 16):
                xdo('mousemove', '--sync', round(start[0] + (end[0] - start[0]) * i / 15),
                    round(start[1] + (end[1] - start[1]) * i / 15))
                time.sleep(.015)
        finally:
            xdo('mouseup', 1)
    elif command == 'scroll':
        xdo('mousemove', '--sync', *point([.5, .5]))
        mods = [{'command': 'ctrl', 'option': 'alt'}.get(m, m) for m in request.get('modifiers', [])]
        for mod in mods:
            xdo('keydown', mod)
        try:
            xdo('click', '--repeat', max(1, abs(request['dy']) // 15), 4 if request['dy'] > 0 else 5)
        finally:
            for mod in reversed(mods):
                xdo('keyup', mod)
    else:
        raise ValueError(f'Unknown command: {command}')
    return None


def main():
    # An isolated session bus is mandatory: never attach to the user's desktop.
    if os.environ.get('PANCAKE_CONFORMANCE_LINUX_DESKTOP') != '1':
        raise RuntimeError('Linux UI transport requires the isolated desktop runner')
    Atspi.set_timeout(2000, 2000)
    Atspi.set_main_context(GLib.MainContext.default())
    def shown(event, user_data=None):
        if event.detail1 and event.source not in TRANSIENTS:
            TRANSIENTS.append(event.source)
    listener = Atspi.EventListener.new(shown)
    listener.register('object:state-changed:showing')
    for line in sys.stdin:
        try:
            response = {'ok': True, 'result': execute(json.loads(line))}
        except Exception as error:
            response = {'ok': False, 'error': str(error)}
        print(json.dumps(response), flush=True)


if __name__ == '__main__':
    main()
