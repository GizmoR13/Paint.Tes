# Walidacja pierwszej wersji

Stan testów: 2026-11-12, Ubuntu 24.04, proprietary NVIDIA 580.178.04,
Tesla V100-PCIE-32GB. Python 3.12.3, PyTorch 2.11.0+cu126, PySide6 6.10.2.
Silnik ComfyUI: commit `3f438ca69f3d0efc5f748de055daeea9ba26ee50`.

## Sprawdzone

- 29 testów automatycznych: wszystkie kombinacje rodzin i trybów w grafach,
  maski, zachowanie pikseli, padding bez przeskalowania, historia i zapis ustawień,
  karty/referencje, wpisywanie promptu, zaznaczenie, pędzel, cofanie i profile modeli.
- Mały syntetyczny model ONNX na fizycznej V100: wejście lokalne, wykonanie CUDA,
  skalowanie maski, zachowanie kanału alfa, wynik RGBA. Test nie ocenia segmentacji
  rzeczywistego modelu U2Net/BiRefNet; jego wag nie było na dysku.
- Qwen-Image 2.1 z istniejących wag `int8_convrot`: rzeczywiste zadania text to
  image, image to image z niezależną referencją, inpaint i outpaint. Próby po jednym
  kroku, obrazy 128×128 (outpaint 160×160). Sprawdzono rozmiary i niezmienione
  piksele poza maską. Nie jest to benchmark ani ocena jakości.
- MOSS-Image: rzeczywisty text to image 128×128 / 1 krok na lokalnym transformerze
  int8_convrot, enkoderze Qwen3.5 w4a8 z metadanymi Comfy i małym VAE Flux2.
  Dodatkowo generacja 512×512, 20 kroków, CFG 4: poprawny wizualnie obraz,
  około 35 s po uruchomieniu silnika (jedna próba, nie benchmark).
- Start prywatnego silnika na V100, lista loaderów i zakończenie własnego procesu.
- Render GUI Qt oraz kontrola układu na zrzutach. Brakującą bibliotekę xcb-cursor
  rozpakowano prywatnie dla aplikacji; pakiety systemowe pozostały bez zmian.

## Jeszcze niezweryfikowane

- Rzeczywista generacja na bazowych checkpointach SD 1.5/SDXL — nie było
  odpowiedniego pełnego checkpointu w obsługiwanym formacie. Grafy są testowane,
  ale sama walidacja grafu nie potwierdza jakości ani zgodności dowolnych wag.
- Duże rozdzielczości, długie sesje i zużycie pamięci dla wszystkich ustawień.
- Rzeczywiste LoRA i jakość segmentacji na trenowanym lokalnym modelu ONNX.
- Inne dystrybucje Ubuntu i inne karty niż przetestowana V100.

Nie pobierano modeli w ramach testów. Nie zmieniano istniejącej instalacji
ComfyUI, sterownika, ustawień zasilania ani działających silników LLM.
