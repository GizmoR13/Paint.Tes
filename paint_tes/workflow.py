"""Build local ComfyUI execution graphs from editor requests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .config import ModelProfile
from .i18n import tr
from .imageops import validate_size


@dataclass
class Generation:
    mode: str = "txt2img"
    prompt: str = ""
    negative: str = ""
    width: int = 512
    height: int = 512
    steps: int = 25
    cfg: float = 7.0
    seed: int = 0
    strength: float = 0.65
    sampler: str = "euler"
    scheduler: str = "normal"

    def validate(self):
        validate_size(self.width, self.height)
        if self.mode not in ("txt2img", "img2img", "inpaint", "outpaint"):
            raise ValueError(tr("Nieznany tryb generacji."))
        if not 1 <= self.steps <= 150 or not 0 <= self.cfg <= 30 or not 0.01 <= self.strength <= 1:
            raise ValueError(tr("Nieprawidłowe parametry generacji."))
        if not 0 <= self.seed < 2**63:
            raise ValueError(tr("Seed poza zakresem."))


def build_workflow(
    profile: ModelProfile,
    request: Generation,
    names: dict,
    image=None,
    mask=None,
    reference=None,
    output_prefix=None,
):
    request.validate()
    if request.width % 16 or request.height % 16:
        raise ValueError(tr("Wymiary przekazane silnikowi muszą być wielokrotnością 16."))
    if request.mode != "txt2img" and not image:
        raise ValueError(tr("Ten tryb wymaga obrazu źródłowego."))
    if request.mode in ("inpaint", "outpaint") and not mask:
        raise ValueError(tr("Inpaint/outpaint wymaga maski."))
    info = profile.info
    if reference and not info.independent_reference:
        raise ValueError(
            tr(
                "Ta rodzina nie ma niezależnej referencji. Wybierz image-to-image lub ustaw referencję na Brak."
            )
        )
    if reference and info.reference_lora and not profile.lora:
        raise ValueError(
            tr(
                "Referencja Krea 2 wymaga zgodnej LoRA style-reference. Wybierz ją w profilu albo ustaw referencję na Brak."
            )
        )
    graph = {}

    def node(kind, **inputs):
        key = str(len(graph) + 1)
        graph[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    def output(ref, index):
        return [ref[0], index]

    if profile.family in ("sd15", "sdxl"):
        model = node("CheckpointLoaderSimple", ckpt_name=names["checkpoint"])
        clip, vae = output(model, 1), output(model, 2)
    else:
        model = node("UNETLoader", unet_name=names["diffusion"], weight_dtype="default")
        clip = node(
            "CLIPLoader",
            clip_name=names["encoder"],
            type=info.clip_type,
            device="default",
        )
        vae = node("VAELoader", vae_name=names["vae"])
        if info.flow_shift is not None:
            model = node("ModelSamplingAuraFlow", model=model, shift=profile.shift)
        # FLUX.3 / Krea 2 keep their native exponential-flow schedules.

    if profile.lora:
        if info.reference_lora:
            model = node(
                "LoraLoaderModelOnly",
                model=model,
                lora_name=names["lora"],
                strength_model=profile.lora_strength,
            )
        else:
            model = node(
                "LoraLoader",
                model=model,
                clip=clip,
                lora_name=names["lora"],
                strength_model=profile.lora_strength,
                strength_clip=profile.lora_strength,
            )
            clip = output(model, 1)

    source_pixels = node("LoadImage", image=image) if image else None
    prompt = request.prompt
    if info.flux3 and profile.upsample_prompt:
        if not names.get("prompt_upsampler"):
            raise ValueError(
                tr(
                    "Wybierz lokalny model prompt upsamplera FLUX.3 lub wyłącz rozszerzanie promptu."
                )
            )
        upsampler = node(
            "CLIPLoader", clip_name=names["prompt_upsampler"], type="flux3", device="default"
        )
        inputs = dict(
            clip=upsampler,
            prompt=request.prompt,
            max_length=1024,
            sampling_mode="off",
            thinking=False,
            use_default_template=True,
            mtp="off",
            system_prompt="Rewrite the request as a detailed, coherent English still-image scene caption. Preserve all requested subjects, counts, relationships, exact text, visual style and edit instructions. Do not add unrelated objects. Return only the scene description, without headings or markdown.",
        )
        if source_pixels:
            inputs["image"] = source_pixels
        prompt = node("TextGenerate", **inputs)
    if profile.family == "qwen21":
        inputs = {
            "clip": clip,
            "prompt": request.prompt,
            "negative_prompt": request.negative,
            "vae": vae,
            "resolution": 0,
        }
        if source_pixels:
            inputs["images.image_1"] = source_pixels
        if reference:
            inputs["images.image_2" if source_pixels else "images.image_1"] = node(
                "LoadImage", image=reference
            )
        encoding = node("TextEncodeQwenImage21", **inputs)
        positive, negative = encoding, output(encoding, 1)
        # Never use reference dimensions for the requested output canvas.
        latent = node(
            "PaintTesEmptyQwen21Latent", width=request.width, height=request.height, batch_size=1
        )
    else:
        positive = node("CLIPTextEncode", clip=clip, text=prompt)
        negative = node("CLIPTextEncode", clip=clip, text=request.negative)
        latent = node(
            info.latent_node,
            width=request.width,
            height=request.height,
            batch_size=1,
        )
    if image:
        latent = node("VAEEncode", pixels=source_pixels, vae=vae)
        if info.flux3:
            positive = node("ReferenceLatent", conditioning=positive, latent=latent)
            negative = node("ReferenceLatent", conditioning=negative, latent=latent)
        if mask:
            mask_image = node("LoadImage", image=mask)
            mask_ref = node("ImageToMask", image=mask_image, channel="red")
            latent = node("SetLatentNoiseMask", samples=latent, mask=mask_ref)
    if reference and info.independent_reference and profile.family != "qwen21":
        ref_pixels = node("LoadImage", image=reference)
        ref_latent = node("VAEEncode", pixels=ref_pixels, vae=vae)
        positive = node("ReferenceLatent", conditioning=positive, latent=ref_latent)
        negative = node("ReferenceLatent", conditioning=negative, latent=ref_latent)
        if info.reference_lora:
            positive = node(
                "FluxKontextMultiReferenceLatentMethod",
                conditioning=positive,
                reference_latents_method="index_timestep_zero",
            )
            negative = node(
                "FluxKontextMultiReferenceLatentMethod",
                conditioning=negative,
                reference_latents_method="index_timestep_zero",
            )
            model = node(
                "ModelSamplingFlux",
                model=model,
                max_shift=1.15,
                base_shift=0.5,
                width=request.width,
                height=request.height,
            )
    samples = node(
        "KSampler",
        model=model,
        positive=positive,
        negative=negative,
        latent_image=latent,
        seed=request.seed,
        steps=request.steps,
        cfg=request.cfg,
        sampler_name=request.sampler,
        scheduler=request.scheduler,
        denoise=1.0 if request.mode == "txt2img" else request.strength,
    )
    pixels = node("VAEDecode", samples=samples, vae=vae)
    node("SaveImage", images=pixels, filename_prefix=output_prefix or "PaintTES-" + uuid4().hex)
    return graph
