"""Validate real ComfyUI nodes without downloading/loading trained model weights."""

# ruff: noqa: E402 -- engine flags and paths must precede ComfyUI imports

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
from paint_tes.hardware import require_volta

torch = require_volta()
root = APP_ROOT / "engine/ComfyUI"
sys.path.insert(0, str(root))
sys.argv = [
    str(root / "main.py"),
    "--disable-dynamic-vram",
    "--force-fp32",
    "--use-pytorch-cross-attention",
    "--disable-all-custom-nodes",
    "--offline",
    "--disable-assets",
]
import comfy.options

comfy.options.enable_args_parsing()
import folder_paths
import nodes

from paint_tes.config import ModelProfile
from paint_tes.engine import EngineClient
from paint_tes.workflow import Generation, build_workflow


async def main():
    import execution
    import server
    from app.assets.manager import default_asset_manager
    from PIL import Image
    from safetensors.torch import save_file

    server.PromptServer(asyncio.get_running_loop(), default_asset_manager())
    await nodes.init_extra_nodes(init_custom_nodes=False, init_api_nodes=False)
    with tempfile.TemporaryDirectory(prefix="paint-tes-model-schemas-") as directory:
        temp = Path(directory)
        folder_paths.set_input_directory(str(temp))
        folder_paths.set_output_directory(str(temp))
        for name in ["source.png", "mask.png", "ref.png"]:
            Image.new("RGB", (128, 128), "white").save(temp / name)
        weights = temp / "schema-only.safetensors"
        save_file({"schema_only": torch.zeros(1)}, weights)
        families = ["flux3", "flux3_base", "zimage", "zimage_turbo", "krea2", "krea2_turbo"]
        count = 0

        async def validate(family, mode="txt2img", reference=False, upsample=False):
            nonlocal count
            profile = ModelProfile(
                family=family,
                diffusion=str(weights),
                encoder=str(weights),
                vae=str(weights),
                lora=str(weights) if family.startswith("krea2") and reference else "",
                prompt_upsampler=str(weights) if upsample else "",
                upsample_prompt=upsample,
            )
            client = EngineClient(temp / "registry")
            names, _ = client.register_models(profile)
            for category in ["checkpoints", "diffusion_models", "text_encoders", "vae", "loras"]:
                folder_paths.add_model_folder_path(category, str(client.root / "models" / category))
            graph = build_workflow(
                profile,
                Generation(mode=mode, width=128, height=128),
                names,
                image="source.png" if mode != "txt2img" else None,
                mask="mask.png" if mode in ("inpaint", "outpaint") else None,
                reference="ref.png" if reference else None,
            )
            result = await execution.validate_prompt(uuid4().hex, graph, None)
            assert result[0], (family, mode, reference, upsample, result)
            count += 1

        for family in families:
            for mode in ["txt2img", "img2img", "inpaint", "outpaint"]:
                await validate(family, mode)
            if family.startswith(("flux3", "krea2")):
                await validate(family, "inpaint", reference=True)
            if family.startswith("flux3"):
                await validate(family, "img2img", reference=True, upsample=True)
        from comfy_extras.nodes_flux import EmptyFlux2LatentImage
        from comfy_extras.nodes_sd3 import EmptySD3LatentImage

        assert EmptyFlux2LatentImage.execute(128, 128, 1)[0]["samples"].shape == (1, 128, 8, 8)
        assert EmptySD3LatentImage.execute(128, 128, 1)[0]["samples"].shape == (1, 16, 16, 16)
        # Also run the real reference-conditioning node on tiny tensors.
        from comfy_extras.nodes_edit_model import ReferenceLatent

        conditioning = [[torch.zeros((1, 2, 4)), {}]]
        latent = {"samples": torch.zeros((1, 16, 16, 16))}
        result = ReferenceLatent.execute(conditioning, latent)[0]
        assert len(result[0][1]["reference_latents"]) == 1
        print(
            f"PASS: {count} real ComfyUI graphs; exact latent shapes and reference conditioning; no trained weights loaded.",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
