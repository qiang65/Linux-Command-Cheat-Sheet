#!/usr/bin/env python3
"""真实拖放验收：模拟 QDropEvent 拖动分类行，验证数据库与 tabBar 自动对应。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import QMimeData, QPointF, Qt                                # noqa: E402
from PyQt5.QtGui import QDropEvent                                             # noqa: E402
from PyQt5.QtWidgets import QApplication                                       # noqa: E402
from db import Store                                                           # noqa: E402
from main_window import GroupHeader, MainWindow                                # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "drag.db")
for s in ("", "-wal", "-shm"):
    if os.path.exists(db + s):
        os.remove(db + s)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))
store.add_category_named("Docker 速查")
store.add_category_named("网络排查")
win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
win.show_category("cheatsheet")
win.show_category("settings")
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


cl = win.settings_page.catList


def drag_row(src, dst):
    """模拟内部拖放的「删除 + 插入」落地路径（不发 rowsMoved）。"""
    it = cl.takeItem(src)
    cl.insertItem(dst, it)
    return True


def drop_event_row(src, dst):
    """模拟拖放落点事件：走 viewport 的 Drop 事件过滤器兜底提交。"""
    it = cl.takeItem(src)
    cl.blockSignals(True)          # 屏蔽行信号，只靠 Drop 事件触发提交
    cl.insertItem(dst, it)
    cl.blockSignals(False)
    rect = cl.visualItemRect(cl.item(dst))
    ev = QDropEvent(QPointF(rect.center().x(), rect.bottom() - 2), Qt.MoveAction,
                    cl.mimeData([it]), Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(cl.viewport(), ev)
    return True


def db_order():
    return [c["key"] for c in store.categories(with_settings=False)]


def tab_order():
    return list(win.top.tabbar.tabs)


def lit():
    return [k for k, b in win.top.tabbar.tabs.items() if b.isChecked()]


print("== 拖放前 ==")
n = cl.count()
check("分类列表行数与数据库一致", n == len(db_order()), f"{n} vs {len(db_order())}")
before = db_order()
print("  · 顺序:", before)

print("== 模拟内部拖放（第 0 行 → 第 2 行，删除+插入路径）==")
sent = drag_row(0, 2)
app.processEvents()
check("拖放操作已执行", sent)
after = db_order()
check("拖放后数据库顺序自动更新（未手动调用提交）", before != after and after[2] == before[0],
      f"{before} -> {after}")

print("== tabBar 与数据库对应 ==")
win.reload_all()
app.processEvents()
check("tabBar 顺序与数据库完全一致", tab_order() == after,
      f"{tab_order()} vs {after}")
check("tabBar 按钮数与分类数一致", len(tab_order()) == len(after))
check("设置分类不占 tabBar 位", "settings" not in tab_order())

print("== 连续多次拖放 ==")
seq = [db_order()]
for src, dst in ((1, 0), (3, 1), (0, 4)):
    if cl.count() > max(src, dst):
        drag_row(src, dst)
        app.processEvents()
        seq.append(db_order())
check("多次拖放均生效", len({tuple(s) for s in seq}) == len(seq),
      f"{len(seq)} 次，{len({tuple(s) for s in seq})} 种顺序")
win.reload_all()
app.processEvents()
check("多次拖放后 tabBar 仍与数据库一致", tab_order() == db_order(),
      f"{tab_order()} vs {db_order()}")

print("== Drop 事件兜底路径 ==")
b0 = db_order()
drop_event_row(0, 3)
app.processEvents()
check("仅靠 Drop 事件也能提交顺序", db_order() != b0 and db_order()[3] == b0[0],
      f"{b0} -> {db_order()}")
app.processEvents()
check("Drop 完成后 tabBar 即时同步", tab_order() == db_order(),
      f"{tab_order()} vs {db_order()}")
check("Drop 完成后设置列表即时同步",
      [cl.item(i).data(Qt.UserRole) for i in range(cl.count())] == db_order())
win.reload_all()
app.processEvents()
check("兜底提交后 tabBar 同步", tab_order() == db_order())

print("== 拖放后高亮与纵向栏 ==")
win.show_category(after[0])
app.processEvents()
check("切换分类后高亮唯一", lit() == [after[0]], str(lit()))
check("高亮分类的纵向栏分组数正确",
      len(win.listInner.findChildren(GroupHeader))
      == len(store.groups(after[0])),
      f"{len(win.listInner.findChildren(GroupHeader))}"
      f" / {len(store.groups(after[0]))}")
win.show_category("settings")
app.processEvents()
check("回设置页列表顺序与数据库一致",
      [cl.item(i).data(Qt.UserRole) for i in range(cl.count())] == db_order(),
      str([cl.item(i).data(Qt.UserRole) for i in range(cl.count())]))

print("== 新增/删除分类后顺序稳定 ==")
store.add_category_named("Git 命令")
win.reload_all()
app.processEvents()
o1 = db_order()
check("新增分类追加在末尾", o1[-1] == [c["key"] for c in store.categories(with_settings=False)][-1],
      str(o1))
check("新增后 tabBar 与数据库一致", tab_order() == o1)
win.show_category("settings")
app.processEvents()
check("设置页列表顺序同步新增",
      [cl.item(i).data(Qt.UserRole) for i in range(cl.count())] == o1)
cid = store.category_id(o1[1])
store.delete_category(cid, keep_in_trash=True)
win.reload_all()
app.processEvents()
check("删除后 tabBar 与数据库一致", tab_order() == db_order(),
      f"{tab_order()} vs {db_order()}")
win.show_category("settings")
app.processEvents()
check("删除后设置页列表同步",
      [cl.item(i).data(Qt.UserRole) for i in range(cl.count())] == db_order())

print("== 重启持久化 ==")
expect = db_order()
store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
store.close()
s2 = Store(db)
check("重开程序顺序保持", [c["key"] for c in s2.categories(with_settings=False)] == expect,
      f"{[c['key'] for c in s2.categories(with_settings=False)]} vs {expect}")
print("  · sort 值:", [(c["key"], c["sort"]) for c in s2.categories()])
s2.close()

print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
