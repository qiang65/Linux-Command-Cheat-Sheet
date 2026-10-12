#!/usr/bin/env bash
# Linux 手册 启动脚本
set -e
cd "$(dirname "$(readlink -f "$0")")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "需要 python3" >&2; exit 1
fi
if ! python3 -c "import PyQt5.QtWidgets" >/dev/null 2>&1; then
    echo "缺少 PyQt5，请先安装：sudo apt install python3-pyqt5" >&2; exit 1
fi

exec python3 app.py "$@"
