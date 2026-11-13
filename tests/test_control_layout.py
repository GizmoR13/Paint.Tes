import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea, QStyle, QStyleOptionSpinBox
from test_ui_update import clean_close, make_window

from paint_tes.theme import STYLE


def click_arrow(box, up=True):
    option = QStyleOptionSpinBox()
    box.initStyleOption(option)
    control = QStyle.SubControl.SC_SpinBoxUp if up else QStyle.SubControl.SC_SpinBoxDown
    rect = box.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, control, box)
    assert rect.width() >= 16 and rect.height() >= 12
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=rect.center())


@pytest.mark.parametrize(
    "name,delta",
    [
        ("brush_size", 1),
        ("width", 16),
        ("height", 16),
        ("steps", 1),
        ("cfg", 0.5),
        ("strength", 0.05),
    ],
)
def test_visible_spin_buttons_change_values(qtbot, tmp_path, monkeypatch, name, delta):
    window = make_window(qtbot, tmp_path, monkeypatch)
    window.setStyleSheet(STYLE)
    box = getattr(window, name)
    scroll = window.findChild(QScrollArea)
    if name != "brush_size":
        scroll.ensureWidgetVisible(box)
    qtbot.wait(20)
    value = box.value()
    click_arrow(box)
    assert box.value() == pytest.approx(value + delta)
    click_arrow(box, False)
    assert box.value() == pytest.approx(value)
    clean_close(window)


@pytest.mark.parametrize("language", ["en", "pl"])
@pytest.mark.parametrize("size", [(1440, 900), (1000, 680)])
def test_resolution_alignment_and_unclipped_hints(qtbot, tmp_path, monkeypatch, language, size):
    window = make_window(qtbot, tmp_path, monkeypatch, language=language)
    window.setStyleSheet(STYLE)
    window.resize(*size)
    qtbot.wait(50)

    def origin(widget):
        return widget.mapTo(window, QPoint())

    assert origin(window.width).x() == origin(window.steps).x()
    assert origin(window.width).y() == origin(window.height).y()
    assert origin(window.height).x() - origin(window.width).x() <= window.width.width() + 24
    label_center = window.resolution_label.mapTo(
        window, window.resolution_label.rect().center()
    ).y()
    field_center = window.width.mapTo(window, window.width.rect().center()).y()
    # Native form labels align to the text baseline, allowing the font's descent.
    assert abs(label_center - field_center) <= max(
        2, window.resolution_label.fontMetrics().descent()
    )
    for label in (window.ref_hint, window.strength_hint, window.job_status):
        assert label.height() >= label.heightForWidth(label.contentsRect().width())
    assert window.findChild(QScrollArea).horizontalScrollBar().maximum() == 0
    clean_close(window)


def test_txt2img_strength_can_be_edited_but_sampler_uses_full_noise(qtbot, tmp_path, monkeypatch):
    from paint_tes.workflow import build_workflow

    window = make_window(qtbot, tmp_path, monkeypatch)
    assert window.mode.currentData() == "txt2img"
    window.strength.lineEdit().selectAll()
    QTest.keyClicks(window.strength.lineEdit(), "0,35")
    captured = []
    monkeypatch.setattr(window, "start_job", captured.append)
    window.generate()
    assert captured[0].request.strength == 0.35
    graph = build_workflow(
        window.selected_profile(), captured[0].request, {"checkpoint": "local.safetensors"}
    )
    sampler = next(node for node in graph.values() if node["class_type"] == "KSampler")
    assert sampler["inputs"]["denoise"] == 1.0
    clean_close(window)
