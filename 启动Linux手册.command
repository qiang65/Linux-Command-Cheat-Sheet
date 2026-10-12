#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$APP_DIR/.venv-macos"
cd "$APP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "需要先安装 Python 3。"
    read -r -p "按回车键退出..."
    exit 1
fi

if [[ ! -x "$VENV/bin/python" ]]; then
    python3 -m venv "$VENV"
fi

if ! "$VENV/bin/python" -c "import PyQt5.QtWidgets" >/dev/null 2>&1; then
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install -r requirements.txt
fi

exec "$VENV/bin/python" "$APP_DIR/app.py" "$@"