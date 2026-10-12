#!/usr/bin/env python3
"""检查详情页是否把同一段说明渲染两遍。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt                                                  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel                             # noqa: E402
from db import Store                                                           # noqa: E402
from main_window import MainWindow                                             # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "dup.db")
for s in ("", "-wal", "-shm"):
    if os.path.exists(db + s):
        os.remove(db + s)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))
win = MainWindow(store, ROOT)
win.resize(1200, 800)
win.show()
app.processEvents()

bad = []
checked = 0
for cat in ("cheatsheet", "shell", "manual"):
    ents = store.entries(cat)
    step = max(1, len(ents) // 12)
    for e in ents[::step]:
        win.show_entry(e["id"], record=False)
        app.processEvents()
        texts = [l.text().strip() for l in win.detailInner.findChildren(QLabel)]
        texts = [t for t in texts if t]
        summ = (e.get("summary") or "").strip()
        key = summ[:40].replace("**", "").replace("`", "")
        hits = sum(1 for t in texts if key and key in t.replace("**", "").replace("`", ""))
        checked += 1
        if hits > 1:
            bad.append((cat, e["name"], hits, [t[:50] for t in texts if key in t]))

print(f"检查 {checked} 条词条")
if bad:
    print(f"重复渲染 {len(bad)} 条：")
    for c, n, h, ts in bad[:8]:
        print(f"  [{c}] {n} 出现 {h} 次")
        for t in ts:
            print("      ·", t)
else:
    print("无重复：每条说明在详情页只出现一次")

# 额外确认：速查表词条详情里说明 + 示例卡片都在
win.show_entry(store.entries("cheatsheet", "rm")[0]["id"], record=False)
app.processEvents()
labels = [l.text().strip() for l in win.detailInner.findChildren(QLabel) if l.text().strip()]
print("\n[rm 详情标签]", len(labels))
for t in labels[:6]:
    print("   ·", t[:70])

# 检查 1：富文本标签必须被解析（渲染后的纯文本里不应残留标签源码）
from PyQt5.QtGui import QTextDocument                                        # noqa: E402


def plain(html):
    d = QTextDocument()
    d.setHtml(html)
    return d.toPlainText()


rich = [l for l in win.detailInner.findChildren(QLabel)
        if l.textFormat() == Qt.RichText and l.text().strip()]
leak = [l.text()[:60] for l in rich
        if "<span" in plain(l.text()) or "<b>" in plain(l.text())
        or "background-color" in plain(l.text())]
fmt_ok = any(l.objectName() == "detailSummary" and l.textFormat() == Qt.RichText
             for l in win.detailInner.findChildren(QLabel))
print("\n富文本标签数:", len(rich), " 摘要标签为富文本:", fmt_ok)
print("渲染后残留标签源码:", "无" if not leak else leak[:2])
print("摘要渲染纯文本:", plain([l.text() for l in win.detailInner.findChildren(QLabel)
                          if l.objectName() == "detailSummary"][0])[:60]
      if fmt_ok else "-")

# 检查 2：meta 标签（分类/分组/标签）不得重复
meta = [t for t in labels if t in ("Linux 命令速查表", "一、文件与目录操作")]
print("meta 重复:", "无" if len(meta) == len(set(meta)) else f"重复 {meta}")

ok = not bad and not leak and len(meta) == len(set(meta))
print("\n结果:", "全部通过" if ok else "存在问题")
sys.exit(0 if ok else 1)
