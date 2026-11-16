"""Reference metadata hooks need no QApplication or global event interception."""
from types import ModuleType, SimpleNamespace
import sys

import pytest


def test_constructor_hook_preserves_arguments_result_and_metadata_order():
    from pancake_conformance.adapters import chimpstackr_ui
    assert hasattr(chimpstackr_ui, 'after_constructor'), 'Safe constructor metadata hook is missing'
    calls = []
    result = object()

    class Target:
        def __init__(self, *args, **kwargs):
            calls.append(('original', self, args, kwargs))
            self.ready = True
            return result

    original = Target.__init__
    def metadata(instance):
        assert instance.ready
        calls.append(('metadata', instance))
    chimpstackr_ui.after_constructor(Target, metadata)
    instance = object.__new__(Target)
    assert Target.__init__(instance, 7, setting='value') is result
    assert calls == [('original', instance, (7,), {'setting': 'value'}), ('metadata', instance)]
    assert Target.__init__.__wrapped__ is original


def test_constructor_failure_preserves_exact_exception_and_skips_metadata():
    from pancake_conformance.adapters import chimpstackr_ui
    assert hasattr(chimpstackr_ui, 'after_constructor'), 'Safe constructor metadata hook is missing'
    error = ValueError('original constructor failed')
    calls = []

    class Target:
        def __init__(self, *, setting):
            calls.append(setting)
            raise error
    chimpstackr_ui.after_constructor(Target, lambda instance: calls.append('metadata'))
    with pytest.raises(ValueError) as caught:
        Target(setting=19)
    assert caught.value is error
    assert calls == [19]


class Widget:
    def __init__(self, text=''):
        self.identifier = self.name = self.description = None
        self.content = text
    def setAccessibleIdentifier(self, value):
        self.identifier = value
    def setAccessibleName(self, value):
        self.name = value
    def setAccessibleDescription(self, value):
        self.description = value
    def text(self):
        return self.content
    def toPlainText(self):
        return self.content


def test_identifier_installer_hooks_only_completed_window_constructors(monkeypatch):
    from pancake_conformance.adapters.chimpstackr_ui import install_identifiers
    calls, filters, factories = [], [], []
    accessible = SimpleNamespace(installFactory=factories.append)
    class QObject:
        def __init__(self, parent=None):
            pass
    qt = ModuleType('PySide6')
    qt.QtCore = SimpleNamespace(QObject=QObject)
    qt.QtGui = SimpleNamespace(QAccessible=accessible)
    qt.QtWidgets = SimpleNamespace(QAccessibleWidget=object, QWidget=Widget, QLabel=Widget)
    monkeypatch.setitem(sys.modules, 'PySide6', qt)

    class Window(Widget):
        def __init__(self, *, token):
            super().__init__()
            calls.append(('window', token))
            for attr in ('stack_btn', 'export_btn', 'viewer', 'info_label', 'device_label', 'zoom_btn'):
                setattr(self, attr, Widget())
            self.viewport_widget = Widget()
            self.viewer.viewport = lambda: self.viewport_widget
            self.import_button = Widget()
            self.toolbar = SimpleNamespace(widgetForAction=lambda action: self.import_button)
            self.act_add = object()
            self.sidebar = SimpleNamespace(frames=Widget(), results=Widget())
            self.mode_switch = SimpleNamespace(buttons=[Widget(), Widget()])
            attributes = ('align_combo', 'autocrop_switch', 'adv_toggle', 'kernel_spin', 'pyramid_spin',
                          'contrast_thresh_spin', 'feather_spin', 'smoothing_spin', 'slab_spin', 'ref_combo',
                          'scale_spin', 'breathing_spin', 'precision_switch')
            self.inspector = SimpleNamespace(**{name: Widget() for name in attributes},
                                              method_group=SimpleNamespace(cards={'hybrid': Widget()}))
            self.activity = SimpleNamespace(**{name: Widget() for name in ('bar', 'detail', 'pause_btn', 'stop_btn')})

    class SettingsDialog(Widget):
        def __init__(self, parent):
            super().__init__()
            calls.append(('settings', parent))
            for attr in ('theme_combo', 'mode_combo', 'gpu_combo', 'remeasure', 'auto_update_switch', 'prerelease_switch'):
                setattr(self, attr, Widget())
            self.lightroom_card = SimpleNamespace(status_label=Widget('Rendered Lightroom status'),
                                                  action_button=Widget(), manage_button=Widget())

    class ExportDialog(Widget):
        def __init__(self, shape, parent=None):
            super().__init__()
            calls.append(('export', shape, parent))
            for attr in ('format_combo', 'depth_combo', 'quality', 'compression', 'ok'):
                setattr(self, attr, Widget())

    class UpdateDialog(Widget):
        def __init__(self, *, release):
            super().__init__()
            calls.append(('update', release))
            self.notes = Widget('Final rendered release notes')
            for attr in ('auto', 'skip_btn', 'later_btn', 'main_btn'):
                setattr(self, attr, Widget())

    class AboutDialog(Widget):
        def __init__(self):
            super().__init__()
            self.version = Widget('Version v3')
        def findChildren(self, kind):
            return [self.version]

    for module_name, cls in [('src.MainWindow', Window), ('src.MainWindow.SettingsWidget', SettingsDialog),
                             ('src.MainWindow.ImageSavingDialog', ExportDialog), ('src.MainWindow.UpdateDialog', UpdateDialog)]:
        module = ModuleType(module_name)
        setattr(module, cls.__name__, cls)
        if module_name == 'src.MainWindow':
            module.AboutDialog = AboutDialog
        monkeypatch.setitem(sys.modules, module_name, module)
    class AboutDialog(Widget):
        pass
    sys.modules["src.MainWindow"].AboutDialog = AboutDialog
    app = SimpleNamespace(installEventFilter=filters.append)
    install_identifiers(app)
    assert filters == [], 'Application-wide event filters convert unrelated worker QObjects through Python'
    assert len(factories) == 1, 'Read-only native viewer accessibility factory must remain installed'
    window = Window(token='original')
    settings = SettingsDialog(window)
    export = ExportDialog((129, 193, 3), parent=window)
    update = UpdateDialog(release='v3')
    assert calls == [('window', 'original'), ('settings', window), ('export', (129, 193, 3), window), ('update', 'v3')]
    assert window.identifier == 'main.window'
    assert window.viewport_widget.identifier == 'viewer'
    assert window.viewer.identifier == 'viewer'
    assert window.import_button.identifier == 'import.files'
    assert window.sidebar.frames.identifier == window.sidebar.frames.name == 'frames'
    assert window.sidebar.results.identifier == window.sidebar.results.name == 'results'
    assert window.inspector.method_group.cards['hybrid'].identifier == 'method.hybrid'
    assert settings.identifier == 'settings.window'
    assert settings.lightroom_card.status_label.description == 'Rendered Lightroom status'
    assert export.identifier == 'export.window' and export.ok.identifier == 'export.confirm'
    assert update.identifier == 'updates.window' and update.notes.description == 'Final rendered release notes'
    assert app._conformance_accessibility_factory[0] is factories[0]

    about = AboutDialog()
    assert about.identifier == 'about.window'
    assert about.version.identifier == 'about.version'
    assert about.version.description == 'Version v3'
