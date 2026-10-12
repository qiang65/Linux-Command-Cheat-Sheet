#!/usr/bin/env python3
"""渲染覆盖率检查：详情页渲染出的文字量 / 词条原文字量。

用于发现"正文被去重逻辑整块砍掉"这类内容不全问题。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtGui import QTextDocument                                              # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel, QPlainTextEdit                   # noqa: E402
from db import Store                                                               # noqa: E402
from main_window import MainWindow                                                 # noqa: E402
import markdown_view                                                               # noqa: E402

app = QApplication(sys.argv)
store = Store(os.path.join(ROOT, "data", "linux.db"))
win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
app.processEvents()

fails = []
CATS = ("shell", "manual", "commmanual", "docker", "cheatsheet")
LIMIT = {"commmanual": 5, "docker": 5, "cheatsheet": 6}

print(f"{'词条':<24}{'原文':>7}{'渲染':>7}{'卡内':>7}{'覆盖率':>8}  代码卡")
tot_src = tot_out = 0
worst = []
for cat in CATS:
    es = store.entries(cat)
    if cat in LIMIT:
        es = es[:LIMIT[cat]]
    for e in es:
        win.show_entry(e["id"], record=False)
        app.processEvents()
        inner = win.detailInner
        txt = " ".join(l.text() for l in inner.findChildren(QLabel))
        doc = QTextDocument()
        doc.setHtml(txt)
        rendered = len(doc.toPlainText())
        ctext = " ".join(p.toPlainText() for p in inner.findChildren(QPlainTextEdit))
        # 分母只算会渲染的内容：长正文词条的 example 与正文代码块重复，
        # 设计上不再单独渲染示例卡，不应计入分母。
        src = len(e["content"]) + len(e["summary"]) + len(e["params"])
        if len(e["content"]) < 300:
            src += len(e["example"])
        out = rendered + len(ctext)
        cov = out / max(1, src) * 100
        tot_src += src
        tot_out += out
        cards = len(inner.findChildren(markdown_view.CodeCard))
        print(f"{e['name'][:22]:<24}{src:>7}{rendered:>7}{len(ctext):>7}{cov:>7.0f}%  {cards}")
        if src >= 400 and cov < 55:
            worst.append((e["name"], cat, round(cov), src))

print(f"\n合计 原文 {tot_src} 字  渲染 {tot_out} 字  覆盖率 {tot_out / max(1, tot_src) * 100:.0f}%")

print("\n== 覆盖率检查 ==")
cov_all = tot_out / max(1, tot_src) * 100
if cov_all < 60:
    fails.append(f"整体覆盖率 {cov_all:.0f}% 偏低")
print(("  PASS  " if cov_all >= 60 else "  FAIL  ") + f"整体覆盖率 ≥60%   {cov_all:.0f}%")
if worst:
    print(f"  FAIL  低覆盖率词条 {len(worst)} 条: {worst[:6]}")
    fails.append("存在低覆盖率词条")
else:
    print("  PASS  无低覆盖率词条（长正文均 ≥55%）")

print("\n== 去重逻辑 ==")
# 摘要与正文首段重复时，正文应剥掉首段而非整块丢弃
cases = [
    ("正文就是摘要", markdown_view.strip_dup_lead("ABC 定义", "ABC 定义"), ""),
    ("剥掉重复首段", markdown_view.strip_dup_lead("首段说明\n\n## 语法\n内容", "首段说明"), "## 语法\n内容"),
    ("首段带标记", markdown_view.strip_dup_lead("**首段说明**\n\n正文", "首段说明"), "正文"),
    ("正文首段不同", markdown_view.strip_dup_lead("独立开头\n正文", "无关摘要"), "独立开头\n正文"),
    ("空正文", markdown_view.strip_dup_lead("", "摘要"), ""),
    ("无摘要", markdown_view.strip_dup_lead("正文", ""), "正文"),
]
for name, got, want in cases:
    ok = got.strip() == want.strip()
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}   -> {got!r}")
    if not ok:
        fails.append(name)

store.close()
print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
