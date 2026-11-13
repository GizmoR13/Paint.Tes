# Paint.TES

Natywny edytor obrazu dla rodziny Ubuntu, z kawowym interfejsem i lokalną generacją
na NVIDIA V100/V100S/TITAN V (Volta, sm_70). Układ pracy inspirowany edytorami typu
Paint.NET: narzędzia po lewej, dokumenty w kartach i panel AI po prawej.

![Paint.Tes — natywne okno z obrazem wygenerowanym lokalnie na V100](docs/screens/paint-tes.png)

## Version 0.3 — FLUX.3 / Z-Image / Krea 2

English is now the default UI language. Switch immediately in
**Settings → General → Language**. Both toolbars use icons with localized
tooltips. Seed is an exact integer input with last-seed reuse; denoising strength
accepts either decimal separator and applies to editing modes.

[English user guide](docs/USER_GUIDE.md) · [Instrukcja po polsku](docs/INSTRUKCJA.md)

## Funkcje

- Text to image, image to image, inpaint i outpaint.
- Osobne karty obrazów; wyniki AI zawsze otwierane jako nowe dokumenty.
- Referencja z innej karty: niezależna referencja w Qwen-Image 2.1 i FLUX.3, styl w Krea 2 przez zgodną LoRA; dla pozostałych
  rodzin karta referencji może być źródłem image to image.
- Prostokąt, elipsa, lasso, wielokąt, odwracanie i zmiękczanie maski.
- Pędzel, gumka, schowek, kadrowanie, obrót, zmiana rozmiaru i cofanie zmian.
- Usuwanie tła do przezroczystego PNG z lokalnego modelu ONNX.
- Profile lokalnych checkpointów SD 1.5/SDXL i zestawów Qwen-Image 2.1/MOSS, FLUX.3, Z-Image i Krea 2.
- Wybór karty według UUID, kontrola precyzji, pamięci i katalogów w ustawieniach.

**Modele wybierasz z dysku. Program nie pobiera wag ani nie wymaga konta/API.**

## Instalacja na Ubuntu 24.04 / pochodnych, x86_64

Wymagane: działający proprietary sterownik NVIDIA wspierający Volta i CUDA 12.6,
Python 3.12 (instalator `uv` może go dostarczyć), Git i [uv](https://docs.astral.sh/uv/getting-started/installation/).
Na Ubuntu wymagane biblioteki Qt są zwykle już dostępne; jeśli Qt zgłasza brak
platformy `xcb`, sprawdź systemowe `libxkbcommon-x11-0` i `libegl1`. Brakujące
`libxcb-cursor0` instalator rozpakowuje we własnym `../qt-runtime`, bez sudo.
Nie wymieniaj sterownika GPU dla tej aplikacji.

```bash
git clone --recurse-submodules https://github.com/GizmoR13/Paint.Tes.git
cd Paint.Tes
./setup.sh
./install-desktop.sh
./start.sh
```

Instalator tworzy osobne `../.venv`, obok repozytorium. Nie wskazuj środowiska
innej aplikacji. Opcjonalne nadpisanie: `PAINT_TES_VENV=/pełna/ścieżka`.
Zależności są ograniczone do przetestowanego zestawu (`constraints-tested.txt`).
PyTorch 2.11.0 i torchvision 0.26.0 są przypięte do CUDA 12.6, z obsługą sm_70.
Instalacja pobiera biblioteki programu, **nie modele**. Kolejne uruchomienia nie
wywołują instalatora ani aktualizacji zależności.

## Modele

W **Ustawienia → Modele lokalne** dodaj nazwany profil:

| Rodzina | Wymagane lokalne pliki |
|---|---|
| SD 1.5 / SDXL | kompletny bazowy checkpoint `.safetensors` z enkoderem i VAE |
| Qwen-Image 2.1 | diffusion / transformer, zgodny enkoder Qwen3-VL i VAE |
| MOSS-Image | diffusion / transformer, zgodny enkoder Qwen3.5 i VAE Flux2 |
| FLUX.3 Klein / Base | diffusion, Qwen3-VL-4B, Flux2 VAE; opcjonalnie osobny prompt upsampler |
| Z-Image / Turbo | diffusion, Qwen3-4B (bez VL), Flux VAE |
| Krea 2 Raw / Turbo | diffusion, Qwen3-VL-4B, VAE Qwen-Image (nie 2.1) |
| Usuwanie tła | ONNX U2Net/ISNet/BiRefNet, skonfigurowany oddzielnie |

Formaty osobnych komponentów: natywne wagi ComfyUI, BF16 albo obsługiwana
kwantyzacja z metadanymi `comfy_quant` (np. int8_convrot/w4a8). Surowe GGUF,
GPTQ bez metadanych ComfyUI, SDNQ z ZPix i katalogi Diffusers nie są obsługiwane
przez ten loader. Samo rozszerzenie `.safetensors` nie gwarantuje zgodności
architektury i wariantu kwantyzacji. Opcjonalna LoRA musi pasować do modelu.
Specjalistyczne checkpointy inpaint wymagające dodatkowych kanałów nie są celem
pierwszej wersji; maskowane edycje korzystają z bazowych modeli.

Nowe rodziny: [wymagane komponenty i parametry](docs/MODELS.md).

Szczegóły obsługi: [Instrukcja](docs/INSTRUKCJA.md).

## Silnik V100

GUI jest napisane w PySide6. Silnik to przypięty ComfyUI jako podmoduł Git;
uruchamia się w prywatnym procesie na losowym porcie loopback dopiero przy
pierwszym zadaniu. Nie korzysta z istniejącej usługi ComfyUI i jej nie zmienia.
Proces sprawdza CUDA 12.x, sm_70 i wybraną kartę, zanim może załadować model.

Na Volcie używa math SDPA, FP32 w trybie bezpiecznym, standardowego offloadu
zamiast dynamicznego VRAM oraz enkodera na GPU z możliwością offloadu do RAM.
FP16 jest opcjonalny dla SD/SDXL. Rodziny z osobnymi komponentami wymagają trybu bezpiecznego, aby nie
ryzykować przepełnień BF16→FP16. Dwie karty nie łączą automatycznie pamięci.

## Walidacja i ograniczenia

Zobacz [raport testów](docs/VALIDATION.md). Ta wersja jest pierwszą wersją roboczą.
Duże rozdzielczości, warianty wag i LoRA wymagają testów na konkretnym sprzęcie.
Brak lokalnego modelu ONNX oznacza, że przed usunięciem tła trzeba go wskazać.
Program nigdy nie pobierze go automatycznie.

```bash
uv pip install --python ../.venv/bin/python pytest pytest-qt onnx ruff
QT_QPA_PLATFORM=offscreen ../.venv/bin/python -m pytest -q tests
# Opcjonalny test małego modelu ONNX na V100:
PAINT_TES_GPU_TESTS=1 QT_QPA_PLATFORM=offscreen ../.venv/bin/python -m pytest -q tests/test_gpu_optional.py
```

## Licencja

GPL-3.0-or-later. [ComfyUI](https://github.com/Comfy-Org/ComfyUI) jest podmodułem
na własnej licencji GPL-3.0; zachowano jego prawa autorskie. Paint.Tes nie zawiera
kodu ani zasobów Paint.NET. PySide6/Qt i pozostałe biblioteki zachowują swoje licencje.
