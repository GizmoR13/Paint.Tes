"""Local ONNX foreground segmentation. No model downloads or model repositories."""

from __future__ import annotations

import argparse
from pathlib import Path

from .i18n import tr


def remove_background(source: Path, target: Path, model: Path, size: int, normalization: str):
    from .hardware import require_volta

    require_volta()
    import numpy as np
    import onnxruntime as ort
    from PIL import Image

    from .imageops import load_image

    if not model.is_file() or model.suffix.lower() != ".onnx":
        raise ValueError(tr("Wybierz lokalny model segmentacji .onnx w ustawieniach."))
    if size not in (320, 512, 1024):
        raise ValueError(tr("Rozmiar wejściowy modelu segmentacji: 320, 512 lub 1024."))
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError(tr("ONNX Runtime nie ma backendu CUDA. Uruchom setup.sh."))
    session = ort.InferenceSession(
        str(model), providers=[("CUDAExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"]
    )
    if "CUDAExecutionProvider" not in session.get_providers():
        raise RuntimeError(tr("Nie udało się uruchomić segmentacji na V100."))
    image = load_image(source)
    array = (
        np.asarray(
            image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32
        )
        / 255.0
    )
    if normalization == "u2net":
        array = array / max(float(array.max()), 1e-8)
    array = (array - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
        [0.229, 0.224, 0.225], dtype=np.float32
    )
    tensor = array.transpose(2, 0, 1)[None].astype(np.float32)
    output = np.asarray(session.run(None, {session.get_inputs()[0].name: tensor})[0]).squeeze()
    if output.ndim != 2:
        raise ValueError(
            tr(
                "Model nie zwrócił pojedynczej maski. Obsługiwane: U2Net/ISNet/BiRefNet z wejściem RGB NCHW i maską N1HW."
            )
        )
    if normalization == "birefnet":
        output = 1.0 / (1.0 + np.exp(-np.clip(output, -60, 60)))
    else:
        low, high = float(output.min()), float(output.max())
        output = (output - low) / max(high - low, 1e-8)
    alpha = Image.fromarray((np.clip(output, 0, 1) * 255).astype(np.uint8)).resize(
        image.size, Image.Resampling.LANCZOS
    )
    old = np.asarray(image.getchannel("A"), dtype=np.float32) / 255
    image.putalpha(Image.fromarray((np.asarray(alpha) * old).astype(np.uint8)))
    image.save(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--normalization", default="u2net")
    args = parser.parse_args()
    remove_background(args.source, args.target, args.model, args.size, args.normalization)


if __name__ == "__main__":
    main()
