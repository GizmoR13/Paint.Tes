from __future__ import annotations

import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import requests
import yaml
from PIL import Image

from .config import ModelProfile, Settings, data_path
from .hardware import list_gpus
from .i18n import tr
from .imageops import composite_edit, padded_for_engine
from .workflow import Generation, build_workflow


class Cancelled(Exception):
    pass


class EngineClient:
    def __init__(self, root: Path | None = None):
        self.root = root or data_path() / "engine"
        self.process = None
        self.url = ""
        self.signature = None
        self.log_handle = None
        self.cancel_event = threading.Event()
        self.prompt_id = None
        self.http = requests.Session()
        self.http.trust_env = False  # Private loopback API must never use an HTTP proxy.

    def stop(self):
        process = self.process
        self.process = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None
        self.url = ""
        self.signature = None

    def cancel(self):
        self.cancel_event.set()
        # This endpoint belongs only to the process launched by this instance.
        if self.url and self.process and self.process.poll() is None and self.prompt_id:
            try:
                self.http.post(self.url + "/queue", json={"delete": [self.prompt_id]}, timeout=3)
                self.http.post(
                    self.url + "/interrupt", json={"prompt_id": self.prompt_id}, timeout=3
                )
            except requests.RequestException:
                pass

    def register_models(self, profile: ModelProfile):
        profile.validate()
        keys = {
            "checkpoint": "checkpoints",
            "diffusion": "diffusion_models",
            "encoder": "text_encoders",
            "vae": "vae",
            "lora": "loras",
        }
        names = {}
        folders = {}
        for key, category in keys.items():
            folder = self.root / "models" / category
            folder.mkdir(parents=True, exist_ok=True)
            folders[category] = str(folder)
            value = getattr(profile, key)
            if value:
                path = Path(value).expanduser().resolve(strict=True)
                name = hashlib.sha256(str(path).encode()).hexdigest()[:16] + "-" + path.name
                link = folder / name
                if not link.exists():
                    link.symlink_to(path)
                names[key] = name
        paths_file = self.root / "model-paths.yaml"
        paths_file.write_text(yaml.safe_dump({"paint_tes": folders}))
        return names, paths_file

    def ensure_server(self, settings: Settings, paths_file, report):
        gpu = settings.gpu_uuid
        available = list_gpus()
        if not gpu and available:
            gpu = available[0]["uuid"]
        if not gpu or gpu not in {g["uuid"] for g in available}:
            raise ValueError(tr("W ustawieniach wybierz dostępną V100/V100S/TITAN V."))
        signature = (gpu, settings.precision, settings.offload)
        if self.process and self.process.poll() is None and signature == self.signature:
            return
        self.stop()
        self.root.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env.update(
            CUDA_VISIBLE_DEVICES=gpu,
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            DO_NOT_TRACK="1",
            SDNQ_USE_TORCH_COMPILE="0",
            SDNQ_USE_TRITON_MM="0",
            PYTHONUNBUFFERED="1",
        )
        self.log_handle = (self.root / "engine.log").open("w")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "paint_tes.worker",
                "--port",
                str(port),
                "--paths",
                str(paths_file),
                "--data",
                str(self.root),
                "--precision",
                settings.precision,
                "--offload",
                settings.offload,
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
        )
        self.url = f"http://127.0.0.1:{port}"
        self.signature = signature
        report(tr("Uruchamianie lokalnego silnika V100…"))
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.cancel_event.is_set():
                self.stop()
                raise Cancelled(tr("Anulowano uruchamianie silnika."))
            if self.process.poll() is not None:
                tail = (self.root / "engine.log").read_text(errors="replace")[-3500:]
                self.stop()
                raise RuntimeError(tr("Nie udało się uruchomić silnika.\n") + tail)
            try:
                self.http.get(self.url + "/system_stats", timeout=2).raise_for_status()
                return
            except requests.RequestException:
                self.cancel_event.wait(0.3)
        self.stop()
        raise TimeoutError(
            tr("Silnik nie uruchomił się w ciągu 180 s. Sprawdź dziennik w ustawieniach.")
        )

    def upload(self, image: Image.Image, prefix):
        data = io.BytesIO()
        image.save(data, format="PNG")
        name = f"{prefix}-{uuid4().hex}.png"
        response = self.http.post(
            self.url + "/upload/image",
            files={"image": (name, data.getvalue(), "image/png")},
            data={"type": "input", "overwrite": "false"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        subfolder = payload.get("subfolder", "")
        return f"{subfolder}/{payload['name']}" if subfolder else payload["name"]

    def generate(
        self,
        settings: Settings,
        profile: ModelProfile,
        request: Generation,
        image=None,
        mask=None,
        reference=None,
        report=lambda _: None,
    ):
        self.prompt_id = None
        names, paths_file = self.register_models(profile)
        if settings.precision == "fp16" and profile.family in ("qwen21", "moss"):
            raise ValueError(
                tr(
                    "Qwen/MOSS wymaga trybu bezpiecznego FP32 na V100. Zmień precyzję w ustawieniach."
                )
            )
        self.ensure_server(settings, paths_file, report)
        source_size = image.size if image else (request.width, request.height)
        original = image.copy() if image else None
        original_mask = mask.copy() if mask else None
        image_name = mask_name = ref_name = None
        try:
            if image:
                padded, padded_mask = padded_for_engine(image, mask)
                image_name = self.upload(padded.convert("RGB"), "source")
                mask_name = self.upload(padded_mask.convert("RGB"), "mask") if padded_mask else None
                request = replace(request, width=padded.width, height=padded.height)
            if reference:
                ref_name = self.upload(reference.convert("RGB"), "reference")
            graph = build_workflow(
                profile,
                request,
                names,
                image_name,
                mask_name,
                ref_name,
                output_prefix="PaintTES-" + uuid4().hex,
            )
            if self.cancel_event.is_set():
                raise Cancelled(tr("Anulowano."))
            response = self.http.post(
                self.url + "/prompt", json={"prompt": graph, "client_id": uuid4().hex}, timeout=30
            )
            if not response.ok:
                raise RuntimeError(
                    tr("Silnik odrzucił konfigurację modelu:\n") + response.text[:3000]
                )
            self.prompt_id = response.json()["prompt_id"]
            report(tr("Generowanie… pierwsze ładowanie dużego modelu może potrwać kilka minut."))
            while True:
                if self.cancel_event.wait(0.5):
                    self.cancel()
                    # Terminate our worker, so the next task never races with a cancelled prompt.
                    self.stop()
                    raise Cancelled(tr("Anulowano generowanie."))
                if self.process.poll() is not None:
                    raise RuntimeError(
                        tr("Silnik zakończył pracę. Możliwy brak RAM/VRAM; sprawdź dziennik.")
                    )
                result = self.http.get(self.url + "/history/" + self.prompt_id, timeout=10)
                result.raise_for_status()
                entry = result.json().get(self.prompt_id)
                if not entry:
                    continue
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(
                        tr("Błąd generacji:\n")
                        + json.dumps(status.get("messages", []), ensure_ascii=False)[-3500:]
                    )
                for output in entry.get("outputs", {}).values():
                    for item in output.get("images", []):
                        response = self.http.get(
                            self.url + "/view",
                            params={
                                k: item[k] for k in ("filename", "subfolder", "type") if k in item
                            },
                            timeout=30,
                        )
                        response.raise_for_status()
                        generated = (
                            Image.open(io.BytesIO(response.content))
                            .convert("RGBA")
                            .crop((0, 0, *source_size))
                        )
                        if original is not None and original_mask is not None:
                            generated = composite_edit(original, generated, original_mask)
                        output_path = (
                            self.root / "output" / item.get("subfolder", "") / item["filename"]
                        ).resolve()
                        if (
                            output_path.is_relative_to((self.root / "output").resolve())
                            and output_path.is_file()
                        ):
                            output_path.unlink()
                        return generated
                if status.get("completed"):
                    raise RuntimeError(tr("Silnik zakończył zadanie bez obrazu."))
        finally:
            self.prompt_id = None
            # Only remove the uniquely named uploads created for this job.
            for name in (image_name, mask_name, ref_name):
                if name:
                    path = self.root / "input" / name
                    if path.is_file():
                        path.unlink()
