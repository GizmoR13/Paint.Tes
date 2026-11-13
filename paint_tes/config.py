from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from .i18n import tr

FAMILIES = {
    "sd15": "Stable Diffusion 1.5",
    "sdxl": "SDXL",
    "qwen21": "Qwen-Image 2.1",
    "moss": "MOSS-Image",
}


def config_path() -> Path:
    # Retain the legacy directory so upgrades keep existing profiles and preferences.
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "Paint.Tes"
        / "settings.json"
    )


def data_path() -> Path:
    override = os.environ.get("PAINT_TES_DATA")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "Paint.Tes"


@dataclass
class ModelProfile:
    name: str = field(default_factory=lambda: tr("Nowy model"))
    family: str = "sdxl"
    checkpoint: str = ""
    diffusion: str = ""
    encoder: str = ""
    vae: str = ""
    lora: str = ""
    lora_strength: float = 1.0
    shift: float = 3.0
    id: str = field(default_factory=lambda: uuid4().hex)

    def validate(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(tr("Nieznana rodzina modelu."))
        required = (
            ("checkpoint",) if self.family in ("sd15", "sdxl") else ("diffusion", "encoder", "vae")
        )
        for key in (*required, *(["lora"] if self.lora else [])):
            path = Path(getattr(self, key)).expanduser()
            if not getattr(self, key) or not path.is_file():
                raise ValueError(
                    tr("Brak lokalnego pliku ({0}): {1}").format(
                        key, getattr(self, key) or tr("nie wybrano")
                    )
                )
            if path.suffix.lower() != ".safetensors":
                raise ValueError(
                    tr(
                        "Wybierz wagi .safetensors. GGUF i katalogi Diffusers wymagają innego loadera i nie są obsługiwane w tej wersji."
                    )
                )
        if not self.name.strip():
            raise ValueError(tr("Podaj nazwę profilu."))


@dataclass
class Settings:
    model_roots: list[str] = field(default_factory=list)
    output_dir: str = str(Path.home() / "Pictures" / "Paint.TES")
    gpu_uuid: str = ""
    precision: str = "safe"
    offload: str = "lowvram"
    background_model: str = ""
    background_size: int = 320
    background_normalization: str = "u2net"
    profiles: list[ModelProfile] = field(default_factory=list)
    active_profile: str = ""
    undo_limit: int = 20
    language: str = "en"

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or config_path()
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        data["profiles"] = [ModelProfile(**p) for p in data.get("profiles", [])]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))
        temp.replace(path)


def scan_models(roots: list[str]) -> list[Path]:
    """Discover local safe tensor weights; never download or inspect pickle files."""
    found: set[Path] = set()
    for root in roots:
        path = Path(root).expanduser()
        if path.is_dir():
            found.update(p for p in path.rglob("*.safetensors") if p.is_file())
    return sorted(found, key=lambda p: str(p).lower())
