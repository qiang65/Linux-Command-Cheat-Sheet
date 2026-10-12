#!/usr/bin/env bash
# 安装桌面启动图标（当前用户，无需 root）
set -e
APPDIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$APPS" "$ICONS"

cp -f "$APPDIR/assets/icon.svg" "$ICONS/linux-handbook.svg"

cat > "$APPS/linux-handbook.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Linux 手册
Name[zh_CN]=Linux 手册
Comment=Linux 命令速查表 / Shell 教程 / 参考手册（离线单机）
Exec="$APPDIR/launcher.sh"
Icon=linux-handbook
Terminal=false
Categories=Utility;Development;
Keywords=linux;command;shell;manual;cheatsheet;
StartupNotify=true
EOF
chmod +x "$APPDIR/launcher.sh"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" || true
echo "已安装启动图标："
echo "  $APPS/linux-handbook.desktop"
echo "卸载：rm '$APPS/linux-handbook.desktop' '$ICONS/linux-handbook.svg'"
