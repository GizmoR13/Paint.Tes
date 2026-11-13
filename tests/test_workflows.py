import pytest

from paint_tes.config import FAMILY_INFO, ModelProfile, Settings
from paint_tes.workflow import Generation, build_workflow


@pytest.mark.parametrize("family", list(FAMILY_INFO))
@pytest.mark.parametrize("mode", ["txt2img", "img2img", "inpaint", "outpaint"])
def test_graphs_for_all_modes_and_families(family, mode):
    request = Generation(mode=mode, width=512, height=512, seed=1)
    names = {key: key + ".safetensors" for key in ["checkpoint", "diffusion", "encoder", "vae"]}
    graph = build_workflow(
        ModelProfile(family=family),
        request,
        names,
        image="source.png" if mode != "txt2img" else None,
        mask="mask.png" if mode in ("inpaint", "outpaint") else None,
    )
    sampler = next(node for node in graph.values() if node["class_type"] == "KSampler")
    assert sampler["inputs"]["denoise"] == (1 if mode == "txt2img" else request.strength)
    if mode in ("inpaint", "outpaint"):
        assert any(node["class_type"] == "SetLatentNoiseMask" for node in graph.values())
    for node in graph.values():
        for value in node["inputs"].values():
            if isinstance(value, list):
                assert value[0] in graph


def test_qwen_reference_is_separate_and_output_size_independent():
    request = Generation(width=768, height=512)
    graph = build_workflow(
        ModelProfile(family="qwen21"),
        request,
        {"diffusion": "a", "encoder": "b", "vae": "c"},
        reference="ref.png",
    )
    encoder = next(node for node in graph.values() if node["class_type"] == "TextEncodeQwenImage21")
    assert encoder["inputs"]["images.image_1"]
    latent = next(
        node for node in graph.values() if node["class_type"] == "PaintTesEmptyQwen21Latent"
    )
    assert latent["inputs"]["width"] == 768
    assert latent["inputs"]["height"] == 512


def test_rejects_invalid_masks_references_and_dimensions():
    profile = ModelProfile(family="sdxl")
    with pytest.raises(ValueError):
        build_workflow(profile, Generation(mode="inpaint"), {"checkpoint": "a"})
    with pytest.raises(ValueError):
        build_workflow(profile, Generation(), {"checkpoint": "a"}, reference="ref.png")
    with pytest.raises(ValueError):
        build_workflow(profile, Generation(width=513), {"checkpoint": "a"})


def test_settings_roundtrip_and_local_paths(tmp_path):
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"not-loaded-in-policy-test")
    profile = ModelProfile(name="My SDXL", checkpoint=str(weights))
    profile.validate()
    settings = Settings(model_roots=[str(tmp_path)], profiles=[profile], gpu_uuid="GPU-test")
    path = tmp_path / "settings.json"
    settings.save(path)
    restored = Settings.load(path)
    assert restored.profiles[0] == profile
    assert restored.gpu_uuid == "GPU-test"
    profile.checkpoint = "https://example.org/model.safetensors"
    with pytest.raises(ValueError):
        profile.validate()


def test_qwen_edit_sees_both_source_and_independent_reference():
    request = Generation(mode="inpaint", width=512, height=512)
    graph = build_workflow(
        ModelProfile(family="qwen21"),
        request,
        {"diffusion": "a", "encoder": "b", "vae": "c"},
        image="source.png",
        mask="mask.png",
        reference="ref.png",
    )
    encoder = next(n for n in graph.values() if n["class_type"] == "TextEncodeQwenImage21")
    assert encoder["inputs"]["images.image_1"] != encoder["inputs"]["images.image_2"]
    source = graph[encoder["inputs"]["images.image_1"][0]]
    assert source["inputs"]["image"] == "source.png"


def test_repeated_fixed_seed_has_fresh_save_node():
    profile = ModelProfile(family="sdxl")
    request = Generation(seed=42)
    first = build_workflow(profile, request, {"checkpoint": "local.safetensors"})
    second = build_workflow(profile, request, {"checkpoint": "local.safetensors"})
    saves = [
        next(n for n in graph.values() if n["class_type"] == "SaveImage")
        for graph in (first, second)
    ]
    samplers = [
        next(n for n in graph.values() if n["class_type"] == "KSampler")
        for graph in (first, second)
    ]
    assert samplers[0] == samplers[1]
    assert saves[0]["inputs"]["filename_prefix"] != saves[1]["inputs"]["filename_prefix"]
