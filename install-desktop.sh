#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
paint_repo="$(pwd)"
"${PAINT_TES_VENV:-$paint_repo/../.venv}/bin/python" - "$paint_repo" <<'PY'
import os,sys
from pathlib import Path
root=Path(sys.argv[1])
# Quote Desktop Entry arguments, including paths with spaces or shell metacharacters.
def quote(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
applications=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'applications'
applications.mkdir(parents=True,exist_ok=True)
entry=applications/'paint-tes.desktop'
data_env=os.environ.get('PAINT_TES_DATA','')
prefix='env '+quote('PAINT_TES_DATA='+data_env)+' ' if data_env else ''
entry.write_text('[Desktop Entry]\nType=Application\nName=Paint.Tes\nComment=Local image editor for NVIDIA Volta\nExec='+prefix+quote(root/'start.sh')+' %F\nIcon='+str(root/'resources/paint-tes.svg')+'\nTerminal=false\nCategories=Graphics;RasterGraphics;\nMimeType=image/png;image/jpeg;image/webp;\nStartupWMClass=Paint.Tes\n')
print(entry)
PY
