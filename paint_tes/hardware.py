from __future__ import annotations

import csv
import io
import subprocess

from .i18n import tr


def list_gpus() -> list[dict]:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,uuid,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    gpus = []
    for row in csv.reader(io.StringIO(proc.stdout)):
        if len(row) == 3:
            name, uuid, free = (v.strip() for v in row)
            if "V100" in name.upper() or "TITAN V" in name.upper():
                gpus.append({"name": name, "uuid": uuid, "free": int(free)})
    return sorted(gpus, key=lambda item: item["free"], reverse=True)


def require_volta():
    import os

    import torch

    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").startswith("GPU-"):
        raise RuntimeError(tr("Wybierz V100 według UUID w ustawieniach Paint.TES."))
    if not torch.cuda.is_available() or torch.version.hip:
        raise RuntimeError(tr("Brak dostępnej karty NVIDIA CUDA."))
    if torch.cuda.device_count() != 1 or torch.cuda.get_device_capability() != (7, 0):
        raise RuntimeError(
            tr("Paint.TES obsługuje V100/V100S/TITAN V (Volta sm_70), jedną kartę na zadanie.")
        )
    if (
        not torch.version.cuda
        or int(torch.version.cuda.split(".")[0]) != 12
        or "sm_70" not in torch.cuda.get_arch_list()
    ):
        raise RuntimeError(tr("Środowisko wymaga PyTorch CUDA 12.x z obsługą sm_70."))
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_math_sdp(True)
    return torch
