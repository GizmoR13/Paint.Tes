"""Opt-in runtime checks: PAINT_TES_GPU_TESTS=1 selects a single V100 by UUID."""

import os
import subprocess
import sys

import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(
    os.environ.get("PAINT_TES_GPU_TESTS") != "1", reason="optional V100 integration test"
)


def test_local_onnx_segmentation_transport(tmp_path):
    import onnx
    from onnx import TensorProto, helper

    from paint_tes.hardware import list_gpus

    gpus = list_gpus()
    if not gpus:
        pytest.skip("no Volta GPU")
    # A tiny synthetic RGB->mask graph tests loading, GPU providers, resizing,
    # alpha preservation and output transport, not trained segmentation quality.
    node = helper.make_node("ReduceMean", ["input"], ["mask"], axes=[1], keepdims=1)
    graph = helper.make_graph(
        [node],
        "mask-test",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, 320, 320])],
        [helper.make_tensor_value_info("mask", TensorProto.FLOAT, [1, 1, 320, 320])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    path = tmp_path / "test.onnx"
    onnx.save(model, path)
    source = tmp_path / "source.png"
    target = tmp_path / "target.png"
    image = Image.new("RGBA", (64, 64), (20, 40, 60, 128))
    image.paste((220, 220, 220, 255), (16, 16, 48, 48))
    image.save(source)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpus[0]["uuid"]
    subprocess.run(
        [sys.executable, "-m", "paint_tes.background", str(source), str(target), str(path)],
        env=env,
        check=True,
        timeout=90,
    )
    output = Image.open(target)
    assert output.size == (64, 64)
    assert output.mode == "RGBA"
    assert output.getpixel((0, 0))[3] <= 128
    assert output.getpixel((32, 32))[3] > 200
