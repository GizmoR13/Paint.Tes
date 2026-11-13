# Paint.TES — user guide

## Language

English is the default. Choose **Settings → General → Language → Polski** for
Polish, or **English** to switch back. The change applies immediately and is
saved for the next launch. Your prompts, tab names and model profile names are
not translated.

## Local models and GPU

Choose a V100/V100S/TITAN V by UUID in Settings. Add a local model profile:

- SD 1.5 / SDXL: a complete base `.safetensors` checkpoint.
- Qwen-Image 2.1 / MOSS: matching diffusion weights, text encoder and VAE.
- Background removal: a local U2Net/ISNet/BiRefNet ONNX model, configured separately.

Model folders help you find weights; files are not moved or copied. The engine
uses links to selected files and never downloads models. Use safe FP32 for
Qwen/MOSS; FP16 is optional for SD/SDXL. Start at a modest image size. The first
load takes longer, and large models can exceed available RAM/VRAM.

## Toolbar and selection

The top and left toolbars use icons. Hover over a button for its name and
shortcut. New, Open, Save, Undo, Redo, Fit, Actual size and Settings are on top.
The left toolbar provides Pan, Rectangle, Ellipse, Lasso, Polygon, Brush and
Eraser. Double-click to close a polygon.

The gold overlay marks the region to edit. Ctrl+D deselects, Ctrl+I inverts,
and Delete clears selected pixels to transparency. Brush and Eraser respect
an active mask. Use Selection → Feather edges to soften a mask.

## New image / text to image

Ctrl+N opens the size, background, local model, steps, CFG, seed and prompt
dialog. Check generation after creation, or use the AI panel. Generation sizes
must be multiples of 16. Ctrl+Enter runs generation. Results open in new tabs.

## Seed and denoising strength

Seed is a single-line integer field supporting **0 through 9223372036854775807**.
Leave it empty for a fresh random seed for every task. The last submitted seed
is shown below the controls. **Reuse last seed** copies it into the field.
With the same model, image, prompt and settings, a fixed seed repeats the result.
Changing other settings can change the image even when the seed is fixed.

**Denoising strength** applies to image-to-image, inpaint and outpaint. It is
disabled for text-to-image, which always uses full noise (1.0). A smaller value
keeps more of the source; a larger one permits a stronger change. Both decimal
points and commas are accepted (for example `0.35` or `0,35`). With very few
sampling steps, changes are discrete. PNG metadata includes the actual seed
and denoising strength.

## Editing and reference tabs

For image-to-image, open the source and choose that mode. For inpaint, select an
area first. Pixels with a zero mask are restored from the original after
decoding. For outpaint, choose the margins in the dialog; the original area is
preserved, including its alpha channel.

Image → Use as reference marks a tab. Switch to a different tab and select it
in Reference tab. Qwen receives a separate reference along with the editing
source. For SD/SDXL/MOSS, a reference tab can be used as the image-to-image
source; independent conditioning references are not supported for these models.

## Background removal

Select a local ONNX model and its matching input size in Settings → Background
removal. The model must accept RGB float32 NCHW and return one N1HW mask. Choose
U2Net/ISNet for probability masks, or BiRefNet for logits. Typical sizes are 320
for U2Net and 1024 for ISNet/BiRefNet. No weights are downloaded automatically.
The result opens in a new RGBA tab; save as PNG or WebP to retain transparency.

## Saving, memory and cancellation

Ctrl+S saves the active tab; Ctrl+Shift+S saves under a new name. Save generated
results before closing. The editor asks about unsaved tabs. Undo is limited by
both step count and 256 MiB of history per tab.

Ctrl+0 fits the image, Ctrl+1 shows actual size, and Ctrl+mouse wheel zooms.
Single-letter tool shortcuts apply while the canvas has focus.

Cancel task interrupts Paint.TES's own engine process. The next task restarts
it. AI → Release engine memory stops that process without closing documents.
Other applications and LLM servers are not stopped.

For upgrade compatibility, the existing `Paint.Tes` configuration/data directory
names are retained. Local workstation data remains under `/mnt/AI/data/paint-tes`;
its engine log is `engine/engine.log`. The application is now displayed as
**Paint.TES** in the window and Ubuntu application menu.
