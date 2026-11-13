from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import QLocale, QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .config import FAMILIES, ModelProfile, Settings, data_path, scan_models
from .hardware import list_gpus
from .i18n import tr


class DecimalSpinBox(QDoubleSpinBox):
    """Accept both decimal separators, independent of UI or system language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale.c())

    def validate(self, text, position):
        state, _, _ = super().validate(text.replace(",", "."), position)
        return state, text, position

    def valueFromText(self, text):
        return super().valueFromText(text.replace(",", "."))


def spin(value, low=16, high=8192, step=16):
    box = QSpinBox()
    box.setRange(low, high)
    box.setSingleStep(step)
    box.setValue(value)
    return box


def file_field(parent, value="", directory=False, pattern=tr("Wagi (*.safetensors)")):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    edit = QLineEdit(value)
    edit.setPlaceholderText(
        tr("Wybierz lokalny plik…") if not directory else tr("Wybierz katalog…")
    )
    button = QPushButton("…")
    button.setFixedWidth(35)

    def choose():
        start = edit.text() or str(Path.home())
        chosen = (
            QFileDialog.getExistingDirectory(parent, tr("Wybierz katalog"), start)
            if directory
            else QFileDialog.getOpenFileName(parent, tr("Wybierz lokalny model"), start, pattern)[0]
        )
        if chosen:
            edit.setText(chosen)

    button.clicked.connect(choose)
    layout.addWidget(edit)
    layout.addWidget(button)
    return widget, edit


class NewImageDialog(QDialog):
    def __init__(self, parent, prompt=""):
        super().__init__(parent)
        self.setWindowTitle(tr("Nowy obraz • Paint.TES"))
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(tr("Nowy obraz"))
        self.width = spin(512)
        self.height = spin(512)
        sizes = QHBoxLayout()
        sizes.addWidget(self.width)
        sizes.addWidget(QLabel("×"))
        sizes.addWidget(self.height)
        self.background = QComboBox()
        self.background.addItems([tr("Białe"), tr("Przezroczyste"), tr("Kawowe")])
        form.addRow(tr("Nazwa"), self.name)
        form.addRow(tr("Rozmiar (px)"), sizes)
        form.addRow(tr("Tło"), self.background)
        self.model = QComboBox()
        for profile in parent.settings.profiles:
            self.model.addItem(profile.name, profile.id)
        self.model.setCurrentIndex(max(0, self.model.findData(parent.model.currentData())))
        self.steps = spin(parent.steps.value(), 1, 150, 1)
        self.cfg = DecimalSpinBox()
        self.cfg.setRange(0, 30)
        self.cfg.setValue(parent.cfg.value())
        self.seed = QLineEdit(parent.seed.text())
        self.seed.setMaxLength(19)
        self.seed.setValidator(
            QRegularExpressionValidator(QRegularExpression("[0-9]{0,19}"), self.seed)
        )
        self.seed.setPlaceholderText(tr("Losowy, jeśli puste"))
        form.addRow(tr("Model lokalny"), self.model)
        form.addRow(tr("Kroki"), self.steps)
        form.addRow("CFG", self.cfg)
        form.addRow(tr("Seed"), self.seed)
        layout.addLayout(form)
        self.generate = QCheckBox(tr("Wygeneruj z promptu po utworzeniu"))
        self.prompt = QPlainTextEdit(prompt)
        self.prompt.setPlaceholderText(
            tr("Opisz obraz. Model i parametry generowania są w panelu AI.")
        )
        layout.addWidget(self.generate)
        layout.addWidget(self.prompt)
        info = QLabel(
            tr(
                "Generacja używa wybranego lokalnego profilu. Rozmiar generacji: wielokrotność 16 px."
            )
        )
        info.setWordWrap(True)
        info.setObjectName("muted")
        layout.addWidget(info)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class OutpaintDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Outpaint • rozszerz płótno"))
        layout = QFormLayout(self)
        self.margins = {}
        for key, label in (
            ("left", tr("Lewo")),
            ("top", tr("Góra")),
            ("right", tr("Prawo")),
            ("bottom", tr("Dół")),
        ):
            self.margins[key] = spin(128, 0, 4096, 16)
            layout.addRow(label + " (px)", self.margins[key])
        text = QLabel(tr("Oryginalne piksele zostaną zachowane. Generowane będą nowe marginesy."))
        text.setWordWrap(True)
        layout.addRow(text)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = copy.deepcopy(settings)
        self.profile_index = -1
        self.setWindowTitle(tr("Ustawienia • Paint.TES"))
        self.resize(860, 680)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        general = QWidget()
        form = QFormLayout(general)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("Polski", "pl")
        self.language.setCurrentIndex(max(0, self.language.findData(settings.language)))
        self.language.setToolTip(tr("Zmień język bez ponownego uruchamiania."))
        form.addRow(tr("Język"), self.language)
        self.roots = QPlainTextEdit("\n".join(settings.model_roots))
        self.roots.setPlaceholderText(tr("Jeden lokalny katalog modeli w wierszu"))
        self.roots.setMaximumHeight(100)
        add_root = QPushButton(tr("Dodaj katalog…"))

        def add_folder():
            folder = QFileDialog.getExistingDirectory(self, tr("Katalog modeli"))
            if folder:
                self.roots.appendPlainText(folder)

        add_root.clicked.connect(add_folder)
        form.addRow(tr("Katalogi modeli"), self.roots)
        form.addRow("", add_root)
        outwidget, self.output = file_field(self, settings.output_dir, directory=True)
        form.addRow(tr("Domyślny zapis obrazów"), outwidget)
        self.gpu = QComboBox()
        self.gpu.addItem(tr("Automatycznie: zgodna karta z największą wolną pamięcią"), "")
        for gpu in list_gpus():
            self.gpu.addItem(
                tr("{0} · {1} MiB wolne · {2}").format(gpu["name"], gpu["free"], gpu["uuid"]),
                gpu["uuid"],
            )
        index = self.gpu.findData(settings.gpu_uuid)
        if index >= 0:
            self.gpu.setCurrentIndex(index)
        form.addRow(tr("Karta AI"), self.gpu)
        self.precision = QComboBox()
        self.precision.addItem(tr("Bezpieczny FP32 • wszystkie rodziny"), "safe")
        self.precision.addItem(tr("FP16 • tylko SD/SDXL"), "fp16")
        self.precision.setCurrentIndex(max(0, self.precision.findData(settings.precision)))
        form.addRow(tr("Precyzja"), self.precision)
        self.offload = QComboBox()
        self.offload.addItem(tr("Oszczędzaj VRAM (offload do RAM)"), "lowvram")
        self.offload.addItem(tr("Normalne wykorzystanie VRAM"), "normalvram")
        self.offload.setCurrentIndex(max(0, self.offload.findData(settings.offload)))
        form.addRow(tr("Pamięć"), self.offload)
        self.undo = spin(settings.undo_limit, 1, 50, 1)
        form.addRow(tr("Liczba kroków cofania (do 256 MiB na kartę)"), self.undo)
        log = QLabel(str(data_path() / "engine" / "engine.log"))
        log.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(tr("Dziennik silnika"), log)
        hint = QLabel(
            tr(
                "Silnik ładuje wyłącznie lokalne wagi. Nie pobiera modeli. Duże Qwen/MOSS mogą wymagać więcej RAM niż jest dostępne; zacznij od małego rozmiaru."
            )
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        form.addRow(hint)
        tabs.addTab(general, tr("Ogólne"))

        models = QWidget()
        ml = QHBoxLayout(models)
        left = QVBoxLayout()
        self.profiles = QListWidget()
        left.addWidget(self.profiles)
        buttons = QHBoxLayout()
        add = QPushButton(tr("Dodaj"))
        remove = QPushButton(tr("Usuń profil"))
        buttons.addWidget(add)
        buttons.addWidget(remove)
        left.addLayout(buttons)
        ml.addLayout(left, 1)
        right = QFormLayout()
        self.profile_name = QLineEdit()
        self.family = QComboBox()
        for key, label in FAMILIES.items():
            self.family.addItem(label, key)
        right.addRow(tr("Nazwa profilu"), self.profile_name)
        right.addRow(tr("Rodzina"), self.family)
        self.fields = {}
        self.field_widgets = {}
        for key, label in (
            ("checkpoint", "Checkpoint SD/SDXL"),
            ("diffusion", "Diffusion / transformer"),
            ("encoder", tr("Enkoder tekstu")),
            ("vae", "VAE"),
            ("lora", tr("LoRA (opcjonalnie)")),
        ):
            widget, edit = file_field(self)
            self.fields[key] = edit
            self.field_widgets[key] = widget
            right.addRow(label, widget)
        self.lora_strength = DecimalSpinBox()
        self.lora_strength.setRange(-3, 3)
        self.lora_strength.setSingleStep(0.05)
        self.shift = DecimalSpinBox()
        self.shift.setRange(0.1, 20)
        self.shift.setSingleStep(0.1)
        right.addRow(tr("Siła LoRA"), self.lora_strength)
        right.addRow("Flow shift (Qwen/MOSS)", self.shift)
        scan = QPushButton(tr("Przeglądaj modele w katalogach…"))
        right.addRow(scan)
        desc = QLabel(
            tr(
                "SD/SDXL: kompletny checkpoint .safetensors.\nQwen/MOSS: trzy zgodne pliki — diffusion, enkoder i VAE.\nSurowe GGUF/GPTQ i SDNQ z ZPix wymagają innych loaderów. Użyj formatu ComfyUI: BF16 lub wag z metadanymi comfy_quant, np. int8_convrot/w4a8."
            )
        )
        desc.setWordWrap(True)
        desc.setObjectName("muted")
        right.addRow(desc)
        ml.addLayout(right, 3)
        tabs.addTab(models, tr("Modele lokalne"))
        add.clicked.connect(self.add_profile)
        remove.clicked.connect(self.remove_profile)
        self.profiles.currentRowChanged.connect(self.select_profile)
        self.family.currentIndexChanged.connect(self.update_family)
        scan.clicked.connect(self.scan)
        self.refresh_profiles()

        bg = QWidget()
        bf = QFormLayout(bg)
        bgwidget, self.background_model = file_field(
            self, settings.background_model, pattern=tr("Model segmentacji (*.onnx)")
        )
        bf.addRow(tr("Lokalny model ONNX"), bgwidget)
        self.bg_type = QComboBox()
        self.bg_type.addItem(tr("U2Net • maska prawdopodobieństwa"), "u2net")
        self.bg_type.addItem(tr("ISNet • maska prawdopodobieństwa"), "isnet")
        self.bg_type.addItem("BiRefNet • logits + sigmoid", "birefnet")
        self.bg_type.setCurrentIndex(
            max(0, self.bg_type.findData(settings.background_normalization))
        )
        self.bg_size = QComboBox()
        for size in (320, 512, 1024):
            self.bg_size.addItem(str(size), size)
        self.bg_size.setCurrentIndex(max(0, self.bg_size.findData(settings.background_size)))
        bf.addRow(tr("Format modelu"), self.bg_type)
        bf.addRow(tr("Rozmiar wejścia"), self.bg_size)
        bginfo = QLabel(
            tr(
                "Model musi przyjmować RGB float32 NCHW i zwracać pojedynczą maskę N1HW. Ustaw rozmiar zgodny z modelem (U2Net zwykle 320, ISNet/BiRefNet zwykle 1024). Wagi wybierasz z dysku; Paint.TES ich nie pobiera."
            )
        )
        bginfo.setWordWrap(True)
        bf.addRow(bginfo)
        tabs.addTab(bg, tr("Usuwanie tła"))
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def save_profile(self):
        if 0 <= self.profile_index < len(self.settings.profiles):
            profile = self.settings.profiles[self.profile_index]
            profile.name = self.profile_name.text().strip() or tr("Nowy model")
            profile.family = self.family.currentData()
            for key, edit in self.fields.items():
                setattr(profile, key, edit.text().strip())
            profile.lora_strength = self.lora_strength.value()
            profile.shift = self.shift.value()
            item = self.profiles.item(self.profile_index)
            if item:
                item.setText(profile.name)

    def refresh_profiles(self, index=0):
        self.profiles.blockSignals(True)
        self.profiles.clear()
        for profile in self.settings.profiles:
            self.profiles.addItem(profile.name)
        self.profiles.blockSignals(False)
        self.profile_index = -1
        if self.settings.profiles:
            self.profiles.setCurrentRow(min(index, len(self.settings.profiles) - 1))
        else:
            self.update_family()

    def select_profile(self, index):
        self.save_profile()
        self.profile_index = index
        if index < 0 or index >= len(self.settings.profiles):
            return
        profile = self.settings.profiles[index]
        self.profile_name.setText(profile.name)
        self.family.setCurrentIndex(max(0, self.family.findData(profile.family)))
        for key, edit in self.fields.items():
            edit.setText(getattr(profile, key))
        self.lora_strength.setValue(profile.lora_strength)
        self.shift.setValue(profile.shift)
        self.update_family()

    def update_family(self):
        single = self.family.currentData() in ("sd15", "sdxl")
        for key, widget in self.field_widgets.items():
            widget.setEnabled(
                key == "lora" or (key == "checkpoint" if single else key != "checkpoint")
            )
        self.shift.setEnabled(not single)

    def add_profile(self):
        self.save_profile()
        self.settings.profiles.append(ModelProfile())
        self.refresh_profiles(len(self.settings.profiles) - 1)

    def remove_profile(self):
        index = self.profiles.currentRow()
        if index >= 0:
            self.profile_index = -1
            self.settings.profiles.pop(index)
            self.refresh_profiles(max(0, index - 1))

    def scan(self):
        roots = [line.strip() for line in self.roots.toPlainText().splitlines() if line.strip()]
        paths = scan_models(roots)
        if not paths:
            QMessageBox.information(
                self,
                tr("Modele lokalne"),
                tr("Nie znaleziono wag .safetensors w podanych katalogach."),
            )
            return
        picked, ok = QInputDialog.getItem(
            self,
            tr("Modele lokalne"),
            tr("Znalezione pliki (wybrany wpis skopiuje się do schowka):"),
            [str(p) for p in paths],
            0,
            False,
        )
        if ok:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(picked)
            QMessageBox.information(
                self,
                tr("Ścieżka skopiowana"),
                tr(
                    "Wklej ścieżkę w odpowiednie pole profilu: checkpoint, diffusion, enkoder lub VAE."
                ),
            )

    def accept(self):
        self.save_profile()
        self.settings.language = self.language.currentData()
        self.settings.model_roots = [
            line.strip() for line in self.roots.toPlainText().splitlines() if line.strip()
        ]
        self.settings.output_dir = self.output.text().strip() or str(
            Path.home() / "Pictures" / "Paint.TES"
        )
        self.settings.gpu_uuid = self.gpu.currentData()
        self.settings.precision = self.precision.currentData()
        self.settings.offload = self.offload.currentData()
        self.settings.undo_limit = self.undo.value()
        self.settings.background_model = self.background_model.text().strip()
        self.settings.background_size = self.bg_size.currentData()
        self.settings.background_normalization = self.bg_type.currentData()
        super().accept()
