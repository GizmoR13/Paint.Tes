"""Private ComfyUI process, guarded before any model can be loaded."""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path

from .i18n import tr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--paths", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--precision", choices=("safe", "fp16"), default="safe")
    parser.add_argument("--offload", choices=("lowvram", "normalvram"), default="lowvram")
    args = parser.parse_args()
    from .hardware import require_volta

    torch = require_volta()
    root = Path(__file__).resolve().parents[1] / "engine" / "ComfyUI"
    if not (root / "main.py").is_file():
        raise RuntimeError(tr("Brakuje silnika. Uruchom git submodule update --init --recursive."))
    data = Path(args.data)
    for name in ("input", "output", "temp", "user"):
        (data / name).mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root))
    sys.argv = [
        str(root / "main.py"),
        "--listen",
        "127.0.0.1",
        "--port",
        args.port,
        "--disable-auto-launch",
        "--disable-all-custom-nodes",
        "--offline",
        "--disable-assets",
        "--disable-dynamic-vram",
        "--use-pytorch-cross-attention",
        "--preview-method",
        "none",
        "--extra-model-paths-config",
        args.paths,
        "--input-directory",
        str(data / "input"),
        "--output-directory",
        str(data / "output"),
        "--temp-directory",
        str(data / "temp"),
        "--user-directory",
        str(data / "user"),
        "--" + args.offload,
        "--fp32-vae",
        "--fp32-text-enc",
        "--force-fp32" if args.precision == "safe" else "--force-fp16",
    ]
    import comfy.options

    comfy.options.enable_args_parsing()
    import comfy.model_management as memory
    import nodes

    # The legacy LOW_VRAM policy otherwise chooses CPU for text encoding.
    # Keep GPU execution with ordinary ModelPatcher offloading on Volta.
    memory.text_encoder_device = memory.get_torch_device

    class EmptyQwen21:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {
                    "width": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 16}),
                    "height": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 16}),
                    "batch_size": ("INT", {"default": 1, "min": 1, "max": 1}),
                }
            }

        RETURN_TYPES = ("LATENT",)
        FUNCTION = "create"
        CATEGORY = "Paint.TES"

        def create(self, width, height, batch_size=1):
            import comfy.model_management

            latent = torch.zeros(
                (batch_size, 64, height // 16, width // 16),
                device=comfy.model_management.intermediate_device(),
            )
            return ({"samples": latent},)

    nodes.NODE_CLASS_MAPPINGS["PaintTesEmptyQwen21Latent"] = EmptyQwen21
    os.chdir(root)
    runpy.run_path(str(root / "main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
