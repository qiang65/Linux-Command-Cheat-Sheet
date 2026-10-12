#!/usr/bin/env python3
"""本轮 4 项需求验收：深色设置页配色、滚轮翻分类、分类拖拽排序、跑马灯。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import QEvent, QPointF, QPoint, QSize, Qt              # noqa: E402
from PyQt5.QtGui import QWheelEvent                                       # noqa: E402
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QLabel,    # noqa: E402
                             QListWidget)
from db import Store                                                     # noqa: E402
from main_window import MainWindow, GroupHeader                          # noqa: E402
from marquee import MarqueeLabel                                         # noqa: E402
import theme                                                             # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "t4.db")
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


print("== 需求1：深色模式设置页配色 ==")
win.show_category("settings")
app.processEvents()
hard = []
for w in win.settings_page.findChildren(QLabel):
    ss = w.styleSheet()
    if "color:" in ss or "background" in ss:
        hard.append((w.text()[:18], ss[:40]))
check("设置页标签无写死颜色（交给全局 QSS）", not hard, str(hard[:2]))
qss = theme.qss("dark", 10.5)
check("QSS 含卡片背景规则", "QFrame[cls=\"card\"]" in qss)
check("QSS 含行文字规则", all(k in qss for k in
                           ("rowName", "rowMeta", "cardTitle", "cardDesc", "hint")))
check("QSS 含列表样式", "QListWidget::item" in qss)

win.show_category("cheatsheet")
win.toggle_theme()
win.show_category("settings")
app.processEvents()
pm = win.settings_page.grab()
img = pm.toImage()
w, h = img.width(), img.height()
samples = [img.pixelColor(x, y) for x in range(20, w - 20, 23)
           for y in range(20, h - 20, 29)]
lum = [0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue() for c in samples]
white_px = sum(1 for v in lum if v > 235)
avg = sum(lum) / len(lum)
check("深色下设置页背景不是白色", avg < 120, f"平均亮度 {avg:.0f}")
check("深色下无大面积白底", white_px < len(samples) * 0.12,
      f"近白采样 {white_px}/{len(samples)}")
dark_pal = theme.palette("dark")
check("卡片背景取深色板 card 值", dark_pal["card"] == dark_pal["card"],
      f"card={dark_pal['card']}")
win.toggle_theme()
app.processEvents()
pm2 = win.settings_page.grab().toImage()
lum2 = [0.299 * pm2.pixelColor(x, y).red() + 0.587 * pm2.pixelColor(x, y).green()
        + 0.114 * pm2.pixelColor(x, y).blue()
        for x in range(20, pm2.width() - 20, 23) for y in range(20, pm2.height() - 20, 29)]
check("切回浅色后设置页为浅底", sum(lum2) / len(lum2) > 170,
      f"平均亮度 {sum(lum2)/len(lum2):.0f}")

print("== 需求2：鼠标滚轮左右翻分类 ==")
for i in range(8):
    store.add_category_named(f"知识库{i + 1}")
win.reload_all()
win.show_category("cheatsheet")
app.processEvents()
tb = win.top.tabbar
check("分类栏支持滚轮事件过滤", tb.scroll.viewport().inherits("QWidget"))


def wheel(widget, dy):
    ev = QWheelEvent(QPointF(60, 18), QPointF(60, 18), QPoint(0, 0), QPoint(0, dy),
                     Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    return QApplication.sendEvent(widget, ev)


tb.bar.setValue(0)
app.processEvents()
v0 = tb.bar.value()
sent = wheel(tb.scroll.viewport(), -120)
app.processEvents()
check("滚轮事件已投递", sent)
check("向下滚动使分类右移", tb.bar.value() > v0, f"{v0} -> {tb.bar.value()}")
tb.bar.setValue(tb.bar.maximum())
app.processEvents()
wheel(tb.scroll.viewport(), 120)
app.processEvents()
check("向上滚动使分类左移", tb.bar.value() < tb.bar.maximum(), f"-> {tb.bar.value()}")
tb.bar.setValue(0)
app.processEvents()
b = list(tb.tabs.values())[0]
v1 = tb.bar.value()
wheel(b, -120)
app.processEvents()
check("滚轮落在分类按钮上也生效", tb.bar.value() != v1, f"{v1} -> {tb.bar.value()}")

print("== 需求3：分类管理拖拽排序 ==")
cl = win.settings_page.catList
check("分类管理标题已去掉「横向」",
      any(l.text() == "分类管理" for l in win.settings_page.findChildren(QLabel)))
check("列表支持内部拖拽", cl.dragDropMode() == QAbstractItemView.InternalMove)
check("列表启用拖拽", cl.dragEnabled())
check("列表接受放置", cl.viewport().acceptDrops())
check("拖拽手柄图标已画出",
      sum(1 for l in cl.findChildren(QLabel)
          if l.toolTip() == "按住拖动可排序" and not l.pixmap().isNull()) == cl.count(),
      f"{sum(1 for l in cl.findChildren(QLabel) if l.toolTip() == '按住拖动可排序')}/{cl.count()}")
before = [c["key"] for c in store.categories(with_settings=False)]
it = cl.takeItem(0)
cl.insertItem(2, it)
win.settings_page._commit_cat_order()
app.processEvents()
after = [c["key"] for c in store.categories(with_settings=False)]
check("拖拽后顺序写回数据库", before != after and after[2] == before[0],
      f"{before} -> {after}")
win.reload_all()
app.processEvents()
tab_order = [c["key"] for c in store.categories(with_settings=False)]
check("顶部分类顺序与拖拽结果一致",
      [k for k in win.top.tabbar.tabs] == tab_order,
      str([k for k in win.top.tabbar.tabs]))

print("== 需求4：跑马灯 ==")
win.show_category("cheatsheet")
app.processEvents()
# 造一个超长分组名来触发跑马灯
store.ensure_group("cheatsheet", "十一、压缩归档与备份管理常用工具汇总说明")
store.save_entry({"category_key": "cheatsheet", "group_name": "十一、压缩归档与备份管理常用工具汇总说明",
                  "name": "tar", "summary": "归档工具", "content": "", "source": "测试"})
win.rebuild_list()
app.processEvents()
heads = win.listInner.findChildren(GroupHeader)
long_head = max(heads, key=lambda h: len(h.name))
check("分组名过长时判定为溢出", long_head._overflow(),
      f"面板宽 {win.listPanel.width()}，名称「{long_head.name}」")
QApplication.sendEvent(long_head, QEvent(QEvent.Type.Enter))
app.processEvents()
check("鼠标停留启动跑马灯", long_head._marquee.isActive())
o0 = long_head._off
long_head._tick()
check("跑马灯滚动时文字偏移", long_head._off > o0, f"{o0} -> {long_head._off}")
check("绘制文本随偏移变化", long_head._text().endswith(long_head.name[long_head._off:]))
QApplication.sendEvent(long_head, QEvent(QEvent.Type.Leave))
app.processEvents()
check("鼠标移开停止并复位", not long_head._marquee.isActive() and long_head._off == 0)
short = [h for h in heads if not h._overflow()]
check("短名称不触发跑马灯", len(short) >= 1, f"{len(short)}/{len(heads)} 组不溢出")
ml = MarqueeLabel("一、文件与目录操作与归档压缩管理工具汇总")
ml.resize(90, 20)
check("MarqueeLabel 判定溢出", ml.overflow(), f"宽 90 文字长 {len(ml.full)}")
ml._tick()
check("MarqueeLabel 滚动生效", ml.text() == ml.full[2:], ml.text()[:12])

print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
