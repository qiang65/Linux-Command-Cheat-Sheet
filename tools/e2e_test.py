#!/usr/bin/env python3
"""端到端验收测试：增删改、分组、收藏、复制、导入导出、持久化。"""
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtWidgets import QApplication                                    # noqa: E402
from db import Store                                                       # noqa: E402
from main_window import MainWindow, EntryItem                              # noqa: E402
from editor import EntryDialog                                             # noqa: E402
from markdown_view import CodeCard                                         # noqa: E402

# 期望值取自种子文件，种子扩充后测试无需改代码
_seed = json.load(open(os.path.join(ROOT, "data", "seed.json"), encoding="utf-8"))
SEED_ENTRIES = sum(len(g["entries"]) for c in _seed["categories"] for g in c["groups"])
SEED_GROUPS = sum(len(c["groups"]) for c in _seed["categories"])
SEED_KEYS = [c["key"] for c in _seed["categories"]]

app = QApplication(sys.argv)
db = os.path.join(ROOT, "data", "e2e.db")
for suf in ("", "-wal", "-shm"):
    if os.path.exists(db + suf):
        os.remove(db + suf)
store = Store(db)
store.ensure_categories()
store.seed_from_json(os.path.join(ROOT, "data", "seed.json"))
win = MainWindow(store, ROOT)
win.resize(1200, 800)
win.show()
app.processEvents()

fails = []


def check(name, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


print("== 1. 初始状态 ==")
check(f"词条总数与种子一致（{SEED_ENTRIES}）", store.stats()["entries"] == SEED_ENTRIES,
      str(store.stats()["entries"]))
check("横向分类齐全（含设置）",
      set(c["key"] for c in store.categories()) == set(SEED_KEYS + ["settings"]),
      str([c["key"] for c in store.categories()]))
check("速查表分组 14 个", len(store.groups("cheatsheet")) == 14)

print("== 2. 新增词条（含新分组） ==")
dlg = EntryDialog(store, "cheatsheet", win.pal, win)
dlg.name.setText("ffprobe")
dlg.cat.setCurrentIndex(dlg.cat.findData("cheatsheet"))
dlg.group.setEditText("自定义新分组")
dlg.summary.setPlainText("查看媒体文件信息")
dlg.example.setPlainText("ffprobe -i a.mp4")
dlg.content.setPlainText("## 说明\n\nffprobe 是 ffmpeg 套件的探测工具。\n\n```bash\nffprobe -show_streams a.mp4\n```")
dlg._save()
nid = dlg.saved_id()
win.rebuild_list()
win.show_entry(nid, record=False)
app.processEvents()
e = store.entry(nid)
check("新增成功", bool(e), e["name"] if e else "")
check("自动创建新分组", e and e["group_name"] == "自定义新分组", e["group_name"] if e else "")
check("出现在列表", nid in win.items)
check("正文渲染出代码卡片",
      len(win.detailInner.findChildren(CodeCard)) >= 1,
      str(len(win.detailInner.findChildren(CodeCard))))

print("== 3. 编辑词条 ==")
dlg2 = EntryDialog(store, "cheatsheet", win.pal, win, entry_id=nid)
check("编辑框回填名称", dlg2.name.text() == "ffprobe")
check("编辑框回填分组", dlg2.group.currentText() == "自定义新分组")
dlg2.name.setText("ffprobe2")
dlg2._save()
check("名称已更新", store.entry(nid)["name"] == "ffprobe2")

print("== 4. 收藏与只看收藏 ==")
win.show_entry(nid, record=False)
win.on_fav(nid)
check("收藏标记写入", store.entry(nid)["fav"] == 1)
win.favBtn.setChecked(True)
app.processEvents()
names = [i.entry["name"] for i in win.items.values()]
check("只看收藏只剩 1 条", len(names) == 1 and names[0] == "ffprobe2", str(names))
win.on_fav(nid)
win.favBtn.setChecked(False)
app.processEvents()
check("取消收藏后恢复全量", len(win.items) == 169, str(len(win.items)))

print("== 5. 代码卡片一键复制 ==")
win.show_entry(store.entries("cheatsheet", "rm")[0]["id"], record=False)
app.processEvents()
cards = win.detailInner.findChildren(CodeCard)
check("速查表词条渲染出示例卡片", len(cards) >= 1, str(len(cards)))
if cards:
    QApplication.clipboard().clear()
    cards[0]._copy()
    check("剪贴板内容等于代码", QApplication.clipboard().text() == cards[0].code,
          repr(QApplication.clipboard().text()[:40]))
    check("按钮显示已复制", cards[0].btn.text().startswith("已复制"))
else:
    check("ls 详情存在代码卡片", False)

print("== 6. 搜索 ==")
win.top.search.setText("递归")
app.processEvents()
hits = [i.entry["name"] for i in win.items.values()]
check("搜索命中", len(hits) >= 3 and "rm" in hits, str(hits[:6]))
win.top.search.setText("zzzz-不存在")
app.processEvents()
check("无命中时列表清空", len(win.items) == 0)
win.top.search.clear()
app.processEvents()
check("清空搜索恢复", len(win.items) == 169)

print("== 7. 删除词条 ==")
store.delete_entry(nid)
win.rebuild_list()
app.processEvents()
check("删除生效", store.entry(nid) is None and len(win.items) == 168)

print("== 8. 导出 / 导入 ==")
p = os.path.join(ROOT, "data", "e2e_export.json")
before = store.stats()["entries"]
n = store.export_json(p)
check("导出条数与库内一致", n == before, f"导出 {n} / 库内 {before}")
store.import_json(p, replace=True)
check("覆盖导入后条数一致", store.stats()["entries"] == before,
      str(store.stats()["entries"]))
check("导入后分组数", store.stats()["groups"] == SEED_GROUPS,
      f"{store.stats()['groups']} / 期望 {SEED_GROUPS}")
win.rebuild_list()
app.processEvents()
check("导入后速查表列表重建", len(win.items) == 168, str(len(win.items)))

print("== 9. 浏览历史 ==")
win.show_entry(store.entries("shell", "数组")[0]["id"], record=True)
h = store.history(5)
check("历史记录写入", len(h) >= 1 and h[0]["name"] == "Shell 数组", str(h[:1]))
store.clear_history()
check("清空历史", len(store.history(5)) == 0)

print("== 10. 持久化（主题/字号/分类/窗口） ==")
win.mode = "dark"
win.store.set_setting("theme", "dark")
win.cat = "manual"
win.store.set_setting("last_cat", "manual")
win.save_geometry()
store.close()
s2 = Store(db)
check("主题持久化", s2.setting("theme") == "dark")
check("分类持久化", s2.setting("last_cat") == "manual")
check("窗口几何持久化", bool(s2.setting("geometry")))
s2.close()

print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
