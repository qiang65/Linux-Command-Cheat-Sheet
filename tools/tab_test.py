#!/usr/bin/env python3
"""验证分类按钮互斥高亮，且高亮项与纵向栏内容一致。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt                                                                    # noqa: E402
from PyQt5.QtGui import QKeyEvent                                                              # noqa: E402
from PyQt5.QtWidgets import QApplication, QPushButton                                       # noqa: E402
from db import Store                                                                        # noqa: E402
from main_window import MainWindow, GroupHeader                                            # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "tab.db")
for s in ("", "-wal", "-shm"):
    if os.path.exists(db + s):
        os.remove(db + s)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))
win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
win.show_category("cheatsheet")
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


def lit():
    return [k for k, b in win.top.tabbar.tabs.items() if b.isChecked()]


def cat_name(key):
    return next(c["name"] for c in store.categories() if c["key"] == key)


print("== 只有一个高亮 ==")
check("初始只有当前分类高亮", lit() == ["cheatsheet"], str(lit()))
keys = list(win.top.tabbar.tabs)
for k in keys:
    win.top.tabbar.tabs[k].click()
    app.processEvents()
    check(f"点击「{cat_name(k)}」后仅它高亮", lit() == [k], str(lit()))
    check(f"  纵向栏标题同步为「{cat_name(k)}」",
          win.listTitle.text().strip() == cat_name(k), win.listTitle.text())
    check("  纵向栏显示该分类的分组",
          all(h.name not in ("",) for h in win.listInner.findChildren(GroupHeader))
          and len(win.listInner.findChildren(GroupHeader)) == len(store.groups(k)),
          f"{len(win.listInner.findChildren(GroupHeader))} 组 / 应 {len(store.groups(k))} 组")

print("== 连续点击不累积高亮 ==")
for k in keys:
    win.top.tabbar.tabs[k].click()
    app.processEvents()
check("遍历点击后仍只有一个高亮", len(lit()) == 1, str(lit()))
check("最后点击的项保持高亮", lit() == [keys[-1]], str(lit()))

print("== 键盘切换同样互斥 ==")
for i, k in enumerate(keys[:3], start=1):
    key = Qt.Key_1 + i - 1
    win.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, key, Qt.ControlModifier, chr(key)))
    app.processEvents()
    check(f"Ctrl+{i} 切到「{cat_name(k)}」且高亮一致",
          win.cat == k and lit() == [k] and win.listTitle.text().strip() == cat_name(k),
          f"cat={win.cat} lit={lit()} title={win.listTitle.text()}")

print("== 设置页 ==")
win.top.settings_btn.click()
app.processEvents()
check("设置页时所有分类按钮都不高亮", lit() == [], str(lit()))
check("设置页时设置按钮高亮", win.top.settings_btn.isChecked())
win.top.tabbar.tabs[keys[0]].click()
app.processEvents()
check("从设置页回到分类页仅该分类高亮", lit() == [keys[0]]
      and not win.top.settings_btn.isChecked(), str(lit()))

print("== 分类增删后高亮保持唯一 ==")
store.add_category_named("Docker 速查")
win.reload_all()
app.processEvents()
check("新增分类后仍只有一个高亮", len(lit()) == 1, str(lit()))
check("高亮项就是当前纵向栏分类", lit() == [win.cat], f"lit={lit()} cat={win.cat}")
cid = store.category_id("commmanual")
store.delete_category(cid, keep_in_trash=True)
win.reload_all()
app.processEvents()
check("删除分类后高亮唯一且有效", len(lit()) == 1 and lit()[0] == win.cat,
      f"lit={lit()} cat={win.cat}")
check("被删分类的按钮已消失", "commmanual" not in win.top.tabbar.tabs)

print("== 拖拽排序后高亮跟随 ==")
store.reorder_categories(["shell", "cheatsheet", "manual"])
win.reload_all()
app.processEvents()
check("排序后高亮仍唯一", len(lit()) == 1, str(lit()))
check("排序后高亮对应纵向栏", lit() == [win.cat]
      and win.listTitle.text().strip() == cat_name(win.cat),
      f"lit={lit()} title={win.listTitle.text()}")

print("== 样式区分 ==")
qss_on = win.top.tabbar.tabs[keys[0]].styleSheet()
check("分类按钮无写死颜色（高亮样式由全局 QSS 控制）", not qss_on, qss_on[:40])
b_on = win.top.tabbar.tabs[win.cat]
b_off = win.top.tabbar.tabs[[k for k in keys if k != win.cat][0]]
check("高亮项为 checked、其余为 unchecked",
      b_on.isChecked() and not b_off.isChecked())
check("互斥由代码手动保证（非 autoExclusive，允许全部取消）",
      not b_on.autoExclusive() and not b_off.autoExclusive())

store.close()
print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
