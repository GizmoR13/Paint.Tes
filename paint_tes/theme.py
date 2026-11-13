from pathlib import Path

STYLE = """
QMainWindow, QDialog { background: #28211d; color: #eee0ce; }
QWidget { background-color: #28211d; color: #eee0ce; font-family: 'Noto Sans'; font-size: 13px; }
QMenuBar, QMenu, QToolBar { background: #332a24; color: #eee0ce; border: none; }
QMenuBar::item:selected, QMenu::item:selected { background: #69503a; }
QToolBar { spacing: 6px; padding: 8px; border-bottom: 1px solid #4d3d30; }
QToolButton { border: 1px solid transparent; border-radius: 5px; padding: 7px; }
QToolButton:hover, QToolButton:checked { background: #685039; border-color: #a47a50; }
QDockWidget { font-weight: bold; }
QDockWidget::title { background: #3d3027; padding: 9px; }
QLabel#brand { color: #e1b989; font-size: 24px; font-weight: 700; }
QLabel#section { color: #c4a27f; font-size: 11px; font-weight: 700; }
QLabel#muted { color: #b7a18c; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {
 background: #211b17; color: #f0e1cc; border: 1px solid #65503e; border-radius: 5px; padding: 6px;
 selection-background-color: #99734e; }
QSpinBox, QDoubleSpinBox { padding-right: 25px; min-height: 20px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
 subcontrol-origin: border; subcontrol-position: top right; width: 22px; height: 16px;
 border-left: 1px solid #826044; border-bottom: 1px solid #65503e;
 border-top-right-radius: 5px; background: #503b2b; }
QSpinBox::down-button, QDoubleSpinBox::down-button {
 subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; height: 16px;
 border-left: 1px solid #826044; border-bottom-right-radius: 5px; background: #503b2b; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #805b3c; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
 image: url("@CONTROLS@/up.svg"); width: 12px; height: 8px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
 image: url("@CONTROLS@/down.svg"); width: 12px; height: 8px; }
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {
 image: url("@CONTROLS@/up-disabled.svg"); }
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
 image: url("@CONTROLS@/down-disabled.svg"); }
QComboBox { padding-right: 27px; }
QComboBox::drop-down {
 subcontrol-origin: border; subcontrol-position: top right; width: 23px;
 border-left: 1px solid #826044; border-top-right-radius: 5px;
 border-bottom-right-radius: 5px; background: #503b2b; }
QComboBox::drop-down:hover { background: #805b3c; }
QComboBox::down-arrow { image: url("@CONTROLS@/down.svg"); width: 12px; height: 8px; }
QComboBox::down-arrow:disabled { image: url("@CONTROLS@/down-disabled.svg"); }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #d4a16b; }
QPushButton { background: #4b382a; border: 1px solid #826044; border-radius: 6px; padding: 8px 13px; }
QPushButton:hover { background: #664a33; }
QPushButton:disabled { background: #332a24; color: #7f7064; border-color: #4a3a2c; }
QPushButton#primary { background: #bf9161; color: #21170e; font-weight: bold; border-color: #dab58c; padding: 11px; }
QPushButton#primary:hover { background: #d5a875; }
QTabWidget::pane { border: 1px solid #544030; background: #1c1916; }
QTabBar::tab { background: #352a22; padding: 10px 18px; border-right: 1px solid #49372a; }
QTabBar::tab:selected { background: #65503b; border-top: 2px solid #d7ac7a; }
QStatusBar { background: #332a24; color: #b9a38d; }
QGroupBox { border: 1px solid #594331; border-radius: 6px; margin-top: 12px; padding-top: 15px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #d3b291; }
QScrollArea { border: none; background: #28211d; }
QScrollBar:vertical { background: #30261f; width: 12px; }
QScrollBar::handle:vertical { background: #755a41; min-height: 25px; border-radius: 4px; }
QProgressBar { background: #211b17; border: 1px solid #65503e; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #ac8055; }
QCheckBox { spacing: 8px; }
QSplitter::handle { background: #3c2e23; }
"""

STYLE = STYLE.replace(
    "@CONTROLS@", (Path(__file__).resolve().parents[1] / "resources" / "controls").as_posix()
)
