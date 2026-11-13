import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("PAINT_TES_GPU_TESTS") != "1", reason="optional Volta engine schema test"
)
def test_real_engine_node_schemas():
    from paint_tes.hardware import list_gpus

    gpus = list_gpus()
    if not gpus:
        pytest.skip("no Volta GPU")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpus[0]["uuid"]
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/engine_schema_probe.py")],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (result.stdout + "\n" + result.stderr)[-8000:]
    assert "PASS: 30 real ComfyUI graphs" in result.stdout
