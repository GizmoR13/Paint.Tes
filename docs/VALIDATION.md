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

## Aktualizacja 0.2 — 2026-11-13

- 37 testów automatycznych przeszło (test ONNX pozostaje osobnym testem opt-in).
- Domyślny angielski, przełączanie EN/PL bez utraty kart, promptu i parametrów,
  zapis języka, ikony i podpowiedzi obu pasków.
- Wpisanie `0.25` i `0,80` przekazuje prawidłową siłę zmiany do KSampler.
  Seed 0 i maksymalny 64-bitowy seed są przekazywane bez zaokrąglenia;
  wartości poza zakresem są odrzucane, a puste pole losuje seed.
- Rzeczywisty MOSS na V100: dwa identyczne zadania img2img 128×128 / 8 kroków
  dały identyczne piksele. Zmiana seeda oraz zmiana siły 0.25→0.80 zmieniły wynik.
- Nazwa pliku wyjściowego jest unikalna dla każdego zadania. Powtarzane zadanie
  ze stałym seedem nie odwołuje się do już usuniętego pliku roboczego z cache.
- Kontrola zrzutów EN i PL, formatowanie i lint przeszły.

## Poprawki GUI 0.2.1 — 2026-11-13

- 48 testów przeszło; osobny test GPU/ONNX pozostaje opt-in.
- Klikanie rzeczywistych strzałek QStyle zwiększa i zmniejsza rozmiar pędzla,
  szerokość, wysokość, kroki, CFG i strength. Wysokokontrastowe SVG dla wszystkich
  spinboxów oraz list rozwijanych, także w oknach dialogowych.
- Rozdzielczość jest w jednym wierszu formularza, z podpisem po lewej i polami
  obok siebie. Kontrola EN/PL przy 1440×900 i 1000×680, bez przewijania poziomego.
- Informacyjne etykiety dobierają wysokość do całego zawiniętego tekstu.
- Strength jest edytowalny również w text-to-image, aby można go było ustawić
  z wyprzedzeniem. Sampler txt2img nadal używa 1.0; edycja używa wpisanej wartości.
- Obejrzano zrzut pełnego panelu z polami i nieuciętymi informacjami.

## Nowe rodziny 0.3 — 2026-11-13

- 89 testów przeszło; 2 testy GPU są opt-in. Ruff: bez błędów.
- Osobno test schematów w przypiętym ComfyUI na V100: 30 grafów dla sześciu
  nowych wariantów, w tym cztery tryby, referencje i lokalny upsampler FLUX.3.
  Sprawdzono rzeczywiste nazwy/typy wejść, połączenia, rozmiary latentów oraz
  wykonanie ReferenceLatent na małych tensorach. Test nie ładuje trenowanych wag.
- Domyślne parametry, zapis/odczyt profili, aktywacja pól, wymagane komponenty,
  rozdzielenie enkodera i upsamplera, natywne harmonogramy FLUX/Krea oraz LoRA
  referencji Krea są objęte testami aplikacji.
- Pełna generacja FLUX.3, Z-Image i Krea 2 pozostaje niezweryfikowana: brak
  kompletnego zestawu wag lokalnie. Części pobierania FLUX.3 pozostały nietknięte.
  Nie pobierano modeli ani nie aktualizowano silnika, sterownika i zależności.

Test schematów (bez trenowanych wag):
```bash
PAINT_TES_GPU_TESTS=1 QT_QPA_PLATFORM=offscreen ../.venv/bin/python -m pytest -q tests/test_engine_schemas_optional.py
```
