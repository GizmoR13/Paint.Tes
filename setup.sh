#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    echo 'Paint.Tes currently supports Ubuntu-family Linux x86_64.' >&2
    exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
    echo 'Install uv: https://docs.astral.sh/uv/getting-started/installation/' >&2
    exit 1
fi
if [ ! -f engine/ComfyUI/main.py ]; then
    git submodule update --init --recursive
fi
paint_env="${PAINT_TES_VENV:-$(pwd)/../.venv}"
if [ ! -x "$paint_env/bin/python" ]; then uv venv --python 3.12 "$paint_env"; fi
uv pip install --python "$paint_env/bin/python" --index-url https://download.pytorch.org/whl/cu126 'torch==2.11.0' 'torchvision==0.26.0'
uv pip install --python "$paint_env/bin/python" --constraint constraints-v100.txt --constraint constraints-tested.txt -r requirements.txt
uv pip check --python "$paint_env/bin/python"
# Ubuntu's Qt xcb cursor dependency can be installed privately without sudo.
if ! /sbin/ldconfig -p 2>/dev/null | grep 'libxcb-cursor.so.0' >/dev/null; then
    qt_runtime="${PAINT_TES_QT_RUNTIME:-$(pwd)/../qt-runtime}"
    mkdir -p "$qt_runtime/download"
    (
        cd "$qt_runtime/download"
        apt-get download libxcb-cursor0
        for package in libxcb-cursor0_*.deb; do dpkg-deb -x "$package" "$qt_runtime"; done
    )
fi
echo 'Paint.Tes installed. Start with ./start.sh. Models are selected locally in Settings.'
