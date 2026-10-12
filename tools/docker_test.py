#!/usr/bin/env python3
"""验证《Docker 命令》54 条导入后的表现，重点查网络/卷命令的章节切分。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5.QtCore import Qt                                                     # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel                                # noqa: E402
from db import Store                                                            # noqa: E402
from main_window import GroupHeader, MainWindow                                 # noqa: E402
import markdown_view                                                            # noqa: E402

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
check("Docker 分类已建立", "docker" in keys, str(keys))
check("顶部分类栏出现 Docker", "docker" in win.top.tabbar.tabs,
      str([b.text() for b in win.top.tabbar.tabs.values()]))
check("词条 54 条", store.category_entry_count("docker") == 54,
      str(store.category_entry_count("docker")))
gs = store.groups("docker")
check("分组 9 个", len(gs) == 9, str([g["name"] for g in gs]))
check("总词条 690", store.stats()["entries"] == 690, str(store.stats()["entries"]))
check("每条都有说明", all(e["summary"].strip() for e in store.entries("docker")))

print("== 列表显示 ==")
win.show_category("docker")
app.processEvents()
heads = win.listInner.findChildren(GroupHeader)
check("分组标题 9 个", len(heads) == 9, str(len(heads)))
win.toggle_all()
app.processEvents()
vis = sum(1 for i in win.items.values() if i.isVisible())
check("展开后 54 条可见", vis == 54, f"{vis}")

print("== 命令详情页词条 ==")
for nm in ("run", "ps", "build", "images", "exec", "compose up"):
    r = [e for e in store.entries("docker") if e["name"] == nm]
    check(f"{nm} 词条存在", bool(r), str([e['name'] for e in store.entries('docker')][:6]))
    if not r:
        continue
    e = r[0]
    win.show_entry(e["id"], record=False)
    app.processEvents()
    codes = win.detailInner.findChildren(markdown_view.CodeCard)
    summ = e["summary"].strip()[:26]
    texts = [l.text().strip() for l in win.detailInner.findChildren(QLabel) if l.text().strip()]
    hits = sum(1 for t in texts if summ and summ in t.replace("**", "").replace("`", ""))
    # 摘要卡显示 1 次；正文变完整后正文里自然提到同一句话属正常，
    # 旧版靠"整块砍掉正文"把次数压到 1，那才是内容不全。
    check(f"  {nm}: 正文充实且说明不重复堆叠",
          len(e["content"]) > 200 and hits <= 2,
          f"正文 {len(e['content'])} 字，说明出现 {hits} 次")
    check(f"  {nm}: 有可复制代码卡片", len(codes) >= 1, f"{len(codes)} 个")

print("== 网络 / 卷命令（取自分类页章节）==")
for nm in ("network ls", "network create", "network disconnect",
           "volume ls", "volume inspect", "volume rm"):
    r = [e for e in store.entries("docker") if e["name"] == nm]
    check(f"{nm} 词条存在", bool(r))
    if not r:
        continue
    e = r[0]
    # 章节切分：正文应只含该子命令，不应把整个分类页塞进来
    other = [x for x in ("network rm", "network connect", "volume rm", "volume create")
             if x != nm and x in e["content"]]
    check(f"  {nm}: 正文只含本命令章节", len(e["content"]) > 40 and not other,
          f"{len(e['content'])} 字，混入其他命令 {other}")
    check(f"  {nm}: 有示例代码", "```" in e["content"] or e["example"].strip(),
          e["example"][:40].replace("\n", " / "))

print("== 搜索 ==")
win.top.search.setText("容器")
app.processEvents()
check("搜索「容器」命中多条", len(win.items) >= 8, f"{len(win.items)} 条")
win.top.search.setText("docker")
app.processEvents()
check("搜索 docker 有命中", len(win.items) >= 1, f"{len(win.items)} 条")
win.top.search.clear()
app.processEvents()

print("== 与既有分类共存 ==")
for k, n in (("cheatsheet", 168), ("commmanual", 441), ("shell", 12), ("manual", 15)):
    check(f"{k} 仍为 {n} 条", store.category_entry_count(k) == n,
          str(store.category_entry_count(k)))
win.show_category("settings")
app.processEvents()
rows = [win.settings_page.catList.item(i).data(Qt.UserRole)
        for i in range(win.settings_page.catList.count())]
check("分类管理列表含 Docker", "docker" in rows, str(rows))
check("分类管理行数与数据库一致", len(rows) == len(store.categories(with_settings=False)),
      f"{len(rows)} vs {len(store.categories(with_settings=False))}")
win.show_category("docker")
app.processEvents()

store.close()
print("\n结果:", "全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
