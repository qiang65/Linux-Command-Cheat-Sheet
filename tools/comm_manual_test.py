#!/usr/bin/env python3
"""验证《Linux 命令大全》441 条导入后的实际表现。"""
import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
_seed = json.load(open(os.path.join(ROOT, "data", "seed.json"), encoding="utf-8"))
SEED_ENTRIES = sum(len(g["entries"]) for c in _seed["categories"] for g in c["groups"])

from PyQt5.QtCore import Qt                                                    # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel                               # noqa: E402
from db import Store                                                           # noqa: E402
from main_window import MainWindow, GroupHeader                                # noqa: E402
import markdown_view                                                           # noqa: E402

app = QApplication(sys.argv)
store = Store(os.path.join(ROOT, "data", "linux.db"))
win = MainWindow(store, ROOT)
win.resize(1280, 820)
win.show()
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


print("== 分类与数据 ==")
keys = [c["key"] for c in store.categories(with_settings=False)]
check("新分类已建立", "commmanual" in keys, str(keys))
check("顶部分类栏出现新 tab", "commmanual" in win.top.tabbar.tabs,
      str([b.text() for b in win.top.tabbar.tabs.values()]))
check("词条数 441", store.category_entry_count("commmanual") == 441,
      str(store.category_entry_count("commmanual")))
gs = store.groups("commmanual")
check("分组 11 个", len(gs) == 11, str([g["name"] for g in gs]))
check(f"总词条与种子一致（{SEED_ENTRIES}）", store.stats()["entries"] == SEED_ENTRIES,
      str(store.stats()["entries"]))

print("== 列表显示 ==")
win.show_category("commmanual")
win.top.set_tab("commmanual")
app.processEvents()
check("默认全部收起", not any(b.isVisible() for b in win.listInner.findChildren(
    __import__("PyQt5.QtWidgets", fromlist=["QWidget"]).QWidget)
    if b.parent() is win.listInner and b.layout() and b.layout().count() > 0
    and b.property("cls") is None))
heads = win.listInner.findChildren(GroupHeader)
check("分组标题 11 个", len(heads) == 11, str(len(heads)))
t0 = time.time()
heads[0].clicked.emit()
app.processEvents()
dt = (time.time() - t0) * 1000
vis = sum(1 for i in win.items.values() if i.isVisible())
check("展开一组后该组条目可见", vis == 56, f"可见 {vis} 条 / 共 {len(win.items)} 控件，耗时 {dt:.0f}ms")
check("展开耗时可接受", dt < 1500, f"{dt:.0f}ms")
win.expanded.clear()
win.rebuild_list()
app.processEvents()
win.toggle_all()          # 当前全收起 → 全展开
app.processEvents()
vis_all = sum(1 for i in win.items.values() if i.isVisible())
check("展开全部后 441 条可见", vis_all == 441, f"{vis_all}")
win.toggle_all()          # 有展开 → 全收起
app.processEvents()
check("再点一次全部收起", sum(1 for i in win.items.values() if i.isVisible()) == 0)

print("== 词条详情 ==")
for nm in ("chmod", "grep", "ps", "tar", "awk"):
    r = store.entries("commmanual", nm)
    if not r:
        check(f"{nm} 可搜到", False)
        continue
    e = r[0]
    win.show_entry(e["id"], record=False)
    app.processEvents()
    texts = [l.text().strip() for l in win.detailInner.findChildren(QLabel) if l.text().strip()]
    summ = (e.get("summary") or "").strip()
    key = summ[:30]
    hits = sum(1 for t in texts if key and key in t.replace("**", "").replace("`", ""))
    check(f"{nm}: 有正文且说明不重复堆叠",
          len(e["content"]) > 300 and hits <= 2,      # 摘要卡 1 次 + 正文自然提及 1 次
          f"正文 {len(e['content'])} 字，说明出现 {hits} 次")
    codes = win.detailInner.findChildren(markdown_view.CodeCard)
    check(f"{nm}: 有可复制代码卡片", len(codes) >= 1, f"{len(codes)} 个")

print("== 4 个 404 页面的兜底 ==")
missing = ["docker", "podman", "kubectl", "virsh"]
for nm in missing:
    r = store.entries("commmanual", nm)
    check(f"{nm} 词条存在且有说明", bool(r) and bool(r[0]["summary"].strip()),
          r[0]["summary"] if r else "无词条")
    if r:
        win.show_entry(r[0]["id"], record=False)
        app.processEvents()
        check(f"{nm} 详情可显示", any(l.text().strip()
                                     for l in win.detailInner.findChildren(QLabel)))

print("== 搜索与统计 ==")
win.top.search.setText("权限")
app.processEvents()
check("搜索命中多条", len(win.items) >= 5, f"{len(win.items)} 条")
win.top.search.setText("chmod")
app.processEvents()
check("精确搜索命中", any(i.entry["name"] == "chmod" for i in win.items.values()),
      str([i.entry["name"] for i in win.items.values()][:6]))
win.top.search.clear()
app.processEvents()
sizes = [len(e["content"]) for e in store.entries("commmanual")]
check("正文长度分布合理", max(sizes) < 12000 and sum(sizes) / len(sizes) > 500,
      f"平均 {sum(sizes)//len(sizes)} 最长 {max(sizes)}")
check("示例字段覆盖过半", sum(1 for s in sizes) > 0
      and store.db.execute("SELECT COUNT(*) n FROM entries WHERE category_id="
                           "(SELECT id FROM categories WHERE key='commmanual') "
                           "AND example<>''").fetchone()["n"] > 220,
      str(store.db.execute("SELECT COUNT(*) n FROM entries WHERE category_id="
                           "(SELECT id FROM categories WHERE key='commmanual') "
                           "AND example<>''").fetchone()["n"]))

store.close()
print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
