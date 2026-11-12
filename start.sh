#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
paint_env="${PAINT_TES_VENV:-$(pwd)/../.venv}"
if [ ! -x "$paint_env/bin/python" ]; then
    echo 'Run ./setup.sh first.' >&2
    exit 1
fi
qt_runtime="${PAINT_TES_QT_RUNTIME:-$(pwd)/../qt-runtime}"
if [ -d "$qt_runtime/usr/lib/x86_64-linux-gnu" ]; then
    export LD_LIBRARY_PATH="$qt_runtime/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
# Qt must use its own plugin directory, not plugins exported by another app.
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH
exec "$paint_env/bin/python" -m paint_tes "$@"
