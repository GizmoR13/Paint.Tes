from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from .i18n import tr


@dataclass(frozen=True)
class FamilyInfo:
    label: str
    clip_type: str = ""
    latent_node: str = "EmptyLatentImage"
    flow_shift: float | None = None
    steps: int = 25
    cfg: float = 7.0
    scheduler: str = "normal"
    independent_reference: bool = False
    reference_lora: bool = False
    hint: str = ""

    @property
    def separate(self):
        return bool(self.clip_type)

    @property
    def flux3(self):
        return self.clip_type == "flux3"


FAMILY_INFO = {
    "sd15": FamilyInfo("Stable Diffusion 1.5"),
    "sdxl": FamilyInfo("SDXL"),
    "qwen21": FamilyInfo(
        "Qwen-Image 2.1", "qwen_image", "PaintTesEmptyQwen21Latent", 3.0, 20, 4, "simple", True
    ),
    "moss": FamilyInfo("MOSS-Image", "moss_image", "EmptyFlux2LatentImage", 5.0, 20, 4, "simple"),
    "flux3": FamilyInfo(
        "FLUX.3 Image Klein",
        "flux3",
        "EmptyFlux2LatentImage",
        None,
        16,
        1,
        "simple",
        True,
        hint="FLUX.3: Qwen3-VL-4B text encoder + Flux2 VAE. The optional Qwen3.5-9B prompt upsampler is a separate model, not the text encoder. Use a detailed scene caption or enable local prompt expansion.",
    ),
    "flux3_base": FamilyInfo(
        "FLUX.3 Image Klein Base",
        "flux3",
        "EmptyFlux2LatentImage",
        None,
        50,
        3.5,
        "simple",
        True,
        hint="FLUX.3 Base: Qwen3-VL-4B text encoder + Flux2 VAE. Use base weights, not the distilled checkpoint. Prompt expansion is optional and needs its own local model.",
    ),
    "zimage": FamilyInfo(
        "Z-Image",
        "lumina2",
        "EmptySD3LatentImage",
        3.0,
        28,
        4,
        "simple",
        hint="Z-Image: Qwen3-4B text encoder (not Qwen3-VL) + the matching Flux/ae.safetensors VAE. Select the base or Turbo family to get the matching sampling defaults.",
    ),
    "zimage_turbo": FamilyInfo(
        "Z-Image Turbo",
        "lumina2",
        "EmptySD3LatentImage",
        3.0,
        8,
        1,
        "simple",
        hint="Z-Image Turbo: Qwen3-4B text encoder + Flux/ae.safetensors VAE. Start with 8 steps and CFG 1; negative conditioning is unused at CFG 1.",
    ),
    "krea2": FamilyInfo(
        "Krea 2 Raw",
        "krea2",
        "EmptySD3LatentImage",
        None,
        52,
        3.5,
        "simple",
        True,
        True,
        hint="Krea 2 Raw: Qwen3-VL-4B text encoder + Qwen-Image VAE (not the Qwen-Image 2.1 VAE). A separate style reference requires the matching style-reference LoRA.",
    ),
    "krea2_turbo": FamilyInfo(
        "Krea 2 Turbo",
        "krea2",
        "EmptySD3LatentImage",
        None,
        8,
        1,
        "simple",
        True,
        True,
        hint="Krea 2 Turbo: Qwen3-VL-4B text encoder + Qwen-Image VAE. Start with 8 steps and CFG 1. A separate style reference needs a compatible style-reference LoRA.",
    ),
}
FAMILIES = {key: info.label for key, info in FAMILY_INFO.items()}


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
    prompt_upsampler: str = ""
    upsample_prompt: bool = False
    lora_strength: float = 1.0
    shift: float = 3.0
    id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def info(self) -> FamilyInfo:
        if self.family not in FAMILY_INFO:
            raise ValueError(tr("Nieznana rodzina modelu."))
        return FAMILY_INFO[self.family]

    def validate(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(tr("Nieznana rodzina modelu."))
        required = (
            ("checkpoint",) if self.family in ("sd15", "sdxl") else ("diffusion", "encoder", "vae")
        )
        extra = ["lora"] if self.lora else []
        if self.info.flux3 and self.upsample_prompt:
            extra.append("prompt_upsampler")
        for key in (*required, *extra):
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
