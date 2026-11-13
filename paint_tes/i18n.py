"""Small explicit EN/PL catalog. User prompts and document names are never translated."""

from __future__ import annotations

import os
import re

LANGUAGE = os.environ.get("PAINT_TES_LANGUAGE", "en")
EN = {
    "Plik": "File",
    "Edycja": "Edit",
    "Zaznaczenie": "Selection",
    "Obraz": "Image",
    "Widok": "View",
    "Pomoc": "Help",
    "Nowy": "New",
    "Nowy obraz": "New image",
    "Nowy obraz…": "New image…",
    "Nowy obraz (px)": "New image (px)",
    "Otwórz": "Open",
    "Otwórz…": "Open…",
    "Otwórz obrazy": "Open images",
    "Otwórz obrazy…": "Open images…",
    "Zapisz": "Save",
    "Zapisz jako…": "Save as…",
    "Zapisz obraz": "Save image",
    "Zamknij kartę": "Close tab",
    "Zakończ": "Quit",
    "Cofnij": "Undo",
    "Ponów": "Redo",
    "Kopiuj obraz": "Copy image",
    "Wklej jako nową kartę": "Paste as new tab",
    "Ze schowka": "From clipboard",
    "Wyczyść zaznaczenie": "Clear selected pixels",
    "Ustawienia": "Settings",
    "Ustawienia…": "Settings…",
    "Zaznacz wszystko": "Select all",
    "Usuń zaznaczenie": "Deselect",
    "Odwróć zaznaczenie": "Invert selection",
    "Zmiękcz krawędzie…": "Feather edges…",
    "Przytnij do zaznaczenia": "Crop to selection",
    "Zmień rozmiar…": "Resize…",
    "Obróć w prawo": "Rotate clockwise",
    "Odbij poziomo": "Flip horizontally",
    "Użyj jako referencji": "Use as reference",
    "Generuj": "Generate",
    "Usuń tło": "Remove background",
    "Zwolnij pamięć silnika": "Release engine memory",
    "Dopasuj do okna": "Fit to window",
    "Dopasuj": "Fit",
    "Rozmiar rzeczywisty": "Actual size",
    "Instrukcja": "User guide",
    "O Paint.TES": "About Paint.TES",
    "Plik i widok": "File and view",
    "Pędzel: ": "Brush: ",
    "Kolor": "Color",
    "Narzędzia": "Tools",
    "Przesuń": "Pan",
    "Prostokąt": "Rectangle selection",
    "Elipsa": "Ellipse selection",
    "Wielokąt": "Polygon selection",
    "Pędzel": "Brush",
    "Gumka": "Eraser",
    "STUDIO AI": "AI STUDIO",
    "KAWA • PIKSELE • VOLTA": "COFFEE • PIXELS • VOLTA",
    "Twoje obrazy. Twoje modele. Lokalna V100.": "Your images. Your models. Your local V100.",
    "Ustaw modele lokalne…": "Set up local models…",
    "Gotowy • silnik AI uruchamia się dopiero przy generowaniu": "Ready • the AI engine starts only when needed",
    "Tryb": "Mode",
    "Modele i ustawienia…": "Models and settings…",
    "Co chcesz zobaczyć lub zmienić?": "What would you like to create or change?",
    "Negatywny prompt (opcjonalnie)": "Negative prompt (optional)",
    "Karta referencji": "Reference tab",
    "Brak": "None",
    "Kroki": "Steps",
    "Siła zmiany": "Denoising strength",
    "Generuj obraz": "Generate image",
    "Usuń tło → przezroczystość": "Remove background → transparency",
    "Anuluj zadanie": "Cancel task",
    "Wyniki powstają w nowych kartach. Zapisujesz je samodzielnie.": "Results open in new tabs. Save the images you want to keep.",
    "Dodaj lokalny profil w ustawieniach": "Add a local profile in Settings",
    "Dodaj profil lokalnego modelu w ustawieniach.": "Add a local model profile in Settings.",
    "Inna karta jest niezależną referencją Qwen. Dla edycji źródłem jest aktywna karta.": "Another tab is an independent Qwen reference. For editing, the active tab is the source.",
    "Dla SD/SDXL/MOSS karta referencji może być źródłem image-to-image. Niezależne referencje są dostępne w Qwen 2.1.": "For SD/SDXL/MOSS, the reference tab can be the image-to-image source. Independent references are available with Qwen 2.1.",
    "Inpaint • zaznaczenie": "Inpaint • selection",
    "Outpaint • nowe marginesy": "Outpaint • new margins",
    "Nazwa": "Name",
    "Tło": "Background",
    "Białe": "White",
    "Przezroczyste": "Transparent",
    "Kawowe": "Coffee",
    "Rozmiar (px)": "Size (px)",
    "Nowy obraz • Paint.TES": "New image • Paint.TES",
    "Model lokalny": "Local model",
    "Wygeneruj z promptu po utworzeniu": "Generate from the prompt after creating",
    "Opisz obraz. Model i parametry generowania są w panelu AI.": "Describe the image. Choose the local model and generation parameters above.",
    "Generacja używa wybranego lokalnego profilu. Rozmiar generacji: wielokrotność 16 px.": "Generation uses the selected local profile. Dimensions must be multiples of 16 pixels.",
    "Losowy, jeśli puste": "Random when empty",
    "losowy": "random",
    "Outpaint • rozszerz płótno": "Outpaint • expand canvas",
    "Lewo": "Left",
    "Prawo": "Right",
    "Góra": "Top",
    "Dół": "Bottom",
    "Oryginalne piksele zostaną zachowane. Generowane będą nowe marginesy.": "Original pixels will be preserved. Only the new margins will be generated.",
    "Ustawienia • Paint.TES": "Settings • Paint.TES",
    "Ustawienia Paint.TES": "Paint.TES settings",
    "Ogólne": "General",
    "Katalogi modeli": "Model folders",
    "Jeden lokalny katalog modeli w wierszu": "One local model folder per line",
    "Dodaj katalog…": "Add folder…",
    "Katalog modeli": "Model folder",
    "Domyślny zapis obrazów": "Default image output folder",
    "Karta AI": "AI GPU",
    "Automatycznie: zgodna karta z największą wolną pamięcią": "Automatic: compatible GPU with the most free memory",
    "Bezpieczny FP32 • wszystkie rodziny": "Safe FP32 • all model families",
    "FP16 • tylko SD/SDXL": "FP16 • SD/SDXL only",
    "Precyzja": "Precision",
    "Pamięć": "Memory",
    "Oszczędzaj VRAM (offload do RAM)": "Save VRAM (offload to RAM)",
    "Normalne wykorzystanie VRAM": "Normal VRAM usage",
    "Liczba kroków cofania (do 256 MiB na kartę)": "Undo steps (up to 256 MiB per tab)",
    "Dziennik silnika": "Engine log",
    "Silnik ładuje wyłącznie lokalne wagi. Nie pobiera modeli. Duże Qwen/MOSS mogą wymagać więcej RAM niż jest dostępne; zacznij od małego rozmiaru.": "The engine loads local weights only. It does not download models. Large Qwen/MOSS models may exceed available RAM; start with a small image.",
    "Dodaj": "Add",
    "Usuń profil": "Remove profile",
    "Nazwa profilu": "Profile name",
    "Rodzina": "Family",
    "Enkoder tekstu": "Text encoder",
    "LoRA (opcjonalnie)": "LoRA (optional)",
    "Siła LoRA": "LoRA strength",
    "Przeglądaj modele w katalogach…": "Browse models in folders…",
    "Modele lokalne": "Local models",
    "Nowy model": "New model",
    "SD/SDXL: kompletny checkpoint .safetensors.\nQwen/MOSS: trzy zgodne pliki — diffusion, enkoder i VAE.\nSurowe GGUF/GPTQ i SDNQ z ZPix wymagają innych loaderów. Użyj formatu ComfyUI: BF16 lub wag z metadanymi comfy_quant, np. int8_convrot/w4a8.": "SD/SDXL: a complete .safetensors checkpoint.\nQwen/MOSS: matching diffusion, text encoder and VAE files.\nRaw GGUF/GPTQ and ZPix SDNQ need other loaders. Use ComfyUI-format BF16 or weights with comfy_quant metadata, such as int8_convrot/w4a8.",
    "Usuwanie tła": "Background removal",
    "Lokalny model ONNX": "Local ONNX model",
    "Model segmentacji (*.onnx)": "Segmentation model (*.onnx)",
    "Format modelu": "Model format",
    "Rozmiar wejścia": "Input size",
    "U2Net • maska prawdopodobieństwa": "U2Net • probability mask",
    "ISNet • maska prawdopodobieństwa": "ISNet • probability mask",
    "Model musi przyjmować RGB float32 NCHW i zwracać pojedynczą maskę N1HW. Ustaw rozmiar zgodny z modelem (U2Net zwykle 320, ISNet/BiRefNet zwykle 1024). Wagi wybierasz z dysku; Paint.TES ich nie pobiera.": "The model must accept RGB float32 NCHW and return a single N1HW mask. Match its input size (usually 320 for U2Net, 1024 for ISNet/BiRefNet). Select local weights; Paint.TES does not download them.",
    "Nie znaleziono wag .safetensors w podanych katalogach.": "No .safetensors weights found in the selected folders.",
    "Znalezione pliki (wybrany wpis skopiuje się do schowka):": "Discovered files (the selected path will be copied to the clipboard):",
    "Ścieżka skopiowana": "Path copied",
    "Wklej ścieżkę w odpowiednie pole profilu: checkpoint, diffusion, enkoder lub VAE.": "Paste the path into the matching profile field: checkpoint, diffusion, encoder or VAE.",
    "Wybierz katalog": "Choose folder",
    "Wybierz katalog…": "Choose folder…",
    "Wybierz lokalny model": "Choose local model",
    "Wybierz lokalny plik…": "Choose local file…",
    "Wagi (*.safetensors)": "Weights (*.safetensors)",
    "Ustawienia zapisane.": "Settings saved.",
    "Poczekaj na zakończenie albo anuluj zadanie przed zmianą ustawień.": "Wait for the task to finish or cancel it before changing settings.",
    "Wybierz inną kartę, a następnie tę kartę w polu Karta referencji.": "Select another tab, then choose this tab in the Reference tab field.",
    "Niezapisany obraz": "Unsaved image",
    "Zmiękczenie maski": "Feather mask",
    "Promień (px)": "Radius (px)",
    "Rozmiar obrazu": "Image size",
    "Szerokość × wysokość (np. 1024x768)": "Width × height (for example 1024x768)",
    "Kolor pędzla": "Brush color",
    "Otwórz obraz albo utwórz nową kartę.": "Open an image or create a new tab.",
    "Zaznacz obszar lassem, prostokątem lub elipsą.": "Select an area with the lasso, rectangle or ellipse tool.",
    "Dodaj co najmniej jeden margines.": "Add at least one margin.",
    "Niezależna referencja działa z Qwen 2.1. Dla tego modelu wybierz image-to-image lub ustaw referencję na Brak.": "Independent references require Qwen 2.1. For this model, choose image-to-image or set the reference to None.",
    "Otwórz obraz do usunięcia tła.": "Open an image to remove its background.",
    "Przygotowanie lokalnego zadania…": "Preparing local task…",
    "Gotowe. Wynik w nowej karcie — zapisz, aby zachować obraz.": "Done. The result is in a new tab — save it to keep the image.",
    "Zadanie zakończone błędem. Obrazy źródłowe pozostały bez zmian.": "Task failed. Source images are unchanged.",
    "Anulowanie…": "Cancelling…",
    "Najpierw anuluj bieżące zadanie.": "Cancel the current task first.",
    "Pamięć silnika Paint.TES zwolniona.": "Paint.TES engine memory released.",
    "Anulowano.": "Cancelled.",
    "Anulowano. Obrazy źródłowe pozostały w kartach.": "Cancelled. Source images remain in their tabs.",
    "Anulowano generowanie.": "Generation cancelled.",
    "Anulowano uruchamianie silnika.": "Engine startup cancelled.",
    "W Ustawienia → Usuwanie tła wybierz lokalny model ONNX.": "Choose a local ONNX model in Settings → Background removal.",
    "Nie znaleziono zgodnej V100/V100S/TITAN V.": "No compatible V100/V100S/TITAN V found.",
    "Usuwanie tła z użyciem lokalnego modelu ONNX…": "Removing background with a local ONNX model…",
    "Bez tła • ": "Background removed • ",
    "Nieznana rodzina modelu.": "Unknown model family.",
    "Wybierz wagi .safetensors. GGUF i katalogi Diffusers wymagają innego loadera i nie są obsługiwane w tej wersji.": "Select .safetensors weights. GGUF and Diffusers folders need other loaders and are not supported in this version.",
    "Podaj nazwę profilu.": "Enter a profile name.",
    "nie wybrano": "not selected",
    "W ustawieniach wybierz dostępną V100/V100S/TITAN V.": "Select an available V100/V100S/TITAN V in Settings.",
    "Uruchamianie lokalnego silnika V100…": "Starting local V100 engine…",
    "Nie udało się uruchomić silnika.\n": "Could not start the engine.\n",
    "Silnik nie uruchomił się w ciągu 180 s. Sprawdź dziennik w ustawieniach.": "The engine did not start within 180 seconds. Check the log in Settings.",
    "Qwen/MOSS wymaga trybu bezpiecznego FP32 na V100. Zmień precyzję w ustawieniach.": "Qwen/MOSS requires safe FP32 on V100. Change precision in Settings.",
    "Silnik odrzucił konfigurację modelu:\n": "The engine rejected the model configuration:\n",
    "Generowanie… pierwsze ładowanie dużego modelu może potrwać kilka minut.": "Generating… loading a large model for the first time can take several minutes.",
    "Silnik zakończył pracę. Możliwy brak RAM/VRAM; sprawdź dziennik.": "The engine exited. It may have run out of RAM/VRAM; check the log.",
    "Błąd generacji:\n": "Generation error:\n",
    "Silnik zakończył zadanie bez obrazu.": "The engine finished without an image.",
    "Wybierz V100 według UUID w ustawieniach Paint.TES.": "Select a V100 by UUID in Paint.TES Settings.",
    "Brak dostępnej karty NVIDIA CUDA.": "No NVIDIA CUDA GPU is available.",
    "Paint.TES obsługuje V100/V100S/TITAN V (Volta sm_70), jedną kartę na zadanie.": "Paint.TES supports V100/V100S/TITAN V (Volta sm_70), one GPU per task.",
    "Środowisko wymaga PyTorch CUDA 12.x z obsługą sm_70.": "This environment requires PyTorch CUDA 12.x with sm_70 support.",
    "Brakuje silnika. Uruchom git submodule update --init --recursive.": "Engine missing. Run git submodule update --init --recursive.",
    "Rozmiar: 16–8192 px na bok, maksymalnie 32 megapiksele.": "Size: 16–8192 pixels per side, up to 32 megapixels.",
    "Obraz, wynik i maska muszą mieć ten sam rozmiar.": "The source, result and mask must have the same dimensions.",
    "Marginesy nie mogą być ujemne.": "Margins cannot be negative.",
    "Nieznany tryb generacji.": "Unknown generation mode.",
    "Nieprawidłowe parametry generacji.": "Invalid generation parameters.",
    "Seed poza zakresem.": "Seed must be between 0 and 9223372036854775807.",
    "Wymiary przekazane silnikowi muszą być wielokrotnością 16.": "Engine dimensions must be multiples of 16.",
    "Wymiary generacji muszą być wielokrotnością 16 px.": "Generation dimensions must be multiples of 16 pixels.",
    "Ten tryb wymaga obrazu źródłowego.": "This mode requires a source image.",
    "Inpaint/outpaint wymaga maski.": "Inpaint/outpaint requires a mask.",
    "Referencja niezależna od obrazu źródłowego wymaga Qwen-Image 2.1. Dla SDXL/MOSS użyj karty referencji jako źródła image-to-image.": "An independent reference requires Qwen-Image 2.1. For SDXL/MOSS, use the reference tab as the image-to-image source.",
    "Wybierz lokalny model segmentacji .onnx w ustawieniach.": "Select a local .onnx segmentation model in Settings.",
    "Rozmiar wejściowy modelu segmentacji: 320, 512 lub 1024.": "Segmentation input size must be 320, 512 or 1024.",
    "ONNX Runtime nie ma backendu CUDA. Uruchom setup.sh.": "ONNX Runtime has no CUDA backend. Run setup.sh.",
    "Nie udało się uruchomić segmentacji na V100.": "Could not start segmentation on V100.",
    "Model nie zwrócił pojedynczej maski. Obsługiwane: U2Net/ISNet/BiRefNet z wejściem RGB NCHW i maską N1HW.": "The model did not return a single mask. Supported: U2Net/ISNet/BiRefNet with RGB NCHW input and an N1HW mask.",
    "Paint.TES • lokalne studio obrazu": "Paint.TES • local image studio",
    "Generacja": "Generation",
    " MiB wolne · ": " MiB free · ",
    " — gdy płótno ma fokus)": " — when the canvas has focus)",
    "Język": "Language",
    "Zmień język bez ponownego uruchamiania.": "Change language without restarting.",
    "Siła zmiany działa w trybach image-to-image, inpaint i outpaint. Text-to-image zawsze używa pełnego szumu (1.0).": "Strength applies to image-to-image, inpaint and outpaint. Text-to-image always uses full noise (1.0).",
    "0.01 = mała zmiana; 1.00 = pełny poziom szumu. Przy niewielu krokach efekty są skokowe.": "0.01 = small change; 1.00 = full noise. With very few steps, changes are discrete.",
    "Losowy (puste pole)": "Random (empty field)",
    "Wpisz liczbę 0–9223372036854775807. Puste pole losuje nowy seed dla każdego zadania.": "Enter 0–9223372036854775807. Leave empty for a new random seed per task.",
    "Użyj ostatniego seeda": "Reuse last seed",
    "Ostatni seed: {0}": "Last seed: {0}",
    "Ostatni seed: —": "Last seed: —",
    "Seed musi być liczbą całkowitą od 0 do 9223372036854775807.": "Seed must be an integer from 0 to 9223372036854775807.",
}
PL = {
    "Text to image": "Tekst na obraz",
    "Image to image": "Obraz na obraz",
    "Seed": "Seed",
    "Sampler": "Sampler",
    "Scheduler": "Harmonogram",
}


def set_language(language: str):
    global LANGUAGE
    LANGUAGE = language if language in ("en", "pl") else "en"
    os.environ["PAINT_TES_LANGUAGE"] = LANGUAGE


def tr(source: str) -> str:
    return EN.get(source, source) if LANGUAGE == "en" else PL.get(source, source)


def translated_text(text: str) -> str:
    """Retranslate UI labels, never user text fields or document tab titles."""
    for source, english in EN.items():
        if text in (source, english):
            return tr(source)
    for source, polish in PL.items():
        if text in (source, polish):
            return tr(source)
    # Toolbar shortcut suffixes are not part of the translated label.
    if " (" in text and text.endswith(")"):
        prefix, suffix = text.rsplit(" (", 1)
        translated = translated_text(prefix)
        if translated != prefix:
            return translated + " (" + suffix
    # Formatted titles and status messages keep their captured values.
    for source, english in EN.items():
        if "{0}" not in source:
            continue
        for pattern in (source, english):
            regex = re.escape(pattern)
            for index in range(8):
                regex = regex.replace(re.escape("{" + str(index) + "}"), f"(?P<v{index}>.*?)")
            match = re.fullmatch(regex, text, flags=re.DOTALL)
            if match:
                values = [match.groupdict().get(f"v{i}", "") for i in range(8)]
                return tr(source).format(*values)
    return text


_qt_translator = None


def apply_qt_language():
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtWidgets import QApplication

    global _qt_translator
    app = QApplication.instance()
    if not app:
        return
    if _qt_translator:
        app.removeTranslator(_qt_translator)
    QLocale.setDefault(QLocale("pl_PL" if LANGUAGE == "pl" else "en_GB"))
    _qt_translator = QTranslator(app)
    if LANGUAGE == "pl" and _qt_translator.load(
        "qtbase_pl", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    ):
        app.installTranslator(_qt_translator)


EN.update(
    {
        "Nie udało się odczytać ustawień: {0}\nPlik nie zostanie nadpisany. Popraw go lub przenieś przed uruchomieniem.": "Could not read settings: {0}\nThe file will not be overwritten. Fix or move it before starting.",
        "Zapisać zmiany w „{0}”?": "Save changes to “{0}”?",
        "{0} · {1} MiB wolne · {2}": "{0} · {1} MiB free · {2}",
        "Zapisano: {0}": "Saved: {0}",
        "Obrazy (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)": "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        "Paint.TES 0.2.1\nNatywny edytor dla Ubuntu i kart NVIDIA Volta.\nLokalne modele • prywatne repozytorium\nGPL-3.0-or-later. Silnik: ComfyUI (GPL-3.0).": "Paint.TES 0.2.1\nNative image editor for Ubuntu and NVIDIA Volta.\nLocal models • private repository\nGPL-3.0-or-later. Engine: ComfyUI (GPL-3.0).",
    }
)


def retranslate_widgets(root):
    from PySide6.QtCore import QObject
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QComboBox,
        QDoubleSpinBox,
        QLabel,
        QLineEdit,
        QMenu,
        QPushButton,
        QSpinBox,
    )

    for widget in [root, *root.findChildren(QObject)]:
        for prop in ("toolTip", "statusTip", "windowTitle", "accessibleName"):
            if hasattr(widget, prop):
                setter = getattr(widget, "set" + prop[0].upper() + prop[1:])
                setter(translated_text(getattr(widget, prop)()))
        if isinstance(widget, (QAction, QLabel, QPushButton)):
            widget.setText(translated_text(widget.text()))
        if isinstance(widget, QMenu):
            widget.setTitle(translated_text(widget.title()))
        if isinstance(widget, QLineEdit):
            widget.setPlaceholderText(translated_text(widget.placeholderText()))
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setPrefix(translated_text(widget.prefix()))
            widget.setSuffix(translated_text(widget.suffix()))
        if isinstance(widget, QComboBox) and not widget.property("userContent"):
            for index in range(widget.count()):
                widget.setItemText(index, translated_text(widget.itemText(index)))


EN["Brak lokalnego pliku ({0}): {1}"] = "Missing local file ({0}): {1}"

EN[
    "Siłę można ustawić w dowolnym trybie. Jest używana w image-to-image, inpaint i outpaint; text-to-image ją pomija (szum 1.0)."
] = "You can edit strength in any mode. It applies to image-to-image, inpaint and outpaint. Text-to-image ignores it (noise 1.0)."
