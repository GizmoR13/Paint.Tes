# Paint.TES — instrukcja

## Język i paski narzędzi

Domyślny język to angielski. W **Settings → General → Language** wybierz
**Polski**. Zmiana działa od razu i zostaje zapisana. Przyciski górnego i lewego
paska mają ikony; nazwy i skróty pojawiają się po najechaniu kursorem.

Seed to teraz jednoliniowe pole liczbowe (0–9223372036854775807). Puste pole
losuje seed dla każdego zadania. Ostatnio wysłany seed jest widoczny obok
przycisku ponownego użycia. Siła zmiany działa w image-to-image, inpaint i
outpaint. Pole można ustawiać w każdym trybie; text-to-image pomija tę wartość i zawsze używa 1.0. Możesz wpisać kropkę lub przecinek,
np. `0.35` albo `0,35`. Przy małej liczbie kroków efekty zmieniają się skokowo.

## Pierwszy start

1. Otwórz **Ustawienia → Ogólne**. Wybierz V100 według UUID, katalog zapisu i
   katalogi do przeszukiwania modeli. Wybierz bezpieczny FP32 i oszczędzanie VRAM.
2. W **Modele lokalne** dodaj profil, wybierz rodzinę i lokalne pliki wag.
   Przyciski `…` otwierają okno wyboru pliku; niczego nie pobierają.
3. Wybierz profil w panelu **Studio AI**. Zacznij od rozdzielczości 512×512 lub
   mniejszej i krótkiego zadania. Duże Qwen/MOSS mogą zużywać dużo RAM i VRAM.

Katalogi modeli służą do ich odnajdywania; nie są przenoszone ani kopiowane.
Silnik tworzy jedynie dowiązania do wybranych plików we własnym katalogu danych.
Nie zamykaj innych aplikacji automatycznie — Paint.Tes nigdy ich nie zatrzymuje.

## Nowy obraz i text to image

**Plik → Nowy obraz** (`Ctrl+N`) otwiera okno nazwy, rozmiaru, tła, modelu,
liczby kroków, CFG, seeda i promptu. Zaznacz generowanie po utworzeniu, jeśli
chcesz od razu uruchomić model. Puste pole seed oznacza losowy seed.
Wymiary generowania muszą być wielokrotnością 16. Puste płótno może mieć dowolny
obsługiwany rozmiar (od 16 px).

Możesz też wpisać prompt w panelu AI, wybrać **Text to image**, rozmiar i kliknąć
**Generuj obraz** (`Ctrl+Enter`). Wynik pojawi się w nowej karcie.

## Karty i referencje

Otwieraj wiele obrazów przez `Ctrl+O` albo wklejaj ze schowka jako nowe karty.
W menu **Obraz → Użyj jako referencji** oznacz obraz, następnie przejdź do innej
karty. Pole **Karta referencji** wybierze oznaczoną kartę.

- **Qwen-Image 2.1** dostaje tę kartę jako niezależną referencję. Przy edycji
  aktywna karta nadal jest źródłem do przekształcenia.
- **SD/SDXL/MOSS**: w trybie **Image to image** wybrana karta referencji staje
  się źródłem. W pozostałych trybach ustaw `Brak`; niezależne referencje nie są
  udawane przez mieszanie obrazów.

## Inpaint

1. Wybierz kartę źródłową.
2. Zaznacz obszar prostokątem, elipsą, lassem lub wielokątem (dwuklik zamyka).
3. Opcjonalnie zmiękcz maskę: **Zaznaczenie → Zmiękcz krawędzie**.
4. Wybierz **Inpaint**, opisz zmianę i ustaw siłę zmiany.
5. Generuj. Wynik powstanie w nowej karcie. Piksele z zerową maską są przywracane
   z oryginału po dekodowaniu, więc nie zmienią się przy okazji edycji.

Złote podświetlenie wskazuje maskę edycji, a nie część obrazu do zachowania.
`Ctrl+D` usuwa maskę; `Ctrl+I` odwraca ją; `Delete` czyści zaznaczone piksele do
przezroczystości. Pędzel i gumka także respektują aktywną maskę.

## Outpaint

Wybierz **Outpaint**, prompt i **Generuj**. W oknie marginesów określ, ile pikseli
dodać z każdej strony. Nowe marginesy tworzą maskę; oryginalny obszar zachowuje
piksele i przezroczystość. Poza maską program nie dokonuje retuszu.

## Image to image

Aktywna karta jest źródłem. Siła zmiany określa udział szumu: mniejsza lepiej
zachowuje strukturę, większa daje modelowi większą swobodę. W razie potrzeby
użyj innej karty w polu referencji zgodnie z zasadami powyżej.

## Usuwanie tła

W **Ustawienia → Usuwanie tła** wskaż własny plik `.onnx` i jego typ:
U2Net/ISNet (maska prawdopodobieństwa) albo BiRefNet (logits). Model musi mieć
wejście RGB float32 NCHW i pojedynczą maskę N1HW. Rozmiar wejścia musi odpowiadać
modelowi (typowo 320 dla U2Net, 1024 dla ISNet/BiRefNet).

Naciśnij **Usuń tło** dla aktywnej karty. Nowa karta ma kanał alfa; zapisz ją jako
PNG albo WebP, aby zachować przezroczystość. JPEG spłaszcza obraz na białym tle.

## Zapis i cofanie

`Ctrl+S` zapisuje bieżącą kartę. PNG przechowuje parametry ostatniej generacji.
Wyniki silnika są plikami roboczymi i po odebraniu trafiają do pamięci karty;
**zapisz wynik przed zamknięciem aplikacji**. Przy zamykaniu niezapisanego obrazu
program pyta o zapis. Cofanie ma limit liczby zmian oraz 256 MiB historii na kartę.

`Ctrl+0` dopasowuje obraz; `Ctrl+1` ustawia 100%; `Ctrl+kółko myszy` zmienia zoom.
Skróty H/S/E/L/P/B/R działają dla narzędzi, gdy płótno ma fokus. W polach tekstowych
można normalnie pisać.

## Pamięć, anulowanie i logi

**Anuluj zadanie** przerywa własny proces silnika podczas generacji. Następne
zadanie uruchomi go ponownie. **AI → Zwolnij pamięć silnika** wyłącza własny
proces, zachowując dokumenty. Zamknięcie Paint.Tes również go zatrzymuje.

Konfiguracja: `~/.config/Paint.Tes/settings.json` (lub XDG_CONFIG_HOME).
Dane: `~/.local/share/Paint.Tes` (lub PAINT_TES_DATA). Lokalna instalacja na tej
stacji używa `/mnt/AI/data/paint-tes`. Dziennik: `engine/engine.log` wewnątrz danych.

Jeżeli model zgłasza nieobsługiwany typ wag, wybierz wariant zgodny z dołączonym
silnikiem. Nie aktualizuj automatycznie PyTorch do CUDA 13; V100 wymaga sm_70.
