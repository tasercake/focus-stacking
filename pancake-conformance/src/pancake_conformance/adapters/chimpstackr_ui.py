"""ChimpStackr-only launch hooks: isolated preferences and native AX identifiers.

The application still starts through src.run.main. This module never calls its
stack, export, selection, comparison, or other business operations.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

IDENTIFIER_CONTRACT = (
    "main.window", "import.files", "stack.start", "export.start", "viewer",
    "frames", "results", "status", "device", "zoom", "mode.view", "mode.compare",
    "alignment", "autocrop", "advanced", "parameter.kernel", "parameter.levels",
    "parameter.contrast", "parameter.feather", "parameter.smoothing", "parameter.slab",
    "alignment.reference", "alignment.precision", "alignment.max_scale_step", "alignment.high_precision",
    "progress", "progress.detail", "stack.pause", "stack.stop",
    "method.laplacian", "method.hybrid", "method.weighted_average", "method.depth_map", "method.exposure_fusion",
    "settings.window", "settings.theme", "settings.device_mode", "settings.gpu", "settings.remeasure",
    "settings.auto_updates", "settings.prereleases", "settings.lightroom.status", "settings.lightroom.action", "settings.lightroom.manage",
    "export.window", "export.format", "export.depth", "export.quality", "export.compression", "export.confirm",
    "updates.window", "updates.notes", "updates.auto", "updates.skip", "updates.later", "updates.download",
)


def after_constructor(cls, metadata):
    """Assign read-only metadata only after the original constructor succeeds."""
    from functools import wraps

    original = cls.__init__

    @wraps(original)
    def initialized(instance, *args, **kwargs):
        result = original(instance, *args, **kwargs)
        metadata(instance)
        return result

    cls.__init__ = initialized


def install_identifiers(application):
    """Assign semantic identifiers after normal window construction."""
    from PySide6 import QtGui as qtg, QtWidgets as qtw

    class ViewerAccessible(qtw.QAccessibleWidget):
        def __init__(self, viewer):
            super().__init__(viewer, qtg.QAccessible.Canvas, "Image viewer")
            self.viewer = viewer

        def text(self, kind):
            if kind == qtg.QAccessible.Identifier:
                return "viewer"
            if kind == qtg.QAccessible.Description:
                viewer = self.viewer
                point = viewer.mapToScene(viewer.viewport().rect().center())
                return json.dumps({"zoom": viewer.zoom(), "center": [point.x(), point.y()],
                                   "split": viewer.split, "compare": viewer.compare,
                                   "has_image": viewer.has_image, "fit": viewer._fit_mode})
            return super().text(kind)

    interfaces = []

    def accessibility_factory(classname, obj):
        if classname == "ImageViewer":
            interface = ViewerAccessible(obj)
            interfaces.append(interface)
            return interface
        return None

    qtg.QAccessible.installFactory(accessibility_factory)
    application._conformance_accessibility_factory = (accessibility_factory, interfaces)

    def identify(widget, identifier):
        if widget is not None:
            widget.setAccessibleIdentifier(identifier)

    def main_window(window):
        identify(window, "main.window")
        for attr, identifier in (("stack_btn", "stack.start"), ("export_btn", "export.start"),
                                 ("viewer", "viewer"), ("info_label", "status"),
                                 ("device_label", "device"), ("zoom_btn", "zoom")):
            identify(getattr(window, attr, None), identifier)
        if not hasattr(window, "inspector"):
            return
        identify(window.toolbar.widgetForAction(window.act_add), "import.files")
        if sys.platform == "darwin":
            identify(window.viewer.viewport(), "viewer")
        window.viewer.viewport().setAccessibleName("Image viewer")
        identify(window.sidebar.frames, "frames")
        identify(window.sidebar.results, "results")
        # Qt 6.9 uses item-view accessible names for native AX identifiers.
        window.sidebar.frames.setAccessibleName("frames")
        window.sidebar.results.setAccessibleName("results")
        for index, identifier in enumerate(("mode.view", "mode.compare")):
            identify(window.mode_switch.buttons[index], identifier)
        inspector = window.inspector
        for attr, identifier in (("align_combo", "alignment"), ("autocrop_switch", "autocrop"),
                                 ("adv_toggle", "advanced"), ("kernel_spin", "parameter.kernel"),
                                 ("pyramid_spin", "parameter.levels"), ("contrast_thresh_spin", "parameter.contrast"),
                                 ("feather_spin", "parameter.feather"), ("smoothing_spin", "parameter.smoothing"),
                                 ("slab_spin", "parameter.slab"), ("ref_combo", "alignment.reference"),
                                 ("scale_spin", "alignment.precision"), ("breathing_spin", "alignment.max_scale_step"),
                                 ("precision_switch", "alignment.high_precision")):
            identify(getattr(inspector, attr), identifier)
        for key, card in inspector.method_group.cards.items():
            identify(card, f"method.{key}")
        for attr, identifier in (("bar", "progress"), ("detail", "progress.detail"),
                                 ("pause_btn", "stack.pause"), ("stop_btn", "stack.stop")):
            identify(getattr(window.activity, attr), identifier)

    def settings_dialog(dialog):
        identify(dialog, "settings.window")
        for attr, identifier in (("theme_combo", "settings.theme"), ("mode_combo", "settings.device_mode"),
                                 ("gpu_combo", "settings.gpu"), ("remeasure", "settings.remeasure"),
                                 ("auto_update_switch", "settings.auto_updates"), ("prerelease_switch", "settings.prereleases")):
            identify(getattr(dialog, attr), identifier)
        for attr, identifier in (("status_label", "settings.lightroom.status"),
                                 ("action_button", "settings.lightroom.action"),
                                 ("manage_button", "settings.lightroom.manage")):
            identify(getattr(dialog.lightroom_card, attr), identifier)

        # The existing explicit accessible name otherwise hides QLabel text in macOS AX.
        label = dialog.lightroom_card.status_label
        label.setAccessibleDescription(label.text())

    def export_dialog(dialog):
        identify(dialog, "export.window")
        for attr, identifier in (("format_combo", "export.format"), ("depth_combo", "export.depth"),
                                 ("quality", "export.quality"), ("compression", "export.compression"), ("ok", "export.confirm")):
            identify(getattr(dialog, attr), identifier)

    def update_dialog(dialog):
        identify(dialog, "updates.window")
        for attr, identifier in (("notes", "updates.notes"), ("auto", "updates.auto"),
                                 ("skip_btn", "updates.skip"), ("later_btn", "updates.later"),
                                 ("main_btn", "updates.download")):
            identify(getattr(dialog, attr), identifier)
        dialog.notes.setAccessibleDescription(dialog.notes.toPlainText())

    def about_dialog(dialog):
        identify(dialog, "about.window")
        for label in dialog.findChildren(qtw.QLabel):
            if label.text().startswith("Version "):
                identify(label, "about.version")
                label.setAccessibleDescription(label.text())

    from src.MainWindow import Window, AboutDialog
    from src.MainWindow.SettingsWidget import SettingsDialog
    from src.MainWindow.ImageSavingDialog import ExportDialog
    from src.MainWindow.UpdateDialog import UpdateDialog

    for cls, metadata in ((Window, main_window), (SettingsDialog, settings_dialog),
                          (ExportDialog, export_dialog), (UpdateDialog, update_dialog), (AboutDialog, about_dialog)):
        after_constructor(cls, metadata)


def install_worker_observers():
    """Install passive tracing at Qt-created Python thread entry boundaries."""
    try:
        from chimpstackr_observer import observe_current_thread
    except ModuleNotFoundError as exc:
        if exc.name == "chimpstackr_observer":
            return
        raise
    from functools import wraps
    from src.MainWindow import ImageLoader
    from src.MainWindow.Threading import Worker
    from src.MainWindow.MainLayout.ImageWidgets import ThumbnailWorker
    from src.MainWindow.SettingsWidget import BackgroundMeasurer
    from src.MainWindow.UpdateDialog import _Task as UpdateTask

    def instrument(cls):
        original = cls.run

        @wraps(original)
        def observed_run(self, *args, **kwargs):
            with observe_current_thread():
                return original(self, *args, **kwargs)

        cls.run = observed_run

    for cls in (Worker, ImageLoader, ThumbnailWorker, BackgroundMeasurer._Task, UpdateTask):
        instrument(cls)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, default=os.environ.get("CHIMPSTACKR_CONFORMANCE_TARGET_ROOT"), required=not bool(os.environ.get("CHIMPSTACKR_CONFORMANCE_TARGET_ROOT")))
    parser.add_argument("--settings-root", type=Path, default=os.environ.get("CONFORMANCE_UI_SETTINGS_DIR") or os.environ.get("CF_UI_SETTINGS_DIR"), required=not bool(os.environ.get("CONFORMANCE_UI_SETTINGS_DIR") or os.environ.get("CF_UI_SETTINGS_DIR")))
    parser.add_argument("--initial-settings", default=os.environ.get("CF_UI_INITIAL_SETTINGS", "{}"), help="Initial user preference JSON; existing values persist")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    args.settings_root.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.target_root.resolve()))
    from PySide6 import QtCore as qtc

    qtc.QSettings.setDefaultFormat(qtc.QSettings.IniFormat)
    qtc.QSettings.setPath(qtc.QSettings.IniFormat, qtc.QSettings.UserScope, str(args.settings_root.resolve()))
    preferences = qtc.QSettings(qtc.QSettings.IniFormat, qtc.QSettings.UserScope, "noah.peeters", "chimpstackr")
    for key, value in json.loads(args.initial_settings).items():
        if not preferences.contains(key):
            preferences.setValue(key, value)
    preferences.sync()

    from src import run
    # Configure only the service endpoint. All requests, parsing, preferences,
    # worker signals and dialogs continue through the original implementation.
    if endpoint := os.environ.get("CF_UI_UPDATE_FEED"):
        from src import updater
        updater.API = endpoint
    install_worker_observers()
    original = run._App.__init__

    def observed_init(application, arguments):
        original(application, arguments)
        install_identifiers(application)

    run._App.__init__ = observed_init
    sys.argv = ["chimpstackr", *args.paths]
    run.main()


if __name__ == "__main__":
    main()
