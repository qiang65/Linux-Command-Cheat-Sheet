#!/usr/bin/env python3
"""在真实 X11 环境下渲染各界面并截图（用于检查/展示界面效果）。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
SHOTS = os.path.join(ROOT, ".shots")
os.makedirs(SHOTS, exist_ok=True)

from PyQt5.QtWidgets import QApplication                                    # noqa: E402
from db import Store                                                       # noqa: E402
from main_window import MainWindow, GroupHeader                                         # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "shots.db")
if os.path.exists(db):
    os.remove(db)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))

win = MainWindow(store, ROOT)
win.resize(1320, 860)
win.show()
app.processEvents()


def shot(name):
    app.processEvents()
    p = os.path.join(SHOTS, name + ".png")
    win.grab().save(p, "PNG")
    print("shot:", name)


# 1. 浅色：《Docker 命令》9 组收起 + 展开两组
win.show_category("docker")
win.top.set_tab("docker")
win.expanded.clear()
win.rebuild_list()
heads = win.listInner.findChildren(GroupHeader)
heads[0].clicked.emit()
heads[6].clicked.emit()
app.processEvents()
win.show_entry([e for e in store.entries("docker") if e["name"] == "run"][0]["id"],
               record=False)
shot("live-1-docker")

# 2. 深色：设置页（分类管理 + 删除记录）
store.to_trash(store.entries("cheatsheet", "gzip")[0]["id"])
store.add_category_named("Docker 速查")
store.add_category_named("网络排查")
win.reload_all()
win.toggle_theme()
win.show_category("settings")
app.processEvents()
shot("live-2-settings-dark")

# 3. 浅色：设置页（拖拽排序后 tabBar 已同步）
win.toggle_theme()
win.show_category("settings")
app.processEvents()
cl = win.settings_page.catList
it = cl.takeItem(0)
cl.insertItem(3, it)          # 首行拖到第 4 位
app.processEvents()           # 信号自动写库
win.reload_all()
app.processEvents()
shot("live-3-settings-light")

# 4. 深色：命令大全词条详情（语法 / 参数 / 实例）
win.toggle_theme()
win.show_category("commmanual")
win.top.set_tab("commmanual")
win.show_entry(store.entries("commmanual", "chmod")[0]["id"], record=False)
shot("live-4-comm-detail")

# 5. 深色：Shell 变量详情（正文完整：表格 + 多个代码卡）
win.show_category("shell")
win.top.set_tab("shell")
win.show_entry([e for e in store.entries("shell") if e["name"] == "Shell 变量"][0]["id"],
               record=False)
shot("live-5-shell-detail")
win.toggle_theme()

store.close()
print("done")
