#!/usr/bin/env python3
"""布局体检：离屏运行，检查关键控件尺寸/数量/可见性，发现布局异常。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt                                                  # noqa: E402
from PyQt5.QtGui import QFontMetrics, QTextDocument                          # noqa: E402
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QPushButton  # noqa: E402
from db import Store                                                   # noqa: E402
from main_window import MainWindow, EntryItem                          # noqa: E402
from markdown_view import CodeCard                                     # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "layout.db")
if os.path.exists(db):
    os.remove(db)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))

win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
app.processEvents()

issues = []


def geom(w):
    r = w.rect()
    return f"{w.__class__.__name__} {r.width()}x{r.height()}"


print("窗口:", geom(win))
print("顶部栏:", geom(win.top), " 左面板:", geom(win.listPanel))
print("列表项数:", sum(1 for w in win.listInner.findChildren(EntryItem)))
print("分组头数:", sum(1 for w in win.listInner.findChildren(QPushButton)
                   if w.property("cls") == "group"))

# 打开长正文词条，检查渲染块
eid = store.entries("shell", "变量")[0]["id"]
win.show_category("shell")
win.show_entry(eid, record=False)
app.processEvents()
cards = win.detailInner.findChildren(CodeCard)
labels = win.detailInner.findChildren(QLabel)
print("\n[Shell 变量 详情] 代码卡片:", len(cards), " 标签:", len(labels))
for c in cards[:4]:
    print("   代码卡片", geom(c), "行数", c.code.count("\n") + 1,
          "视口高", c.view.height())
zero = [c for c in cards if c.height() <= 1 or c.width() < 200]
if zero:
    issues.append(f"{len(zero)} 个代码卡片尺寸异常")
# 切字判定：按字形宽度与控件宽度比较（固定像素阈值会误报短标题）。
# 富文本标签的 text() 返回 HTML 源码，必须先取渲染后的纯文本再量宽度。
def shown_text(l):
    if l.textFormat() == Qt.RichText:
        d = QTextDocument()
        d.setHtml(l.text())
        return d.toPlainText()
    return l.text()


narrow = []
for l in labels:
    t = shown_text(l).strip()
    if not t:
        continue
    longest = max(t.split("\n"), key=lambda x: len(x))
    adv = QFontMetrics(l.font()).horizontalAdvance(longest)
    wrap = l.wordWrap()
    if adv > l.width() + 2 and not wrap and not t.endswith("…"):
        narrow.append(l)
if narrow:
    issues.append(f"{len(narrow)} 个标签文字被切: " +
                  " | ".join(shown_text(l)[:16] for l in narrow[:3]))

# 检查详情卡片宽度是否被挤压
card = win.detailInner.findChild(QFrame, "detailCard")
print("详情卡片:", geom(card) if card else "无")
if card and card.width() < 500:
    issues.append("详情卡片过窄")

# 速查表词条详情
win.show_category("cheatsheet")
cid = store.entries("cheatsheet", "ls")[0]["id"]
win.show_entry(cid, record=False)
app.processEvents()
print("\n[ls 详情] 卡片:", geom(win.detailInner.findChild(QFrame, "detailCard")))
print("状态栏:", win.statusLabel.text())

# 搜索
win.top.search.setText("端口")
app.processEvents()
n = sum(1 for w in win.listInner.findChildren(EntryItem))
print("\n搜索「端口」列表项:", n, "|", win.statusLabel.text())
win.top.search.clear()
app.processEvents()
print("清空后列表项:", sum(1 for w in win.listInner.findChildren(EntryItem)))

# 设置页
win.show_category("settings")
app.processEvents()
print("\n设置页可见:", win.settings_page.isVisible(),
      " 左面板隐藏:", not win.listPanel.isVisible(),
      " 统计:", win.settings_page.statLabel.text().splitlines()[-1])
hist = win.settings_page.findChildren(QPushButton)
print("设置页按钮:", [b.text()[:14] for b in hist][:8])

# 主题
win.toggle_theme()
app.processEvents()
print("\n深色模式:", win.mode, "按钮:", win.top.theme_btn.text())
win.toggle_theme()

# 折叠分组
grp = [w for w in win.listInner.findChildren(QPushButton) if w.property("cls") == "group"]
if grp:
    before = sum(1 for w in win.listInner.findChildren(EntryItem) if w.isVisible())
    grp[0].click()
    app.processEvents()
    after = sum(1 for w in win.listInner.findChildren(EntryItem) if w.isVisible())
    print("折叠分组:", grp[0].text().strip()[:20], f"{before} -> {after}")

print("\nQSS 生效检查:", "background" in app.styleSheet().lower())
print("\n问题汇总:", issues if issues else "无")
store.close()
