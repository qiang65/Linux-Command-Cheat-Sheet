#!/usr/bin/env python3
"""检查纵向列表命令名是否被切字（末尾半字）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import QEvent, Qt                                           # noqa: E402
from PyQt5.QtGui import QFontMetrics                                          # noqa: E402
from PyQt5.QtWidgets import QApplication                                      # noqa: E402
from db import Store                                                          # noqa: E402
from main_window import MainWindow                                            # noqa: E402
from marquee import MarqueeLabel                                              # noqa: E402
import theme                                                                  # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "font.db")
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
win.top.set_tab("cheatsheet")
win.toggle_all()          # 全展开，让所有条目完成布局
app.processEvents()
win._relayout(win.listInner)
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


font_options = [win.settings_page.fontSel.itemData(i)
                for i in range(win.settings_page.fontSel.count())]
check("字号选项支持 7 pt", 7 in font_options, str(font_options))
font_changes = []
win.settings_page.font_changed.connect(font_changes.append)
win.settings_page.fontSel.setCurrentIndex(win.settings_page.fontSel.findData(7))
check("选择 7 pt 后发出字号变更", font_changes == [7], str(font_changes))
win.settings_page.fontSel.setCurrentIndex(
    win.settings_page.fontSel.findData(float(store.setting("font_pt", "10.5"))))

print("== 字体设置 ==")
qss = theme.qss("light", 10.5)
rule = qss.split('QLabel[cls="itemName"]')[1].split("}")[0]
check("QSS 不再用 font-weight 控制命令名（避免 sizeHint 低估）",
    "font-weight" not in rule and "font-size" in rule, rule.strip())
sample = list(win.items.values())[0]
check("命令名字体为粗体且字号正确",
    sample.name.font().bold()
    and abs(sample.name.font().pointSizeF() - (win.base_pt + 0.5)) < 0.1,
      f"bold={sample.name.font().bold()} pt={sample.name.font().pointSizeF()}")
check("命令名标签上下留白避免字形裁切",
    sample.name.minimumHeight() >= QFontMetrics(sample.name.font()).height() + 4,
    f"label={sample.name.minimumHeight()}px, line={QFontMetrics(sample.name.font()).height()}px")
check("命令说明字号恢复原设定",
    abs(sample.summary.font().pointSizeF() - max(7.0, win.base_pt - 1.5)) < 0.1,
    f"pt={sample.summary.font().pointSizeF()}")

print("== 逐条检查切字 ==")
clipped, elided, complete = [], [], 0
for eid, item in win.items.items():
    lab = item.name
    w = lab.width()
    if w <= 0:
        continue
    fm = QFontMetrics(lab.font())
    full_w = fm.horizontalAdvance(lab.full)
    shown = lab.text()
    if full_w <= w:
        if shown != lab.full:
            clipped.append((lab.full, shown, w, full_w))
        else:
            complete += 1
    else:
        if not shown.endswith("…"):
            clipped.append((lab.full, shown, w, full_w))
        else:
            elided.append(lab.full)

total = complete + len(elided)
check("无条目被硬切字（完整显示或省略号收尾）", not clipped,
      str(clipped[:3]))
print(f"  · 完整显示 {complete} 条，省略号收尾 {len(elided)} 条")
check("绝大多数命令名完整显示", complete >= total * 0.9,
      f"{complete}/{total}")
if elided:
    print("  · 需要省略号的名称:", elided[:6])

print("== 可用宽度 ==")
lab = sample.name
check("列表面板由可拖动分隔器控制", win.content.handleWidth() > 0
    and win.content.count() == 2)
check("纵向列表默认空间增加", win.listPanel.width() >= 390,
    f"{win.listPanel.width()}px")
print("== 命令中文说明跑马灯 ==")
win.content.setSizes([230, 1050])
app.processEvents()
name_label = MarqueeLabel("a-very-long-command-name-that-overflows")
name_label.resize(70, 20)
check("命令名标签支持超宽检测", name_label.overflow())
QApplication.sendEvent(name_label, QEvent(QEvent.Enter))
name_label._tick()
check("命令名跑马灯推进文字", name_label._off > 0)
QApplication.sendEvent(name_label, QEvent(QEvent.Leave))

summary_label = next((item.summary for item in win.items.values()
                if item.summary.full and item.summary.overflow()), None)
check("中文说明使用跑马灯标签", summary_label is not None)
if summary_label:
    QApplication.sendEvent(summary_label, QEvent(QEvent.Enter))
    summary_label._tick()
    check("说明悬停时文字推进", summary_label._off > 0)
    QApplication.sendEvent(summary_label, QEvent(QEvent.Leave))

    old_width = win.listPanel.width()
    win.content.setSizes([470, 810])
    app.processEvents()
    check("扩大分隔器后列表面板增宽", win.listPanel.width() > old_width,
        f"{old_width} -> {win.listPanel.width()}px")
    print(f"  · 面板 {win.listPanel.width()}px，命令名可用宽约 {lab.width()}px")

store.close()
print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
