from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Qt
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


def spin(value, low=16, high=8192, step=16):
    box = QSpinBox()
    box.setRange(low, high)
    box.setSingleStep(step)
    box.setValue(value)
    return box


def file_field(parent, value="", directory=False, pattern="Wagi (*.safetensors)"):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    edit = QLineEdit(value)
    edit.setPlaceholderText("Wybierz lokalny plik…" if not directory else "Wybierz katalog…")
    button = QPushButton("…")
    button.setFixedWidth(35)

    def choose():
        start = edit.text() or str(Path.home())
        chosen = (
            QFileDialog.getExistingDirectory(parent, "Wybierz katalog", start)
            if directory
            else QFileDialog.getOpenFileName(parent, "Wybierz lokalny model", start, pattern)[0]
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
        self.setWindowTitle("Nowy obraz • Paint.Tes")
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit("Nowy obraz")
        self.width = spin(512)
        self.height = spin(512)
        sizes = QHBoxLayout()
        sizes.addWidget(self.width)
        sizes.addWidget(QLabel("×"))
        sizes.addWidget(self.height)
        self.background = QComboBox()
        self.background.addItems(["Białe", "Przezroczyste", "Kawowe"])
        form.addRow("Nazwa", self.name)
        form.addRow("Rozmiar (px)", sizes)
        form.addRow("Tło", self.background)
        self.model = QComboBox()
        for profile in parent.settings.profiles:
            self.model.addItem(profile.name, profile.id)
        self.model.setCurrentIndex(max(0, self.model.findData(parent.model.currentData())))
        self.steps = spin(parent.steps.value(), 1, 150, 1)
        self.cfg = QDoubleSpinBox()
        self.cfg.setRange(0, 30)
        self.cfg.setValue(parent.cfg.value())
        self.seed = QLineEdit(parent.seed.toPlainText())
        self.seed.setPlaceholderText("Losowy, jeśli puste")
        form.addRow("Model lokalny", self.model)
        form.addRow("Kroki", self.steps)
        form.addRow("CFG", self.cfg)
        form.addRow("Seed", self.seed)
        layout.addLayout(form)
        self.generate = QCheckBox("Wygeneruj z promptu po utworzeniu")
        self.prompt = QPlainTextEdit(prompt)
        self.prompt.setPlaceholderText("Opisz obraz. Model i parametry generowania są w panelu AI.")
        layout.addWidget(self.generate)
        layout.addWidget(self.prompt)
        info = QLabel(
            "Generacja używa wybranego lokalnego profilu. Rozmiar generacji: wielokrotność 16 px."
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
        self.setWindowTitle("Outpaint • rozszerz płótno")
        layout = QFormLayout(self)
        self.margins = {}
        for key, label in (
            ("left", "Lewo"),
            ("top", "Góra"),
            ("right", "Prawo"),
            ("bottom", "Dół"),
        ):
            self.margins[key] = spin(128, 0, 4096, 16)
            layout.addRow(label + " (px)", self.margins[key])
        text = QLabel("Oryginalne piksele zostaną zachowane. Generowane będą nowe marginesy.")
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
        self.setWindowTitle("Ustawienia • Paint.Tes")
        self.resize(860, 680)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        general = QWidget()
        form = QFormLayout(general)
        self.roots = QPlainTextEdit("\n".join(settings.model_roots))
        self.roots.setPlaceholderText("Jeden lokalny katalog modeli w wierszu")
        self.roots.setMaximumHeight(100)
        add_root = QPushButton("Dodaj katalog…")

        def add_folder():
            folder = QFileDialog.getExistingDirectory(self, "Katalog modeli")
            if folder:
                self.roots.appendPlainText(folder)

        add_root.clicked.connect(add_folder)
        form.addRow("Katalogi modeli", self.roots)
        form.addRow("", add_root)
        outwidget, self.output = file_field(self, settings.output_dir, directory=True)
        form.addRow("Domyślny zapis obrazów", outwidget)
        self.gpu = QComboBox()
        self.gpu.addItem("Automatycznie: zgodna karta z największą wolną pamięcią", "")
        for gpu in list_gpus():
            self.gpu.addItem(
                f"{gpu['name']} · {gpu['free']} MiB wolne · {gpu['uuid']}", gpu["uuid"]
            )
        index = self.gpu.findData(settings.gpu_uuid)
        if index >= 0:
            self.gpu.setCurrentIndex(index)
        form.addRow("Karta AI", self.gpu)
        self.precision = QComboBox()
        self.precision.addItem("Bezpieczny FP32 • wszystkie rodziny", "safe")
        self.precision.addItem("FP16 • tylko SD/SDXL", "fp16")
        self.precision.setCurrentIndex(max(0, self.precision.findData(settings.precision)))
        form.addRow("Precyzja", self.precision)
        self.offload = QComboBox()
        self.offload.addItem("Oszczędzaj VRAM (offload do RAM)", "lowvram")
        self.offload.addItem("Normalne wykorzystanie VRAM", "normalvram")
        self.offload.setCurrentIndex(max(0, self.offload.findData(settings.offload)))
        form.addRow("Pamięć", self.offload)
        self.undo = spin(settings.undo_limit, 1, 50, 1)
        form.addRow("Liczba kroków cofania (do 256 MiB na kartę)", self.undo)
        log = QLabel(str(data_path() / "engine" / "engine.log"))
        log.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Dziennik silnika", log)
        hint = QLabel(
            "Silnik ładuje wyłącznie lokalne wagi. Nie pobiera modeli. Duże Qwen/MOSS mogą wymagać więcej RAM niż jest dostępne; zacznij od małego rozmiaru."
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        form.addRow(hint)
        tabs.addTab(general, "Ogólne")

        models = QWidget()
        ml = QHBoxLayout(models)
        left = QVBoxLayout()
        self.profiles = QListWidget()
        left.addWidget(self.profiles)
        buttons = QHBoxLayout()
        add = QPushButton("Dodaj")
        remove = QPushButton("Usuń profil")
        buttons.addWidget(add)
        buttons.addWidget(remove)
        left.addLayout(buttons)
        ml.addLayout(left, 1)
        right = QFormLayout()
        self.profile_name = QLineEdit()
        self.family = QComboBox()
        for key, label in FAMILIES.items():
            self.family.addItem(label, key)
        right.addRow("Nazwa profilu", self.profile_name)
        right.addRow("Rodzina", self.family)
        self.fields = {}
        self.field_widgets = {}
        for key, label in (
            ("checkpoint", "Checkpoint SD/SDXL"),
            ("diffusion", "Diffusion / transformer"),
            ("encoder", "Enkoder tekstu"),
            ("vae", "VAE"),
            ("lora", "LoRA (opcjonalnie)"),
        ):
            widget, edit = file_field(self)
            self.fields[key] = edit
            self.field_widgets[key] = widget
            right.addRow(label, widget)
        self.lora_strength = QDoubleSpinBox()
        self.lora_strength.setRange(-3, 3)
        self.lora_strength.setSingleStep(0.05)
        self.shift = QDoubleSpinBox()
        self.shift.setRange(0.1, 20)
        self.shift.setSingleStep(0.1)
        right.addRow("Siła LoRA", self.lora_strength)
        right.addRow("Flow shift (Qwen/MOSS)", self.shift)
        scan = QPushButton("Przeglądaj modele w katalogach…")
        right.addRow(scan)
        desc = QLabel(
            "SD/SDXL: kompletny checkpoint .safetensors.\nQwen/MOSS: trzy zgodne pliki — diffusion, enkoder i VAE.\nSurowe GGUF/GPTQ i SDNQ z ZPix wymagają innych loaderów. Użyj formatu ComfyUI: BF16 lub wag z metadanymi comfy_quant, np. int8_convrot/w4a8."
        )
        desc.setWordWrap(True)
        desc.setObjectName("muted")
        right.addRow(desc)
        ml.addLayout(right, 3)
        tabs.addTab(models, "Modele lokalne")
        add.clicked.connect(self.add_profile)
        remove.clicked.connect(self.remove_profile)
        self.profiles.currentRowChanged.connect(self.select_profile)
        self.family.currentIndexChanged.connect(self.update_family)
        scan.clicked.connect(self.scan)
        self.refresh_profiles()

        bg = QWidget()
        bf = QFormLayout(bg)
        bgwidget, self.background_model = file_field(
            self, settings.background_model, pattern="Model segmentacji (*.onnx)"
        )
        bf.addRow("Lokalny model ONNX", bgwidget)
        self.bg_type = QComboBox()
        self.bg_type.addItem("U2Net • maska prawdopodobieństwa", "u2net")
        self.bg_type.addItem("ISNet • maska prawdopodobieństwa", "isnet")
        self.bg_type.addItem("BiRefNet • logits + sigmoid", "birefnet")
        self.bg_type.setCurrentIndex(
            max(0, self.bg_type.findData(settings.background_normalization))
        )
        self.bg_size = QComboBox()
        for size in (320, 512, 1024):
            self.bg_size.addItem(str(size), size)
        self.bg_size.setCurrentIndex(max(0, self.bg_size.findData(settings.background_size)))
        bf.addRow("Format modelu", self.bg_type)
        bf.addRow("Rozmiar wejścia", self.bg_size)
        bginfo = QLabel(
            "Model musi przyjmować RGB float32 NCHW i zwracać pojedynczą maskę N1HW. Ustaw rozmiar zgodny z modelem (U2Net zwykle 320, ISNet/BiRefNet zwykle 1024). Wagi wybierasz z dysku; Paint.Tes ich nie pobiera."
        )
        bginfo.setWordWrap(True)
        bf.addRow(bginfo)
        tabs.addTab(bg, "Usuwanie tła")
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def save_profile(self):
        if 0 <= self.profile_index < len(self.settings.profiles):
            profile = self.settings.profiles[self.profile_index]
            profile.name = self.profile_name.text().strip() or "Nowy model"
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
                self, "Modele lokalne", "Nie znaleziono wag .safetensors w podanych katalogach."
            )
            return
        picked, ok = QInputDialog.getItem(
            self,
            "Modele lokalne",
            "Znalezione pliki (wybrany wpis skopiuje się do schowka):",
            [str(p) for p in paths],
            0,
            False,
        )
        if ok:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(picked)
            QMessageBox.information(
                self,
                "Ścieżka skopiowana",
                "Wklej ścieżkę w odpowiednie pole profilu: checkpoint, diffusion, enkoder lub VAE.",
            )

    def accept(self):
        self.save_profile()
        self.settings.model_roots = [
            line.strip() for line in self.roots.toPlainText().splitlines() if line.strip()
        ]
        self.settings.output_dir = self.output.text().strip() or str(
            Path.home() / "Pictures" / "Paint.Tes"
        )
        self.settings.gpu_uuid = self.gpu.currentData()
        self.settings.precision = self.precision.currentData()
        self.settings.offload = self.offload.currentData()
        self.settings.undo_limit = self.undo.value()
        self.settings.background_model = self.background_model.text().strip()
        self.settings.background_size = self.bg_size.currentData()
        self.settings.background_normalization = self.bg_type.currentData()
        super().accept()
