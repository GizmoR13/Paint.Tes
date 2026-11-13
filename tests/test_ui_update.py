import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit

from paint_tes.app import MainWindow
from paint_tes.config import ModelProfile, Settings
from paint_tes.dialogs import SettingsDialog
from paint_tes.i18n import apply_qt_language, retranslate_widgets, set_language
from paint_tes.workflow import build_workflow


def make_window(qtbot, tmp_path, monkeypatch, language="en"):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PAINT_TES_DATA", str(tmp_path / "data"))
    monkeypatch.setattr("paint_tes.dialogs.list_gpus", lambda: [])
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"loader-not-used")
    profile = ModelProfile(name="My local model", checkpoint=str(weights))
    window = MainWindow(Settings(language=language, profiles=[profile]))
    qtbot.addWidget(window)
    window.show()
    return window


def clean_close(window):
    for index in range(window.tabs.count()):
        doc = window.tabs.widget(index).document
        doc.saved_revision = doc.revision
    window.close()


def test_english_default_icons_and_live_polish(qtbot, tmp_path, monkeypatch):
    window = make_window(qtbot, tmp_path, monkeypatch)
    doc = window.add_document(Image.new("RGBA", (64, 64), "white"), "User title")
    window.prompt.setPlainText("User prompt / mój prompt")
    assert Settings().language == "en"
    assert window.menuBar().actions()[0].text() == "File"
    assert window.generate_button.text() == "Generate image"
    assert "Paint.TES" in window.windowTitle()
    assert window.top_toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    assert window.tools_toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    assert all(not action.icon().isNull() for action in window.top_actions.values())
    assert all(not action.icon().isNull() for action in window.tool_actions.values())
    assert window.top_actions["new"].toolTip() == "New (Ctrl+N)"
    set_language("pl")
    apply_qt_language()
    retranslate_widgets(window)
    assert window.menuBar().actions()[0].text() == "Plik"
    assert window.generate_button.text() == "Generuj obraz"
    assert window.top_actions["new"].toolTip() == "Nowy (Ctrl+N)"
    assert window.tool_actions["brush"].toolTip() == "Pędzel (B)"
    assert window.prompt.toPlainText() == "User prompt / mój prompt"
    assert window.tabs.widget(0) is doc
    assert window.model.currentText() == "My local model"
    set_language("en")
    apply_qt_language()
    retranslate_widgets(window)
    assert window.generate_button.text() == "Generate image"
    assert window.top_actions["new"].toolTip() == "New (Ctrl+N)"
    clean_close(window)


@pytest.mark.parametrize("text, expected", [("0.25", 0.25), ("0,80", 0.8)])
def test_strength_and_exact_64_bit_seed_reach_sampler(qtbot, tmp_path, monkeypatch, text, expected):
    window = make_window(qtbot, tmp_path, monkeypatch)
    window.add_document(Image.new("RGBA", (64, 64), "white"), "Source")
    assert isinstance(window.seed, QLineEdit)
    assert not window.strength.isEnabled()  # txt2img has no source-image denoise.
    window.mode.setCurrentIndex(window.mode.findData("img2img"))
    assert window.strength.isEnabled()
    window.strength.lineEdit().selectAll()
    QTest.keyClicks(window.strength.lineEdit(), text)
    window.seed.setText("9223372036854775807")
    captured = []
    monkeypatch.setattr(window, "start_job", captured.append)
    window.generate()
    assert captured
    request = captured[0].request
    assert request.seed == 9223372036854775807
    assert request.strength == expected
    graph = build_workflow(
        window.selected_profile(), request, {"checkpoint": "local.safetensors"}, image="source.png"
    )
    sampler = next(n for n in graph.values() if n["class_type"] == "KSampler")
    assert sampler["inputs"]["seed"] == 9223372036854775807
    assert sampler["inputs"]["denoise"] == expected
    clean_close(window)


def test_seed_zero_random_and_invalid_range(qtbot, tmp_path, monkeypatch):
    window = make_window(qtbot, tmp_path, monkeypatch)
    captured = []
    errors = []
    monkeypatch.setattr(window, "start_job", captured.append)
    monkeypatch.setattr(window, "show_error", errors.append)
    window.seed.setText("0")
    window.generate()
    assert captured[-1].request.seed == 0
    monkeypatch.setattr("paint_tes.app.secrets.randbelow", lambda _: 1234567890123456789)
    window.seed.clear()
    window.generate()
    assert captured[-1].request.seed == 1234567890123456789
    assert window.seed.text() == ""
    count = len(captured)
    window.seed.setText("9223372036854775808")
    window.generate()
    assert len(captured) == count
    assert errors and "9223372036854775807" in errors[-1]
    clean_close(window)


def test_language_setting_saved(qtbot, tmp_path, monkeypatch):
    window = make_window(qtbot, tmp_path, monkeypatch)
    dialog = SettingsDialog(window, window.settings)
    qtbot.addWidget(dialog)
    dialog.language.setCurrentIndex(dialog.language.findData("pl"))
    dialog.accept()
    path = tmp_path / "settings.json"
    dialog.settings.save(path)
    assert Settings.load(path).language == "pl"
    clean_close(window)


def test_settings_language_change_keeps_generation_controls(qtbot, tmp_path, monkeypatch):
    from dataclasses import replace

    from PySide6.QtWidgets import QDialog

    window = make_window(qtbot, tmp_path, monkeypatch)
    window.steps.setValue(9)
    window.cfg.setValue(3.25)
    window.seed.setText("424242")
    window.prompt.setPlainText("My prompt")

    class ChangeLanguage:
        def __init__(self, parent, settings):
            self.settings = replace(settings, language="pl")

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("paint_tes.app.SettingsDialog", ChangeLanguage)
    window.open_settings()
    assert window.settings.language == "pl"
    assert window.generate_button.text() == "Generuj obraz"
    assert window.reference.itemText(0) == "Brak"
    assert window.steps.value() == 9
    assert window.cfg.value() == 3.25
    assert window.seed.text() == "424242"
    assert window.prompt.toPlainText() == "My prompt"
    clean_close(window)


def test_english_ai_panel_fits_without_horizontal_scrolling(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QScrollArea

    from paint_tes.theme import STYLE

    window = make_window(qtbot, tmp_path, monkeypatch)
    window.setStyleSheet(STYLE)
    qtbot.wait(20)
    scroll = window.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0
    clean_close(window)
