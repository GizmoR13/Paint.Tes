from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from paint_tes.app import MainWindow
from paint_tes.config import Settings
from paint_tes.dialogs import SettingsDialog


def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PAINT_TES_DATA", str(tmp_path / "data"))
    monkeypatch.setattr("paint_tes.dialogs.list_gpus", lambda: [])
    result = MainWindow(Settings(output_dir=str(tmp_path)))
    qtbot.addWidget(result)
    result.show()
    return result


def clean_close(result):
    for i in range(result.tabs.count()):
        doc = result.tabs.widget(i).document
        doc.saved_revision = doc.revision
    result.close()


def test_tabs_reference_and_prompt_keyboard(qtbot, tmp_path, monkeypatch):
    result = window(qtbot, tmp_path, monkeypatch)
    first = result.add_document(Image.new("RGBA", (128, 128), "white"), "Reference")
    result.use_reference()
    second = result.add_document(Image.new("RGBA", (128, 128), "red"), "Editing")
    assert result.reference.currentData() == first.document.id
    result.prompt.setFocus()
    QTest.keyClicks(result.prompt, "hello brush lasso")
    assert result.prompt.toPlainText() == "hello brush lasso"
    assert result.active_tool == "hand"
    result.tabs.setCurrentWidget(first)
    assert result.tabs.count() == 2
    assert second.document.image.getpixel((0, 0)) == (255, 0, 0, 255)
    clean_close(result)


def test_rectangle_brush_undo_and_selection(qtbot, tmp_path, monkeypatch):
    result = window(qtbot, tmp_path, monkeypatch)
    canvas = result.add_document(Image.new("RGBA", (128, 128), "white"), "Canvas")
    qtbot.wait(50)
    canvas.actual_size()
    result.set_tool("rectangle")
    a = canvas.mapFromScene(10, 10)
    b = canvas.mapFromScene(60, 60)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseMove(canvas.viewport(), b)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=b)
    assert canvas.document.mask.getbbox() == (10, 10, 61, 61)
    result.set_tool("brush")
    a = canvas.mapFromScene(30, 30)
    b = canvas.mapFromScene(45, 45)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseMove(canvas.viewport(), b)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=b)
    assert canvas.document.image.getpixel((30, 30)) != (255, 255, 255, 255)
    assert canvas.document.image.getpixel((0, 0)) == (255, 255, 255, 255)
    result.undo()
    assert canvas.document.image.getpixel((30, 30)) == (255, 255, 255, 255)
    result.redo()
    assert canvas.document.image.getpixel((30, 30)) != (255, 255, 255, 255)
    clean_close(result)


def test_profile_editor_keeps_entries_on_tab_switch(qtbot, tmp_path, monkeypatch):
    result = window(qtbot, tmp_path, monkeypatch)
    dialog = SettingsDialog(result, Settings())
    qtbot.addWidget(dialog)
    dialog.add_profile()
    dialog.profile_name.setText("First")
    dialog.fields["checkpoint"].setText("/models/first.safetensors")
    dialog.add_profile()
    dialog.profile_name.setText("Second")
    dialog.profiles.setCurrentRow(0)
    assert dialog.profile_name.text() == "First"
    assert dialog.fields["checkpoint"].text() == "/models/first.safetensors"
    dialog.accept()
    assert [p.name for p in dialog.settings.profiles] == ["First", "Second"]
    clean_close(result)
