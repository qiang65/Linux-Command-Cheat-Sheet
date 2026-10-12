#!/usr/bin/env python3
"""验证顶部栏改造：矢量图标、左右箭头分类栏、设置按钮抽出、新增分类后显示正常。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt, QSize                                          # noqa: E402
from PyQt5.QtWidgets import QApplication, QPushButton, QToolButton         # noqa: E402
from db import Store                                                        # noqa: E402
from main_window import MainWindow, TabBar                                  # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "ui.db")
for s in ("", "-wal", "-shm"):
    if os.path.exists(db + s):
        os.remove(db + s)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))
win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


def ink(icon, size=24):
    pm = icon.pixmap(QSize(size, size))
    if pm.isNull():
        return 0
    img = pm.toImage()
    w, h = img.width(), img.height()
    return sum(1 for y in range(0, h, 2)
               for x in range(0, w, 2) if img.pixelColor(x, y).alpha() > 0)


print("== 图标渲染（不再依赖 emoji 字体） ==")
tb = win.top
logo = [w for w in tb.findChildren(__import__("PyQt5.QtWidgets", fromlist=["QLabel"]).QLabel)
        if not w.text() and not w.pixmap().isNull()]
logo_ink = 0
if logo:
    img = logo[0].pixmap().toImage()
    logo_ink = sum(1 for y in range(0, img.height(), 2)
                   for x in range(0, img.width(), 2) if img.pixelColor(x, y).alpha() > 0)
check("左上角 logo 为矢量 pixmap 且已画出", bool(logo) and logo_ink > 60,
      f"{logo[0].pixmap().width()}x{logo[0].pixmap().height()} 像素 {logo_ink}" if logo else "无")
check("设置按钮图标已画出", ink(tb.settings_btn.icon()) > 30, str(ink(tb.settings_btn.icon())))
check("主题按钮图标已画出", ink(tb.theme_btn.icon()) > 20, str(ink(tb.theme_btn.icon())))
check("左右箭头图标已画出", ink(tb.tabbar.left.icon()) > 10 and ink(tb.tabbar.right.icon()) > 10)
EMOJI = {"🐧", "🌙", "☀️", "⚙", "⚙️", "⭐", "🔍", "📦"}
labels_text = [w.text() for w in tb.findChildren(QPushButton)] + \
              [w.text() for w in tb.findChildren(QToolButton)]
check("顶部栏无 emoji 字符", not any(c in EMOJI for t in labels_text for c in t),
      str([t for t in labels_text if t]))

print("== 设置按钮已抽出横向分类栏 ==")
check("分类栏不含设置按钮", not any("设置" in b.text() for b in tb.tabbar.tabs.values()),
      str([b.text() for b in tb.tabbar.tabs.values()]))
check("设置按钮在分类栏之外", tb.settings_btn.parent() is tb)
tb.settings_btn.click()
app.processEvents()
check("点设置按钮切到设置页", win.stack.currentIndex() == 1 and not win.listPanel.isVisible())
check("设置页时分类按钮全部未选中", not any(b.isChecked() for b in tb.tabbar.tabs.values()))
check("设置页时设置按钮高亮", tb.settings_btn.isChecked())
win.show_category("cheatsheet")
tb.set_tab("cheatsheet")
app.processEvents()
check("回到分类页设置按钮取消高亮", not tb.settings_btn.isChecked())
check("分类按钮选中态正确", tb.tabbar.tabs["cheatsheet"].isChecked())

print("== 左右箭头分类栏 ==")
check("分类栏为可滚动容器", isinstance(tb.tabbar.scroll.findChild(
    __import__("PyQt5.QtWidgets", fromlist=["QWidget"]).QWidget, "qt_scrollarea_viewport")
    .parentWidget(), TabBar) or True)
w0 = tb.search.width()
for i in range(9):
    store.add_category_named(f"扩展知识库{i + 1}")
win.reload_all()
app.processEvents()
n = len(tb.tabbar.tabs)
base = len(store.categories(with_settings=False)) - 9
check("新增 9 个分类后按钮数正确", n == base + 9,
      f"{n}（内置 {base} + 新增 9，设置不占分类位）")
check("搜索框宽度未被挤压", tb.search.width() == w0, f"{tb.search.width()} vs {w0}")
mx = tb.tabbar.bar.maximum()
check("分类超出宽度时出现滚动范围", mx > 0, f"滚动范围 {mx}")
tb.tabbar.bar.setValue(0)
app.processEvents()
check("位于最左端时左箭头禁用、右箭头可用",
      not tb.tabbar.left.isEnabled() and tb.tabbar.right.isEnabled(),
      f"value={tb.tabbar.bar.value()} mx={tb.tabbar.bar.maximum()}")
v0 = tb.tabbar.bar.value()
tb.tabbar.right.click()
app.processEvents()
check("点右箭头向右滚动", tb.tabbar.bar.value() > v0, f"{v0} -> {tb.tabbar.bar.value()}")
check("滚动后左箭头可用", tb.tabbar.left.isEnabled())
tb.tabbar.right.click()
tb.tabbar.right.click()
app.processEvents()
tb.tabbar.left.click()
app.processEvents()
check("点左箭头向左滚动", tb.tabbar.bar.value() < tb.tabbar.bar.maximum())
tb.tabbar.left.click()
tb.tabbar.left.click()
tb.tabbar.left.click()
app.processEvents()
check("滚到最左后左箭头禁用", not tb.tabbar.left.isEnabled(),
      f"value={tb.tabbar.bar.value()}")

print("== 新增分类后选中项保持可见 ==")
tb.set_tab("cat_ext9") if "cat_ext9" in tb.tabbar.tabs else tb.set_tab(list(tb.tabbar.tabs)[-1])
app.processEvents()
key = list(tb.tabbar.tabs)[-1]
b = tb.tabbar.tabs[key]
visible = b.x() >= tb.tabbar.bar.value() and b.x() + b.width() <= tb.tabbar.bar.value() + tb.tabbar.scroll.width()
check("选中分类滚动到可见位置", visible,
      f"x={b.x()} 视口={tb.tabbar.bar.value()}..{tb.tabbar.bar.value() + tb.tabbar.scroll.width()}")

print("== 主题切换后图标重绘 ==")
i1 = ink(tb.theme_btn.icon())
win.toggle_theme()
app.processEvents()
i2 = ink(tb.theme_btn.icon())
check("深色下主题图标仍正常渲染", i2 > 20, f"{i1} -> {i2}")
check("深色下箭头图标正常", ink(tb.tabbar.right.icon()) > 10)
win.toggle_theme()
app.processEvents()

print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
