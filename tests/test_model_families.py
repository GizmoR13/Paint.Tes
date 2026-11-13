import pytest
from test_ui_update import clean_close, make_window

from paint_tes.config import FAMILY_INFO, ModelProfile, Settings
from paint_tes.dialogs import SettingsDialog
from paint_tes.engine import EngineClient
from paint_tes.workflow import Generation, build_workflow

NEW_FAMILIES = ["flux3", "flux3_base", "zimage", "zimage_turbo", "krea2", "krea2_turbo"]
NAMES = {
    name: name + ".safetensors"
    for name in ["diffusion", "encoder", "vae", "lora", "prompt_upsampler"]
}


@pytest.mark.parametrize(
    "family,clip,latent,shift",
    [
        ("flux3", "flux3", "EmptyFlux2LatentImage", False),
        ("flux3_base", "flux3", "EmptyFlux2LatentImage", False),
        ("zimage", "lumina2", "EmptySD3LatentImage", True),
        ("zimage_turbo", "lumina2", "EmptySD3LatentImage", True),
        ("krea2", "krea2", "EmptySD3LatentImage", False),
        ("krea2_turbo", "krea2", "EmptySD3LatentImage", False),
    ],
)
def test_loader_latent_and_native_schedules(family, clip, latent, shift):
    graph = build_workflow(ModelProfile(family=family), Generation(), NAMES)
    kinds = [n["class_type"] for n in graph.values()]
    loader = next(n for n in graph.values() if n["class_type"] == "CLIPLoader")
    assert loader["inputs"]["type"] == clip
    assert latent in kinds
    assert ("ModelSamplingAuraFlow" in kinds) == shift


@pytest.mark.parametrize("family", ["flux3", "flux3_base"])
def test_flux_source_reference_and_prompt_expansion(family):
    profile = ModelProfile(family=family, upsample_prompt=True)
    graph = build_workflow(
        profile, Generation(mode="img2img"), NAMES, image="source.png", reference="reference.png"
    )
    assert sum(n["class_type"] == "ReferenceLatent" for n in graph.values()) == 4
    generator = next((key, n) for key, n in graph.items() if n["class_type"] == "TextGenerate")
    positive = next(
        n
        for n in graph.values()
        if n["class_type"] == "CLIPTextEncode" and n["inputs"]["text"] == [generator[0], 0]
    )
    assert positive
    assert generator[1]["inputs"]["sampling_mode"] == "off"
    assert generator[1]["inputs"]["image"]
    no_up = build_workflow(ModelProfile(family=family), Generation(), NAMES)
    assert not any(n["class_type"] == "TextGenerate" for n in no_up.values())


@pytest.mark.parametrize("family", ["krea2", "krea2_turbo"])
def test_krea_style_reference_needs_adapter_and_method(family):
    with pytest.raises(ValueError):
        build_workflow(ModelProfile(family=family), Generation(), NAMES, reference="ref.png")
    graph = build_workflow(
        ModelProfile(family=family, lora="style.safetensors"),
        Generation(),
        NAMES,
        reference="ref.png",
    )
    assert any(n["class_type"] == "LoraLoaderModelOnly" for n in graph.values())
    methods = [
        n for n in graph.values() if n["class_type"] == "FluxKontextMultiReferenceLatentMethod"
    ]
    assert len(methods) == 2
    assert all(n["inputs"]["reference_latents_method"] == "index_timestep_zero" for n in methods)
    assert any(n["class_type"] == "ModelSamplingFlux" for n in graph.values())


def test_optional_component_registration_and_legacy_settings(tmp_path):
    path = tmp_path / "weights.safetensors"
    path.write_bytes(b"not-loaded")
    client = EngineClient(tmp_path / "engine")
    profile = ModelProfile(
        family="flux3",
        diffusion=str(path),
        encoder=str(path),
        vae=str(path),
        prompt_upsampler="/missing/unused.safetensors",
    )
    names, _ = client.register_models(profile)
    assert "prompt_upsampler" not in names
    profile.upsample_prompt = True
    with pytest.raises(ValueError):
        profile.validate()
    profile.prompt_upsampler = str(path)
    names, _ = client.register_models(profile)
    assert "prompt_upsampler" in names
    settings = Settings(profiles=[profile])
    settings.save(tmp_path / "settings.json")
    assert Settings.load(tmp_path / "settings.json").profiles[0].upsample_prompt
    assert Settings.load(tmp_path / "settings.json").profiles[0].prompt_upsampler == str(path)


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_family_profiles_and_defaults_in_gui(qtbot, tmp_path, monkeypatch, family):
    window = make_window(qtbot, tmp_path, monkeypatch)
    info = FAMILY_INFO[family]
    profile = ModelProfile(name=info.label, family=family)
    window.settings.profiles = [profile]
    window.refresh_profiles()
    assert window.steps.value() == info.steps
    assert window.cfg.value() == info.cfg
    dialog = SettingsDialog(window, window.settings)
    qtbot.addWidget(dialog)
    assert dialog.family.currentData() == family
    assert dialog.fields["encoder"].isEnabled()
    assert not dialog.fields["checkpoint"].isEnabled()
    assert dialog.shift.isEnabled() == (info.flow_shift is not None)
    assert dialog.upsample_prompt.isEnabled() == info.flux3
    dialog.reject()
    clean_close(window)
