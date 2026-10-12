#!/usr/bin/env python3
"""离屏冒烟测试：跑通主流程并截图，用于检查界面效果。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
SHOTS = os.path.join(ROOT, ".shots")
os.makedirs(SHOTS, exist_ok=True)

from PyQt5.QtWidgets import QApplication                                # noqa: E402
from db import Store                                                   # noqa: E402
from main_window import MainWindow                                      # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "smoke.db")
if os.path.exists(db):
    os.remove(db)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))

win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
app.processEvents()


def shot(name):
    app.processEvents()
    p = os.path.join(SHOTS, name + ".png")
    win.grab().save(p)
    print("shot:", name)


shot("01-cheatsheet-empty")

# 打开一个命令词条
ents = store.entries("cheatsheet", "rm")
win.show_entry(ents[0]["id"], record=False)
shot("02-entry-rm")

# 教程词条（长正文 + 代码块）
shell = store.entries("shell", "变量")
win.show_category("shell")
win.top.set_tab("shell")
win.show_entry(shell[0]["id"], record=False)
shot("03-shell-variable")

# 深色主题
win.toggle_theme()
shot("04-dark-shell")

win.show_category("manual")
win.top.set_tab("manual")
man = store.entries("manual", "目录")
win.show_entry(man[0]["id"], record=False)
shot("05-dark-manual")
win.toggle_theme()

# 搜索
win.show_category("cheatsheet")
win.top.set_tab("cheatsheet")
win.top.search.setText("端口")
shot("06-search")
win.top.search.clear()

# 设置页
win.show_category("settings")
win.top.set_tab("settings")
shot("07-settings")

# 编辑对话框
from editor import EntryDialog                                          # noqa: E402
eid = store.entries("cheatsheet", "ls")[0]["id"]
dlg = EntryDialog(store, "cheatsheet", win.pal, win, entry_id=eid)
dlg.show()
app.processEvents()
dlg.grab().save(os.path.join(SHOTS, "08-editor.png"))
print("shot: 08-editor")
dlg.close()

# 收藏 + 只看收藏
win.show_category("cheatsheet")
win.on_fav(eid)
win.favBtn.setChecked(True)
win.rebuild_list()
shot("09-fav-only")

print("\nstats:", store.stats())
store.close()
print("OK")
