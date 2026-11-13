from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageOps, PngImagePlugin
from PySide6.QtCore import QLocale, QRegularExpression, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QKeySequence,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .canvas import Canvas
from .config import Settings, data_path
from .dialogs import DecimalSpinBox, InfoLabel, NewImageDialog, OutpaintDialog, SettingsDialog, spin
from .document import Document
from .engine import Cancelled, EngineClient
from .hardware import list_gpus
from .i18n import apply_qt_language, retranslate_widgets, set_language, tr
from .icons import icon
from .imageops import expand_canvas, load_image, paint_mask, validate_size
from .workflow import Generation


class Job(QThread):
    status = Signal(str)
    success = Signal(object, str, object)
    failure = Signal(str)

    def __init__(
        self, client, settings, profile, request, image, mask, reference, title, background=False
    ):
        super().__init__()
        self.client = client
        self.settings = settings
        self.profile = profile
        self.request = request
        self.image = image
        self.mask = mask
        self.reference = reference
        self.title = title
        self.background = background
        self.background_process = None
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        if self.background:
            if self.background_process and self.background_process.poll() is None:
                self.background_process.terminate()
        else:
            self.client.cancel()

    def run(self):
        try:
            if self.cancelled:
                raise Cancelled(tr("Anulowano."))
            if self.background:
                result = self.run_background()
                metadata = {"operation": "background-remove"}
            else:
                result = self.client.generate(
                    self.settings,
                    self.profile,
                    self.request,
                    self.image,
                    self.mask,
                    self.reference,
                    self.status.emit,
                )
                metadata = {
                    "prompt": self.request.prompt,
                    "negative_prompt": self.request.negative,
                    "seed": str(self.request.seed),
                    "steps": str(self.request.steps),
                    "cfg": str(self.request.cfg),
                    "denoise": str(
                        1.0 if self.request.mode == "txt2img" else self.request.strength
                    ),
                    "mode": self.request.mode,
                    "profile": self.profile.name,
                }
            if self.cancelled:
                raise Cancelled(tr("Anulowano."))
            self.success.emit(result, self.title, metadata)
        except Cancelled:
            self.status.emit(tr("Anulowano. Obrazy źródłowe pozostały w kartach."))
        except Exception as error:
            if self.cancelled:
                self.status.emit(tr("Anulowano."))
            else:
                self.failure.emit(str(error))

    def run_background(self):
        model = Path(self.settings.background_model)
        if not self.settings.background_model or not model.is_file():
            raise ValueError(tr("W Ustawienia → Usuwanie tła wybierz lokalny model ONNX."))
        gpus = list_gpus()
        gpu = self.settings.gpu_uuid or (gpus[0]["uuid"] if gpus else "")
        if not gpu:
            raise ValueError(tr("Nie znaleziono zgodnej V100/V100S/TITAN V."))
        temp = data_path() / "jobs"
        temp.mkdir(parents=True, exist_ok=True)
        self.status.emit(tr("Usuwanie tła z użyciem lokalnego modelu ONNX…"))
        with tempfile.TemporaryDirectory(dir=temp) as directory:
            source = Path(directory) / "source.png"
            target = Path(directory) / "result.png"
            self.image.save(source)
            env = os.environ.copy()
            env.update(CUDA_VISIBLE_DEVICES=gpu, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
            with (Path(directory) / "worker.log").open("w+") as log:
                self.background_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "paint_tes.background",
                        str(source),
                        str(target),
                        str(model),
                        "--size",
                        str(self.settings.background_size),
                        "--normalization",
                        self.settings.background_normalization,
                    ],
                    env=env,
                    cwd=Path(__file__).resolve().parents[1],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                while self.background_process.poll() is None:
                    if self.cancelled:
                        self.background_process.terminate()
                        try:
                            self.background_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.background_process.kill()
                            self.background_process.wait()
                        raise Cancelled()
                    time.sleep(0.1)
                if self.background_process.returncode:
                    log.seek(0)
                    raise RuntimeError(log.read()[-3500:])
                return load_image(target)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings.load()
        set_language(self.settings.language)
        apply_qt_language()
        self.last_seed = None
        self.client = EngineClient()
        self.job = None
        self._closing = False
        self.started = 0
        self.setWindowTitle(tr("Paint.TES • lokalne studio obrazu"))
        self.resize(1440, 900)
        self.setMinimumSize(1000, 680)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_changed)
        self.stack.addWidget(self.tabs)
        welcome = QWidget()
        wl = QVBoxLayout(welcome)
        wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("Paint.TES")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(brand)
        text = QLabel(tr("Twoje obrazy. Twoje modele. Lokalna V100."))
        text.setObjectName("muted")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(text)
        for label, slot in (
            (tr("Nowy obraz…"), self.new_image),
            (tr("Otwórz obrazy…"), self.open_images),
            (tr("Ustaw modele lokalne…"), self.open_settings),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            wl.addWidget(button)
        self.stack.addWidget(welcome)
        self.stack.setCurrentWidget(welcome)
        self.build_menus()
        self.build_tools()
        self.build_ai()
        self.status_label = QLabel(tr("Gotowy • silnik AI uruchamia się dopiero przy generowaniu"))
        self.statusBar().addWidget(self.status_label, 1)
        self.coords = QLabel("")
        self.statusBar().addPermanentWidget(self.coords)
        self.elapsed = QTimer(self)
        self.elapsed.timeout.connect(self.update_elapsed)
        self.refresh_profiles()
        self.refresh_references()

    def action(self, text, slot, shortcut=None, menu=None):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(shortcut)
        if menu:
            menu.addAction(action)
        return action

    def build_menus(self):
        file = self.menuBar().addMenu(tr("Plik"))
        self.action(tr("Nowy obraz…"), self.new_image, QKeySequence.StandardKey.New, file)
        self.action(tr("Otwórz…"), self.open_images, QKeySequence.StandardKey.Open, file)
        file.addSeparator()
        self.action(tr("Zapisz"), self.save_image, QKeySequence.StandardKey.Save, file)
        self.action(tr("Zapisz jako…"), lambda: self.save_image(save_as=True), "Ctrl+Shift+S", file)
        file.addSeparator()
        self.action(
            tr("Zamknij kartę"), lambda: self.close_tab(self.tabs.currentIndex()), "Ctrl+W", file
        )
        self.action(tr("Zakończ"), self.close, "Ctrl+Q", file)
        edit = self.menuBar().addMenu(tr("Edycja"))
        self.undo_action = self.action(tr("Cofnij"), self.undo, QKeySequence.StandardKey.Undo, edit)
        self.redo_action = self.action(tr("Ponów"), self.redo, QKeySequence.StandardKey.Redo, edit)
        edit.addSeparator()
        self.action(tr("Kopiuj obraz"), self.copy_image, QKeySequence.StandardKey.Copy, edit)
        self.action(
            tr("Wklej jako nową kartę"), self.paste_image, QKeySequence.StandardKey.Paste, edit
        )
        self.action(tr("Wyczyść zaznaczenie"), self.delete_selection, "Delete", edit)
        self.action(tr("Ustawienia…"), self.open_settings, "Ctrl+,", edit)
        selection = self.menuBar().addMenu(tr("Zaznaczenie"))
        self.action(tr("Zaznacz wszystko"), self.select_all, "Ctrl+A", selection)
        self.action(tr("Usuń zaznaczenie"), self.clear_selection, "Ctrl+D", selection)
        self.action(tr("Odwróć zaznaczenie"), self.invert_selection, "Ctrl+I", selection)
        self.action(tr("Zmiękcz krawędzie…"), self.feather_selection, None, selection)
        self.action(tr("Przytnij do zaznaczenia"), self.crop_selection, None, selection)
        image = self.menuBar().addMenu(tr("Obraz"))
        self.action(tr("Zmień rozmiar…"), self.resize_image, None, image)
        self.action(
            tr("Obróć w prawo"),
            lambda: self.transform_image(lambda im: im.transpose(Image.Transpose.ROTATE_270)),
            None,
            image,
        )
        self.action(tr("Odbij poziomo"), lambda: self.transform_image(ImageOps.mirror), None, image)
        self.action(tr("Użyj jako referencji"), self.use_reference, None, image)
        ai = self.menuBar().addMenu("AI")
        self.action(tr("Generuj"), self.generate, "Ctrl+Return", ai)
        self.action(tr("Usuń tło"), self.remove_background, None, ai)
        self.action(tr("Zwolnij pamięć silnika"), self.release_engine, None, ai)
        view = self.menuBar().addMenu(tr("Widok"))
        self.action(tr("Dopasuj do okna"), self.fit_canvas, "Ctrl+0", view)
        self.action(tr("Rozmiar rzeczywisty"), self.actual_size, "Ctrl+1", view)
        help_menu = self.menuBar().addMenu(tr("Pomoc"))
        self.action(tr("Instrukcja"), self.help, None, help_menu)
        self.action(
            tr("O Paint.TES"),
            lambda: QMessageBox.information(
                self,
                "Paint.TES",
                tr(
                    "Paint.TES 0.2.1\nNatywny edytor dla Ubuntu i kart NVIDIA Volta.\nLokalne modele • prywatne repozytorium\nGPL-3.0-or-later. Silnik: ComfyUI (GPL-3.0)."
                ),
            ),
            None,
            help_menu,
        )

    def build_tools(self):
        top = QToolBar(tr("Plik i widok"))
        self.top_toolbar = top
        top.setMovable(False)
        top.setIconSize(QSize(24, 24))
        top.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        top.setFixedHeight(56)
        self.addToolBar(top)
        self.top_actions = {}
        for key, label, slot, shortcut in (
            ("new", "Nowy", self.new_image, "Ctrl+N"),
            ("open", "Otwórz", self.open_images, "Ctrl+O"),
            ("save", "Zapisz", self.save_image, "Ctrl+S"),
            ("undo", "Cofnij", self.undo, "Ctrl+Z"),
            ("redo", "Ponów", self.redo, "Ctrl+Shift+Z"),
            ("fit", "Dopasuj do okna", self.fit_canvas, "Ctrl+0"),
            ("actual", "Rozmiar rzeczywisty", self.actual_size, "Ctrl+1"),
            ("settings", "Ustawienia", self.open_settings, "Ctrl+,"),
        ):
            action = self.action(tr(label), slot)
            action.setIcon(icon(key))
            action.setToolTip(tr(label) + " (" + shortcut + ")")
            top.addAction(action)
            self.top_actions[key] = action
        top.addSeparator()
        self.brush_size = spin(16, 1, 500, 1)
        self.brush_size.setPrefix(tr("Pędzel: "))
        self.brush_size.setSuffix(" px")
        top.addWidget(self.brush_size)
        self.color_button = QToolButton()
        self.color_button.setIcon(icon("color"))
        self.color_button.setIconSize(QSize(24, 24))
        self.color_button.setToolTip(tr("Kolor pędzla"))
        self.color_button.setAccessibleName(tr("Kolor pędzla"))
        self.color_button.clicked.connect(self.choose_color)
        top.addWidget(self.color_button)
        self.brush_color = (97, 59, 31, 255)
        self.brush_size.valueChanged.connect(self.update_brush)
        tools = QToolBar(tr("Narzędzia"))
        self.tools_toolbar = tools
        tools.setMovable(False)
        tools.setIconSize(QSize(24, 24))
        tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tools.setFixedWidth(58)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tools)
        self.tool_group = QActionGroup(self)
        self.tool_actions = {}
        for key, label, shortcut in (
            ("hand", "Przesuń", "H"),
            ("rectangle", "Prostokąt", "S"),
            ("ellipse", "Elipsa", "E"),
            ("lasso", "Lasso", "L"),
            ("polygon", "Wielokąt", "P"),
            ("brush", "Pędzel", "B"),
            ("eraser", "Gumka", "R"),
        ):
            action = QAction(tr(label), self)
            action.setIcon(icon(key))
            action.setCheckable(True)
            action.setToolTip(tr(label) + " (" + shortcut + ")")
            action.triggered.connect(lambda checked=False, k=key: self.set_tool(k))
            self.tool_group.addAction(action)
            tools.addAction(action)
            self.tool_actions[key] = action
        self.tool_actions["hand"].setChecked(True)
        self.active_tool = "hand"

    def build_ai(self):
        dock = QDockWidget(tr("STUDIO AI"), self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setMinimumWidth(310)
        dock.setMaximumWidth(430)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        brand = QLabel("Paint.TES")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        label = QLabel(tr("KAWA • PIKSELE • VOLTA"))
        label.setObjectName("section")
        layout.addWidget(label)
        layout.addSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.model = QComboBox()
        self.model.setProperty("userContent", True)
        self.model.currentIndexChanged.connect(self.model_changed)
        self.mode = QComboBox()
        for key, label in (
            ("txt2img", tr("Text to image")),
            ("img2img", tr("Image to image")),
            ("inpaint", tr("Inpaint • zaznaczenie")),
            ("outpaint", tr("Outpaint • nowe marginesy")),
        ):
            self.mode.addItem(label, key)
        self.mode.currentIndexChanged.connect(self.update_hint)
        form.addRow(tr("Model lokalny"), self.model)
        form.addRow(tr("Tryb"), self.mode)
        layout.addLayout(form)
        manage = QPushButton(tr("Modele i ustawienia…"))
        manage.clicked.connect(self.open_settings)
        layout.addWidget(manage)
        label = QLabel("PROMPT")
        label.setObjectName("section")
        layout.addWidget(label)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText(tr("Co chcesz zobaczyć lub zmienić?"))
        self.prompt.setMinimumHeight(100)
        layout.addWidget(self.prompt)
        self.negative = QPlainTextEdit()
        self.negative.setPlaceholderText(tr("Negatywny prompt (opcjonalnie)"))
        self.negative.setMaximumHeight(65)
        layout.addWidget(self.negative)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.reference = QComboBox()
        self.reference.setProperty("userContent", True)
        form.addRow(tr("Karta referencji"), self.reference)
        self.reference.currentIndexChanged.connect(self.update_hint)
        self.ref_hint = InfoLabel()
        self.ref_hint.setWordWrap(True)
        self.ref_hint.setObjectName("muted")
        form.addRow(self.ref_hint)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.width = spin(512)
        self.height = spin(512)
        for dimension in (self.width, self.height):
            dimension.setMinimumWidth(0)
            dimension.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        row.addWidget(self.width, 1)
        row.addWidget(QLabel("×"))
        row.addWidget(self.height, 1)
        self.resolution_label = QLabel(tr("Nowy obraz (px)"))
        self.resolution_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        resolution_fields = QWidget()
        resolution_fields.setLayout(row)
        form.addRow(self.resolution_label, resolution_fields)
        self.steps = spin(25, 1, 150, 1)
        self.cfg = DecimalSpinBox()
        self.cfg.setRange(0, 30)
        self.cfg.setSingleStep(0.5)
        self.cfg.setValue(7)
        self.strength = DecimalSpinBox()
        self.strength.setRange(0.01, 1)
        self.strength.setSingleStep(0.05)
        self.strength.setValue(0.65)
        self.strength.setLocale(QLocale.c())
        self.strength.setDecimals(2)
        self.strength.setKeyboardTracking(False)
        self.strength.setToolTip(
            tr(
                "0.01 = mała zmiana; 1.00 = pełny poziom szumu. Przy niewielu krokach efekty są skokowe."
            )
        )
        self.seed = QLineEdit()
        self.seed.setMaxLength(19)
        self.seed.setValidator(
            QRegularExpressionValidator(QRegularExpression("[0-9]{0,19}"), self.seed)
        )
        self.seed.setPlaceholderText(tr("Losowy (puste pole)"))
        self.seed.setToolTip(
            tr(
                "Wpisz liczbę 0–9223372036854775807. Puste pole losuje nowy seed dla każdego zadania."
            )
        )
        self.sampler = QComboBox()
        self.sampler.addItems(["euler", "dpmpp_2m", "heun", "uni_pc"])
        self.scheduler = QComboBox()
        self.scheduler.addItems(["normal", "simple", "karras", "sgm_uniform"])
        for label, widget in (
            (tr("Kroki"), self.steps),
            ("CFG", self.cfg),
            (tr("Siła zmiany"), self.strength),
            (tr("Seed"), self.seed),
            (tr("Sampler"), self.sampler),
            (tr("Scheduler"), self.scheduler),
        ):
            form.addRow(label, widget)
        self.strength_hint = InfoLabel(
            tr(
                "Siłę można ustawić w dowolnym trybie. Jest używana w image-to-image, inpaint i outpaint; text-to-image ją pomija (szum 1.0)."
            )
        )
        self.strength_hint.setWordWrap(True)
        self.strength_hint.setObjectName("muted")
        form.addRow(self.strength_hint)
        self.last_seed_label = QLabel(tr("Ostatni seed: —"))
        self.last_seed_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.reuse_seed_button = QPushButton(tr("Użyj ostatniego seeda"))
        self.reuse_seed_button.setEnabled(False)
        self.reuse_seed_button.clicked.connect(lambda: self.seed.setText(str(self.last_seed)))
        form.addRow(self.last_seed_label)
        form.addRow(self.reuse_seed_button)
        layout.addLayout(form)
        self.generate_button = QPushButton(tr("Generuj obraz"))
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.generate)
        layout.addWidget(self.generate_button)
        self.bg_button = QPushButton(tr("Usuń tło → przezroczystość"))
        self.bg_button.clicked.connect(self.remove_background)
        layout.addWidget(self.bg_button)
        self.cancel_button = QPushButton(tr("Anuluj zadanie"))
        self.cancel_button.clicked.connect(self.cancel_job)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.job_status = InfoLabel(
            tr("Wyniki powstają w nowych kartach. Zapisujesz je samodzielnie.")
        )
        self.job_status.setWordWrap(True)
        self.job_status.setObjectName("muted")
        layout.addWidget(self.job_status)
        layout.addStretch()
        for combo in body.findChildren(QComboBox):
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(8)
            combo.setMinimumWidth(0)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        scroll.setWidget(body)
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        footer = QVBoxLayout()
        footer.setContentsMargins(10, 8, 10, 8)
        for widget in (
            self.generate_button,
            self.bg_button,
            self.cancel_button,
            self.progress,
            self.job_status,
        ):
            layout.removeWidget(widget)
            footer.addWidget(widget)
        outer.addLayout(footer)
        dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def canvas(self):
        return self.tabs.currentWidget() if isinstance(self.tabs.currentWidget(), Canvas) else None

    def add_document(self, image, title=tr("Nowy obraz"), path=None, clean=False, metadata=None):
        validate_size(*image.size)
        document = Document(image.convert("RGBA"), title, path=path, limit=self.settings.undo_limit)
        if clean:
            document.saved_revision = 0
        document.metadata = metadata or {}
        canvas = Canvas(document)
        canvas.setTool(self.active_tool)
        canvas.color = self.brush_color
        canvas.brush_size = self.brush_size.value()
        canvas.changed.connect(self.document_changed)
        canvas.tool_requested.connect(self.set_tool)
        canvas.position_changed.connect(self.coords.setText)
        index = self.tabs.addTab(canvas, title)
        self.tabs.setCurrentIndex(index)
        self.stack.setCurrentWidget(self.tabs)
        QTimer.singleShot(0, canvas.fit)
        self.refresh_references()
        self.document_changed()
        return canvas

    def document_changed(self):
        for i in range(self.tabs.count()):
            document = self.tabs.widget(i).document
            self.tabs.setTabText(i, document.title + (" •" if document.dirty else ""))
        canvas = self.canvas()
        self.undo_action.setEnabled(bool(canvas and canvas.document.history))
        self.redo_action.setEnabled(bool(canvas and canvas.document.redo_history))
        if canvas:
            im = canvas.document.image
            self.setWindowTitle(f"{canvas.document.title} — Paint.TES")
            if not self.job:
                self.status_label.setText(
                    f"{im.width} × {im.height} px • RGBA • {self.tool_actions[self.active_tool].text()}"
                )

    def current_changed(self, index):
        self.refresh_references()
        self.document_changed()

    def refresh_references(self):
        if not hasattr(self, "reference"):
            return
        selected = getattr(self, "pending_reference", None) or self.reference.currentData()
        self.reference.blockSignals(True)
        self.reference.clear()
        self.reference.addItem(tr("Brak"), "")
        current = self.canvas()
        for i in range(self.tabs.count()):
            document = self.tabs.widget(i).document
            if current is None or document.id != current.document.id:
                self.reference.addItem(document.title, document.id)
        self.reference.setCurrentIndex(max(0, self.reference.findData(selected)))
        self.reference.blockSignals(False)
        if self.reference.findData(selected) > 0:
            self.pending_reference = None
        self.update_hint()

    def refresh_profiles(self):
        current = self.model.currentData() or self.settings.active_profile
        self.model.blockSignals(True)
        self.model.clear()
        if not self.settings.profiles:
            self.model.addItem(tr("Dodaj lokalny profil w ustawieniach"), "")
        for profile in self.settings.profiles:
            self.model.addItem(profile.name, profile.id)
        self.model.setCurrentIndex(max(0, self.model.findData(current)))
        self.model.blockSignals(False)
        self.model_changed()

    def selected_profile(self):
        return next((p for p in self.settings.profiles if p.id == self.model.currentData()), None)

    def model_changed(self):
        profile = self.selected_profile()
        if profile:
            self.settings.active_profile = profile.id
            profile_key = (profile.id, profile.family)
            if profile.family in ("qwen21", "moss") and profile_key != getattr(
                self, "_last_profile_key", None
            ):
                self.cfg.setValue(4)
                self.steps.setValue(20)
                self.scheduler.setCurrentText("simple")
            self._last_profile_key = profile_key
            self.update_hint()

    def update_hint(self):
        if not hasattr(self, "ref_hint"):
            return
        profile = self.selected_profile()
        if profile and profile.family == "qwen21":
            text = tr(
                "Inna karta jest niezależną referencją Qwen. Dla edycji źródłem jest aktywna karta."
            )
        else:
            text = tr(
                "Dla SD/SDXL/MOSS karta referencji może być źródłem image-to-image. Niezależne referencje są dostępne w Qwen 2.1."
            )
        self.ref_hint.setText(text)
        self.strength.setEnabled(True)

    def set_tool(self, tool):
        self.active_tool = tool
        self.tool_actions[tool].setChecked(True)
        for i in range(self.tabs.count()):
            self.tabs.widget(i).setTool(tool)
        self.document_changed()

    def update_brush(self):
        for i in range(self.tabs.count()):
            canvas = self.tabs.widget(i)
            canvas.brush_size = self.brush_size.value()
            canvas.color = self.brush_color

    def choose_color(self):
        color = QColorDialog.getColor(
            QColor(*self.brush_color),
            self,
            tr("Kolor pędzla"),
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            self.brush_color = color.getRgb()
            self.update_brush()

    def new_image(self):
        dialog = NewImageDialog(self, self.prompt.toPlainText())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            width, height = dialog.width.value(), dialog.height.value()
            validate_size(width, height)
            if dialog.generate.isChecked() and (width % 16 or height % 16):
                raise ValueError(tr("Wymiary generacji muszą być wielokrotnością 16 px."))
            color = [(255, 255, 255, 255), (0, 0, 0, 0), (117, 82, 55, 255)][
                dialog.background.currentIndex()
            ]
            self.add_document(
                Image.new("RGBA", (width, height), color),
                dialog.name.text().strip() or tr("Nowy obraz"),
            )
            self.width.setValue(width)
            self.height.setValue(height)
            if dialog.generate.isChecked():
                selected = self.model.findData(dialog.model.currentData())
                if selected >= 0:
                    self.model.setCurrentIndex(selected)
                self.steps.setValue(dialog.steps.value())
                self.cfg.setValue(dialog.cfg.value())
                self.seed.setText(dialog.seed.text())
                self.prompt.setPlainText(dialog.prompt.toPlainText())
                self.mode.setCurrentIndex(0)
                self.generate()
        except Exception as error:
            self.show_error(str(error))

    def open_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Otwórz obrazy"),
            self.settings.output_dir,
            tr("Obrazy (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"),
        )
        for name in paths:
            try:
                self.add_document(load_image(name), Path(name).name, Path(name), clean=True)
            except Exception as error:
                self.show_error(f"{name}\n{error}")

    def save_image(self, checked=False, save_as=False, canvas=None):
        canvas = canvas or self.canvas()
        if not canvas:
            return False
        document = canvas.document
        path = document.path
        if save_as or path is None:
            initial = (
                str(path)
                if path
                else str(
                    Path(self.settings.output_dir) / (document.title.replace("/", "-") + ".png")
                )
            )
            name, kind = QFileDialog.getSaveFileName(
                self, tr("Zapisz obraz"), initial, "PNG (*.png);;WebP (*.webp);;JPEG (*.jpg)"
            )
            if not name:
                return False
            path = Path(name)
            if not path.suffix:
                path = path.with_suffix(
                    ".png" if "PNG" in kind else ".webp" if "WebP" in kind else ".jpg"
                )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            image = document.image
            if path.suffix.lower() in (".jpg", ".jpeg"):
                rgb = Image.new("RGB", image.size, "white")
                rgb.paste(image, mask=image.getchannel("A"))
                rgb.save(path, quality=95)
            elif path.suffix.lower() == ".png":
                info = PngImagePlugin.PngInfo()
                for key, value in getattr(document, "metadata", {}).items():
                    info.add_text(key, str(value))
                image.save(path, pnginfo=info)
            else:
                image.save(path)
            document.path = path
            document.title = path.name
            document.saved_revision = document.revision
            self.document_changed()
            self.status_label.setText(tr("Zapisano: {0}").format(path))
            return True
        except Exception as error:
            self.show_error(str(error))
            return False

    def close_tab(self, index):
        if index < 0:
            return True
        canvas = self.tabs.widget(index)
        if canvas.document.dirty:
            answer = QMessageBox.question(
                self,
                tr("Niezapisany obraz"),
                tr("Zapisać zmiany w „{0}”?").format(canvas.document.title),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            if answer == QMessageBox.StandardButton.Save and not self.save_image(canvas=canvas):
                return False
        self.tabs.removeTab(index)
        canvas.deleteLater()
        self.refresh_references()
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(1)
        return True

    def undo(self):
        if self.canvas():
            self.canvas().document.undo()
            self.canvas().refresh()

    def redo(self):
        if self.canvas():
            self.canvas().document.redo()
            self.canvas().refresh()

    def fit_canvas(self):
        if self.canvas():
            self.canvas().fit()

    def actual_size(self):
        if self.canvas():
            self.canvas().actual_size()

    def select_all(self):
        if self.canvas():
            self.canvas().document.mask = Image.new("L", self.canvas().document.image.size, 255)
            self.canvas().refresh()

    def clear_selection(self):
        if self.canvas():
            self.canvas().document.mask = None
            self.canvas().refresh()

    def invert_selection(self):
        if self.canvas():
            doc = self.canvas().document
            doc.mask = (
                ImageOps.invert(doc.mask)
                if doc.mask is not None
                else Image.new("L", doc.image.size, 255)
            )
            self.canvas().refresh()

    def feather_selection(self):
        if not self.canvas() or not self.canvas().document.mask:
            return
        radius, ok = QInputDialog.getInt(
            self, tr("Zmiękczenie maski"), tr("Promień (px)"), 8, 0, 256
        )
        if ok:
            from PIL import ImageFilter

            doc = self.canvas().document
            doc.mask = doc.mask.filter(ImageFilter.GaussianBlur(radius))
            self.canvas().refresh()

    def delete_selection(self):
        if self.canvas() and self.canvas().document.mask:
            doc = self.canvas().document
            doc.apply(paint_mask(doc.image, doc.mask))
            self.canvas().refresh()

    def crop_selection(self):
        if self.canvas() and self.canvas().document.mask and self.canvas().document.mask.getbbox():
            doc = self.canvas().document
            box = doc.mask.getbbox()
            image = Image.composite(doc.image, Image.new("RGBA", doc.image.size), doc.mask).crop(
                box
            )
            doc.apply(image)
            doc.mask = None
            self.canvas().refresh()
            self.canvas().fit()

    def transform_image(self, fn):
        if self.canvas():
            doc = self.canvas().document
            doc.apply(fn(doc.image))
            doc.mask = None
            self.canvas().refresh()

    def resize_image(self):
        if not self.canvas():
            return
        doc = self.canvas().document
        value, ok = QInputDialog.getText(
            self,
            tr("Rozmiar obrazu"),
            tr("Szerokość × wysokość (np. 1024x768)"),
            text=f"{doc.image.width}x{doc.image.height}",
        )
        if ok:
            try:
                width, height = map(int, value.lower().replace("×", "x").split("x"))
                validate_size(width, height)
                doc.apply(doc.image.resize((width, height), Image.Resampling.LANCZOS))
                doc.mask = None
                self.canvas().refresh()
                self.canvas().fit()
            except Exception as error:
                self.show_error(str(error))

    def copy_image(self):
        if self.canvas():
            from PIL.ImageQt import ImageQt

            doc = self.canvas().document
            image = doc.image
            if doc.mask and doc.mask.getbbox():
                image = Image.composite(image, Image.new("RGBA", image.size), doc.mask).crop(
                    doc.mask.getbbox()
                )
            QApplication.clipboard().setImage(ImageQt(image).copy())

    def paste_image(self):
        image = QApplication.clipboard().image()
        if not image.isNull():
            from PIL.ImageQt import fromqimage

            self.add_document(fromqimage(image), tr("Ze schowka"))

    def use_reference(self):
        if not self.canvas():
            return
        ident = self.canvas().document.id
        self.status_label.setText(
            tr("Wybierz inną kartę, a następnie tę kartę w polu Karta referencji.")
        )
        self.pending_reference = ident

    def open_settings(self):
        if self.job:
            self.show_error(
                tr("Poczekaj na zakończenie albo anuluj zadanie przed zmianą ustawień.")
            )
            return
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                dialog.settings.save()
                self.settings = dialog.settings
                set_language(self.settings.language)
                apply_qt_language()
                retranslate_widgets(self)
                for i in range(self.tabs.count()):
                    self.tabs.widget(i).document.limit = self.settings.undo_limit
                self.refresh_profiles()
                self.refresh_references()
                self.status_label.setText(tr("Ustawienia zapisane."))
            except Exception as error:
                self.show_error(str(error))

    def generate(self):
        if self.job:
            return
        profile = self.selected_profile()
        if not profile:
            self.show_error(tr("Dodaj profil lokalnego modelu w ustawieniach."))
            return
        try:
            profile.validate()
            mode = self.mode.currentData()
            canvas = self.canvas()
            image = mask = reference = None
            reference_id = self.reference.currentData()
            refdoc = next(
                (
                    self.tabs.widget(i).document
                    for i in range(self.tabs.count())
                    if self.tabs.widget(i).document.id == reference_id
                ),
                None,
            )
            if mode != "txt2img":
                if not canvas:
                    raise ValueError(tr("Otwórz obraz albo utwórz nową kartę."))
                doc = canvas.document
                image = doc.image.copy()
                if mode == "img2img" and refdoc and profile.family != "qwen21":
                    image = refdoc.image.copy()
                    refdoc = None
                if mode == "inpaint":
                    if doc.mask is None or not doc.mask.getbbox():
                        raise ValueError(tr("Zaznacz obszar lassem, prostokątem lub elipsą."))
                    mask = doc.mask.copy()
                elif mode == "outpaint":
                    dialog = OutpaintDialog(self)
                    if dialog.exec() != QDialog.DialogCode.Accepted:
                        return
                    values = [dialog.margins[k].value() for k in ("left", "top", "right", "bottom")]
                    if not any(values):
                        raise ValueError(tr("Dodaj co najmniej jeden margines."))
                    image, mask = expand_canvas(image, *values)
            if refdoc:
                if profile.family != "qwen21":
                    raise ValueError(
                        tr(
                            "Niezależna referencja działa z Qwen 2.1. Dla tego modelu wybierz image-to-image lub ustaw referencję na Brak."
                        )
                    )
                reference = refdoc.image.copy()
            seed_text = self.seed.text().strip()
            try:
                seed = int(seed_text) if seed_text else secrets.randbelow(2**63)
                if not 0 <= seed < 2**63:
                    raise ValueError()
            except ValueError:
                raise ValueError(
                    tr("Seed musi być liczbą całkowitą od 0 do 9223372036854775807.")
                ) from None
            self.strength.interpretText()
            width, height = (
                image.size if image is not None else (self.width.value(), self.height.value())
            )
            request = Generation(
                mode,
                self.prompt.toPlainText(),
                self.negative.toPlainText(),
                width,
                height,
                self.steps.value(),
                self.cfg.value(),
                seed,
                self.strength.value(),
                self.sampler.currentText(),
                self.scheduler.currentText(),
            )
            request.validate()
            if mode == "txt2img" and (width % 16 or height % 16):
                raise ValueError(tr("Wymiary generacji muszą być wielokrotnością 16 px."))
            title = f"{dict(txt2img=tr('Generacja'), img2img='Img2img', inpaint='Inpaint', outpaint='Outpaint')[mode]} • {seed}"
            self.start_job(
                Job(self.client, self.settings, profile, request, image, mask, reference, title)
            )
        except Exception as error:
            self.show_error(str(error))

    def remove_background(self):
        if self.job:
            return
        if not self.canvas():
            self.show_error(tr("Otwórz obraz do usunięcia tła."))
            return
        self.start_job(
            Job(
                self.client,
                self.settings,
                None,
                None,
                self.canvas().document.image.copy(),
                None,
                None,
                tr("Bez tła • ") + self.canvas().document.title,
                background=True,
            )
        )

    def start_job(self, job):
        self.client.cancel_event.clear()
        self.job = job
        if job.request is not None:
            self.last_seed = job.request.seed
            self.last_seed_label.setText(tr("Ostatni seed: {0}").format(self.last_seed))
            self.reuse_seed_button.setEnabled(True)
        self.started = time.monotonic()
        self.generate_button.setEnabled(False)
        self.bg_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        job.status.connect(self.set_job_status)
        job.success.connect(self.job_success)
        job.failure.connect(self.job_error)
        job.finished.connect(self.job_finished)
        self.set_job_status(tr("Przygotowanie lokalnego zadania…"))
        self.elapsed.start(1000)
        job.start()

    def set_job_status(self, text):
        self.job_status.setText(text)
        self.status_label.setText(text)

    def update_elapsed(self):
        self.status_label.setText(
            f"{self.job_status.text()} • {int(time.monotonic() - self.started)} s"
        )

    def job_success(self, image, title, metadata):
        self.add_document(image, title, metadata=metadata)
        self.set_job_status(tr("Gotowe. Wynik w nowej karcie — zapisz, aby zachować obraz."))

    def job_error(self, message):
        self.set_job_status(tr("Zadanie zakończone błędem. Obrazy źródłowe pozostały bez zmian."))
        self.show_error(message)

    def job_finished(self):
        job = self.job
        self.job = None
        self.generate_button.setEnabled(True)
        self.bg_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        self.elapsed.stop()
        if job:
            job.deleteLater()
        if self._closing:
            QTimer.singleShot(0, self.close)

    def cancel_job(self):
        if self.job:
            self.job.cancel()
            self.cancel_button.setEnabled(False)
            self.set_job_status(tr("Anulowanie…"))

    def release_engine(self):
        if self.job:
            self.show_error(tr("Najpierw anuluj bieżące zadanie."))
            return
        self.client.stop()
        self.status_label.setText(tr("Pamięć silnika Paint.TES zwolniona."))

    def show_error(self, message):
        QMessageBox.warning(self, "Paint.TES", message)

    def help(self):
        filename = "INSTRUKCJA.md" if self.settings.language == "pl" else "USER_GUIDE.md"
        path = Path(__file__).resolve().parents[1] / "docs" / filename
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event):
        if self.job:
            self._closing = True
            self.cancel_job()
            event.ignore()
            return
        for i in reversed(range(self.tabs.count())):
            if not self.close_tab(i):
                self._closing = False
                event.ignore()
                return
        self.client.stop()
        try:
            self.settings.save()
        except OSError:
            pass
        event.accept()
