# Local model families — Paint.TES 0.3

In **Settings → Local models → Add**, choose the exact family and select existing
local `.safetensors` files for diffusion, text encoder and VAE. Save the profile,
then select it in AI Studio. Changing profiles sets the defaults below; you can
adjust them before generation. All new families use Euler / simple initially.

| Family | Text encoder | VAE | Steps | CFG |
|---|---|---|---:|---:|
| FLUX.3 Image Klein | Qwen3-VL-4B for FLUX.3 | Flux2 | 16 | 1 |
| FLUX.3 Image Klein Base | Qwen3-VL-4B for FLUX.3 | Flux2 | 50 | 3.5 |
| Z-Image | Qwen3-4B, not VL | Flux `ae.safetensors` | 28 | 4 |
| Z-Image Turbo | Qwen3-4B, not VL | Flux `ae.safetensors` | 8 | 1 |
| Krea 2 Raw | Qwen3-VL-4B for Krea 2 | original Qwen-Image, not 2.1 | 52 | 3.5 |
| Krea 2 Turbo | Qwen3-VL-4B for Krea 2 | original Qwen-Image, not 2.1 | 8 | 1 |

Use components intended for the chosen family. Similar names do not guarantee
compatibility. Use ComfyUI-native weights or supported quantizations with ComfyUI
metadata; raw GGUF, SDNQ, generic GPTQ, Diffusers directories and unfinished
`.part-*` downloads are not accepted. The app never downloads or merges weights.

FLUX.3 accepts an independent reference tab as well as the editing source.
A detailed scene caption can be entered directly. To expand a short prompt locally,
select the separate **Qwen3.5-9B FLUX.3 prompt upsampler** and enable **Expand prompt
locally before generation** in the profile. It is optional, uses additional memory
and time, and does not replace the regular Qwen3-VL-4B text encoder. Expansion is
deterministic; the image seed controls diffusion rather than prompt rewriting.

Krea 2 independent style references need the compatible **style-reference LoRA**
selected in the profile. Without it, set Reference tab to None. Ordinary image to
image, masked inpaint and outpaint use the source image as an initial latent;
these generic editing modes do not require a dedicated inpaint checkpoint.
Z-Image reference tabs can be used as the image-to-image source.

On V100, select **safe FP32** precision. FLUX.3 and Krea keep their native sampling
schedules; Z-Image uses flow shift 3 by default. At CFG 1 negative conditioning
has no guidance effect. In text-to-image denoising is always 1; strength applies
to editing. VRAM/RAM requirements depend on the exact weights and resolution.

## Polski

**Ustawienia → Modele lokalne → Dodaj**: wybierz właściwą rodzinę oraz trzy lokalne
pliki: diffusion, enkoder tekstu i VAE. Zapisz profil i wybierz go w panelu AI.
Tabela powyżej podaje komponenty i domyślne parametry. Wybór profilu ustawia kroki,
CFG i scheduler; można je później zmienić. Dla V100 pozostaw bezpieczne FP32.

FLUX.3: opcjonalny lokalny upsampler Qwen3.5-9B rozszerza prompt, ale nie zastępuje
enkodera Qwen3-VL-4B. Włącz go dopiero po wskazaniu kompletnego modelu. Krea 2:
niezależna referencja stylu wymaga zgodnej LoRA style-reference. W Z-Image używaj
enkodera Qwen3-4B bez VL. VAE Qwen-Image 2.1 nie jest VAE dla Krea 2.
Części pobieranych plików pozostaw downloaderowi. Program sam nie pobiera wag.

## Upstream model instructions

- [FLUX.3 ComfyUI components](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy)
- [FLUX.3 usage](https://comfy.org/flux-3-image-klein)
- [Z-Image base](https://huggingface.co/Tongyi-MAI/Z-Image)
- [Z-Image Turbo components](https://huggingface.co/Comfy-Org/Z-Image-Turbo)
- [Krea 2 components](https://huggingface.co/Comfy-Org/Krea-2)
- [Krea 2 Raw](https://huggingface.co/krea/Krea-2-Raw)

See [validation](VALIDATION.md) for the distinction between graph/schema checks
and generation with trained weights.
