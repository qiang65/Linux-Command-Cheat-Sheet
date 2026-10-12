#!/usr/bin/env python3
"""针对本轮 4 项需求的验收测试。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt, QSize                                        # noqa: E402
from PyQt5.QtWidgets import QApplication, QToolButton, QWidget           # noqa: E402
from db import Store                                               # noqa: E402
from main_window import MainWindow, GroupHeader, EntryItem         # noqa: E402
from editor import EntryDialog                                     # noqa: E402

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "feat.db")
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

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(name)


def boxes():
    return [w for w in win.listInner.findChildren(QWidget)
            if w.parent() is win.listInner and w.layout() is not None
            and w.layout().count() > 0 and w.property("cls") is None]


print("== 需求1：分组默认全收缩，点击展开 ==")
win.show_category("cheatsheet")
app.processEvents()
heads = win.listInner.findChildren(GroupHeader)
check("分组标题为自绘控件", len(heads) == 14, str(len(heads)))
vis = [b.isVisible() for b in boxes()]
check("默认全部收起", len(vis) > 0 and not any(vis), f"可见组 {sum(vis)}/{len(vis)}")
check("标题初始为收起箭头", all(h.collapsed for h in heads))
heads[0].clicked.emit()
app.processEvents()
check("点击后展开", any(b.isVisible() for b in boxes()))
check("箭头变为展开", not heads[0].collapsed)
heads[0].clicked.emit()
app.processEvents()
check("再次点击收起", not any(b.isVisible() for b in boxes()))
check("按钮初始为展开全部", win.toggleAllBtn.toolTip() == "展开全部",
      win.toggleAllBtn.toolTip())
win.toggleAllBtn.click()
app.processEvents()
check("点一次全展开", all(b.isVisible() for b in boxes()),
      f"{sum(b.isVisible() for b in boxes())}/{len(boxes())}")
check("按钮提示变为收起全部", win.toggleAllBtn.toolTip() == "收起全部",
      win.toggleAllBtn.toolTip())
win.toggleAllBtn.click()
app.processEvents()
check("再点一次全收起", not any(b.isVisible() for b in boxes()))
check("按钮提示回到展开全部", win.toggleAllBtn.toolTip() == "展开全部",
      win.toggleAllBtn.toolTip())
check("展开收起只有一个按钮", sum(1 for b in win.findChildren(QToolButton)
                              if "全部" in b.toolTip()) == 1)
check("展开收起按钮为图标按钮且已画出",
      not win.toggleAllBtn.icon().isNull()
      and win.toggleAllBtn.icon().pixmap(QSize(18, 18)).width() == 18)
check("收藏按钮为图标按钮且已画出",
      not win.favBtn.icon().isNull()
      and win.favBtn.icon().pixmap(QSize(17, 17)).width() == 17)
check("按钮为小尺寸", win.toggleAllBtn.width() <= 34 and win.favBtn.width() <= 34,
      f"{win.toggleAllBtn.width()}/{win.favBtn.width()}")
win.top.search.setText("网络")
app.processEvents()
check("搜索时自动展开", all(b.isVisible() for b in boxes()))
win.top.search.clear()
app.processEvents()

print("== 需求2：命令名纯文本显示 ==")
win.top.search.clear()
app.processEvents()
win.rebuild_list()
app.processEvents()
special = [i for i in win.items.values()
           if any(ch in i.entry["name"] for ch in "|><&!")]
check("存在含特殊符号的命令名", len(special) >= 5, str([i.entry["name"] for i in special][:8]))
ok = all(i.name.textFormat() == Qt.PlainText and i.name.text() == i.entry["name"]
         for i in special)
check("特殊符号命令名逐字一致且为纯文本", ok,
      str([(i.name.text(), i.entry["name"]) for i in special
           if i.name.text() != i.entry["name"]][:4]))
amp = [i for i in special if "&&" in i.entry["name"]]
if amp:
    check("&& 命令名未被转义", amp[0].name.text() == amp[0].entry["name"],
          amp[0].name.text())

print("== 需求3：删除两级提示 + 删除记录可恢复 ==")
eid = store.entries("cheatsheet", "tar")[0]["id"]
before = store.stats()["entries"]
win.show_entry(eid, record=False)
app.processEvents()
check("详情页有删除按钮", any(b.text() == "删除" for b in win.detailInner.findChildren(
    __import__("PyQt5.QtWidgets", fromlist=["QPushButton"]).QPushButton)))
snap = store.to_trash(eid)
check("删除后词条数 -1", store.stats()["entries"] == before - 1)
check("删除记录 +1", store.trash_count() == 1)
check("快照含正文与分组", snap and snap.get("group_name") == "十一、压缩与归档",
      snap.get("group_name") if snap else "")
trash_btns = [b for b in win.settings_page.findChildren(
    __import__("PyQt5.QtWidgets", fromlist=["QPushButton"]).QPushButton)
    if "恢复" in b.text() and "tar" in b.text()]
win.settings_page.refresh()
app.processEvents()
trash_btns = [b for b in win.settings_page.findChildren(
    __import__("PyQt5.QtWidgets", fromlist=["QPushButton"]).QPushButton)
    if "恢复" in b.text() and "tar" in b.text()]
check("设置页出现恢复条目", len(trash_btns) == 1, str(len(trash_btns)))
tid = store.trash_list()[0]["trash_id"]
nid = store.restore_from_trash(tid)
e = store.entry(nid)
check("恢复成功", e is not None and e["name"] == "tar")
check("恢复到原分组", e and e["group_name"] == "十一、压缩与归档",
      e["group_name"] if e else "")
check("恢复后删除记录清空", store.trash_count() == 0)
check("恢复后词条数还原", store.stats()["entries"] == before)

print("== 需求4：自行添加横向大类 ==")
tabs0 = list(win.top.tabs.keys())
cid, err = store.add_category_named("Docker 速查")
check("新增分类无错误", err == "", err)
win.reload_all()
app.processEvents()
check("顶部出现新 tab", "cat" + str(abs(hash("Docker 速查")) % 100000) in win.top.tabs
      or any("Docker" in b.text() for b in win.top.tabs.values()),
      str([b.text() for b in win.top.tabs.values()]))
key = store.db.execute("SELECT key FROM categories WHERE id=?", (cid,)).fetchone()["key"]
dlg = EntryDialog(store, key, win.pal, win)
dlg.name.setText("docker ps")
dlg.cat.setCurrentIndex(dlg.cat.findData(key))
dlg.group.setEditText("容器管理")
dlg.summary.setPlainText("列出运行中的容器")
dlg.example.setPlainText("docker ps -a")
dlg._save()
win.reload_all()
win.show_category(key)
win.top.set_tab(key)
app.processEvents()
check("新分类可新增词条并显示", len(win.items) == 1, str(len(win.items)))
_, err2 = store.add_category_named("Docker 速查")
check("重名分类被拒绝", err2 != "", err2)
n = store.delete_category(cid, keep_in_trash=True)
win.reload_all()
app.processEvents()
check("删除分类后 tab 消失", not any("Docker 速查" in b.text() for b in win.top.tabs.values()),
      str([b.text() for b in win.top.tabs.values()]))
check("分类词条进入删除记录", n == 1 and store.trash_count() == 1,
      f"删除 {n} 条 / 记录 {store.trash_count()}")
tid = store.trash_list()[0]["trash_id"]
nid = store.restore_from_trash(tid)
check("删除分类后可恢复词条", store.entry(nid)["name"] == "docker ps")
check("恢复时自动补建分类", store.entry(nid)["category_key"] == key)

print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
