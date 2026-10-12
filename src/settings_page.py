#!/usr/bin/env python3
"""设置页：外观、分类管理、数据、导入导出、删除记录、浏览历史、关于。

卡片与行的颜色一律由全局 QSS 的 cls 选择器控制，这里不写死任何颜色，
切换主题时自动跟随，避免深色模式下出现白底黑字。
"""
import json
import os
import subprocess
import time

from PyQt5.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
                             QInputDialog)

import icons
import theme
from marquee import MarqueeLabel


class CategoryListWidget(QListWidget):
    drop_finished = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.drop_finished.emit()


def card(title, hint=""):
    c = QFrame()
    c.setProperty("cls", "card")
    lay = QVBoxLayout(c)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(9)
    t = QLabel(title)
    t.setProperty("cls", "cardTitle")
    lay.addWidget(t)
    if hint:
        h = QLabel(hint)
        h.setProperty("cls", "cardDesc")
        h.setWordWrap(True)
        lay.addWidget(h)
    return c, lay


def lab(text, cls="hint", wrap=False):
    lb = QLabel(text)
    lb.setProperty("cls", cls)
    lb.setWordWrap(wrap)
    return lb


class SettingsPage(QWidget):
    theme_requested = pyqtSignal()
    reloaded = pyqtSignal()
    open_entry = pyqtSignal(int)
    font_changed = pyqtSignal(float)
    restored = pyqtSignal(int)
    categories_changed = pyqtSignal()

    def __init__(self, store, app_dir, parent=None):
        super().__init__(parent)
        self.store = store
        self.app_dir = app_dir
        self.mode = store.setting("theme", "light")
        self.pal = theme.palette(self.mode)
        self.setObjectName("detailInner")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(12)

        t = QLabel("设置")
        t.setProperty("cls", "pageTitle")
        lay.addWidget(t)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setObjectName("detailArea")
        inner = QWidget()
        inner.setObjectName("settingsInner")
        self.innerLay = QVBoxLayout(inner)
        self.innerLay.setContentsMargins(0, 0, 8, 0)
        self.innerLay.setSpacing(12)
        area.setWidget(inner)
        lay.addWidget(area, 1)

        self._build_appearance(inner)
        self._build_categories(inner)
        self._build_data(inner)
        self._build_transfer(inner)
        self._build_trash(inner)
        self._build_history(inner)
        self._build_about(inner)
        self.innerLay.addStretch(1)

    # ----------------------------------------------------------- 外观
    def _build_appearance(self, parent):
        c, lay = card("外观", "主题与字号会立即生效并保存。快捷键 Ctrl+R 可快速切换主题。")
        row = QHBoxLayout()
        self.themeBtn = QPushButton("切换到深色")
        self.themeBtn.setProperty("cls", "primary")
        self.themeBtn.setCursor(Qt.PointingHandCursor)
        self.themeBtn.clicked.connect(self.theme_requested.emit)
        row.addWidget(self.themeBtn)
        row.addSpacing(14)
        row.addWidget(lab("字号", "formLabel"))
        self.fontSel = QComboBox()
        self.fontSel.setProperty("cls", "form")
        for pt in (7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 13):
            self.fontSel.addItem(f"{pt} pt", pt)
        cur = float(self.store.setting("font_pt", "10.5"))
        idx = self.fontSel.findData(cur)
        self.fontSel.setCurrentIndex(idx if idx >= 0 else 2)
        self.fontSel.currentIndexChanged.connect(
            lambda: self.font_changed.emit(float(self.fontSel.currentData())))
        row.addWidget(self.fontSel)
        row.addStretch(1)
        lay.addLayout(row)
        parent.layout().addWidget(c)

    # ----------------------------------------------------------- 分类管理
    def _build_categories(self, parent):
        c, lay = card("分类管理",
                      "可自行增加知识库分类，新增后出现在顶部横向页；"
                      "按住行左右拖动即可改变分类顺序；删除分类时其词条进入「删除记录」，可恢复。")
        row = QHBoxLayout()
        self.newCat = QLineEdit()
        self.newCat.setProperty("cls", "form")
        self.newCat.setPlaceholderText("新分类名称，如：MySQL 命令 / Docker 速查 / 网络排查")
        self.newCat.returnPressed.connect(self._add_category)
        row.addWidget(self.newCat, 1)
        b = QPushButton("添加分类")
        b.setProperty("cls", "primary")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(self._add_category)
        row.addWidget(b)
        lay.addLayout(row)

        self.catList = CategoryListWidget()
        self.catList.setDragDropMode(QAbstractItemView.InternalMove)
        self.catList.setDefaultDropAction(Qt.MoveAction)
        self.catList.setDragEnabled(True)
        self.catList.viewport().setAcceptDrops(True)
        self.catList.setDropIndicatorShown(True)
        self.catList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.catList.setSortingEnabled(False)      # 保持手动/拖拽顺序
        self.catList.setMinimumHeight(148)
        self.catList.setSpacing(2)
        self.catList.setToolTip("按住某一行拖动可调整分类顺序")
        # 内部拖放的落地路径不唯一：有的走 rowsMoved，有的走「删除 + 插入」，
        # 只挂 rowsMoved 会出现拖完了数据库没写、tabBar 不跟着变。三路都挂上。
        m = self.catList.model()
        m.rowsMoved.connect(self._queue_commit)
        m.rowsRemoved.connect(self._queue_commit)
        m.rowsInserted.connect(self._queue_commit)
        self.catList.drop_finished.connect(self._queue_commit)
        lay.addWidget(self.catList)
        parent.layout().addWidget(c)

    def _queue_commit(self):
        QTimer.singleShot(0, self._commit_cat_order)

    def _add_category(self):
        name = self.newCat.text().strip()
        if not name:
            QMessageBox.information(self, "提示", "请先输入分类名称。")
            self.newCat.setFocus()
            return
        cid, err = self.store.add_category_named(name)
        if err:
            QMessageBox.warning(self, "无法添加", err)
            return
        self.newCat.clear()
        self.categories_changed.emit()
        self.refresh()
        QMessageBox.information(self, "已添加",
                                f"分类「{name}」已加入顶部横向页，可直接新增词条。")

    def _rename_category(self, cid, cur):
        name, ok = QInputDialog.getText(self, "重命名分类", "新的分类名称：", text=cur)
        if ok and name.strip() and name.strip() != cur:
            self.store.rename_category(cid, name.strip())
            self.categories_changed.emit()
            self.refresh()

    def _delete_category(self, cid, name, n):
        if QMessageBox.question(
                self, "删除分类 · 第 1 步（共 2 步）",
                f"确定删除分类「{name}」？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        if QMessageBox.question(
                self, "删除分类 · 第 2 步（共 2 步）",
                f"再次确认：删除「{name}」及其 {n} 条词条。\n\n"
                "词条会移入「删除记录」，可以在那里逐条恢复。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        k = self.store.delete_category(cid, keep_in_trash=True)
        self.categories_changed.emit()
        self.refresh()
        QMessageBox.information(self, "已删除",
                                f"分类「{name}」已删除，{k} 条词条进入删除记录。")

    def _commit_cat_order(self):
        """拖拽结束后把列表顺序写回数据库 sort 字段。"""
        keys = [self.catList.item(i).data(Qt.UserRole)
                for i in range(self.catList.count())]
        keys = [k for k in keys if k]
        if len(keys) < 2:
            return
        # 顺序没变就不写库，避免重建列表时触发无谓刷新
        if keys == [c["key"] for c in self.store.categories(with_settings=False)]:
            return
        self.store.reorder_categories(keys)
        self.categories_changed.emit()

    def _refresh_categories(self):
        self.catList.blockSignals(True)
        # clear() 不会立刻回收 itemWidget，先显式摘除，避免残留控件累积
        for i in range(self.catList.count()):
            it = self.catList.item(i)
            w = self.catList.itemWidget(it)
            if w:
                w.setParent(None)
                w.deleteLater()
        self.catList.clear()
        for c in self.store.categories(with_settings=False):
            it = QListWidgetItem()
            it.setData(Qt.UserRole, c["key"])
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(9, 5, 9, 5)
            row.setSpacing(9)
            g = QLabel()
            g.setPixmap(icons.grip(self.pal["text3"], 16).pixmap(14, 14))
            g.setToolTip("按住拖动可排序")
            row.addWidget(g)
            nm = MarqueeLabel(c["name"])
            nm.setProperty("cls", "rowName")
            row.addWidget(nm, 1)
            n = self.store.category_entry_count(c["key"])
            row.addWidget(lab(f"{n} 条", "rowMeta"))
            rb = QPushButton("重命名")
            rb.setProperty("cls", "ghost")
            rb.setCursor(Qt.PointingHandCursor)
            rb.clicked.connect(
                lambda _, i=c["id"], t=c["name"]: self._rename_category(i, t))
            row.addWidget(rb)
            db = QPushButton("删除")
            db.setProperty("cls", "danger")
            db.setCursor(Qt.PointingHandCursor)
            db.clicked.connect(
                lambda _, i=c["id"], t=c["name"], k=n: self._delete_category(i, t, k))
            row.addWidget(db)
            w.setLayout(row)
            it.setSizeHint(w.sizeHint())
            self.catList.addItem(it)
            self.catList.setItemWidget(it, w)
        self.catList.blockSignals(False)

    # ----------------------------------------------------------- 删除记录
    def _build_trash(self, parent):
        c, lay = card("删除记录",
                      "删除的词条保留完整快照，点击条目即可恢复到原分类（保留最近 200 条）。")
        self.trashBox = QVBoxLayout()
        self.trashBox.setSpacing(4)
        lay.addLayout(self.trashBox)
        row = QHBoxLayout()
        b = QPushButton("清空删除记录")
        b.setProperty("cls", "danger")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(self._clear_trash)
        row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        parent.layout().addWidget(c)

    def _clear_trash(self):
        n = self.store.trash_count()
        if n == 0:
            QMessageBox.information(self, "提示", "删除记录已是空的。")
            return
        if QMessageBox.question(
                self, "清空删除记录",
                f"确定清空 {n} 条删除记录？清空后无法恢复。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.store.clear_trash()
        self.refresh()

    def _restore(self, trash_id, name):
        nid = self.store.restore_from_trash(trash_id)
        self.refresh()
        if nid:
            self.restored.emit(nid)
            QMessageBox.information(self, "已恢复", f"「{name}」已恢复到原分类。")

    def _refresh_trash(self):
        while self.trashBox.count():
            it = self.trashBox.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        items = self.store.trash_list(20)
        if not items:
            self.trashBox.addWidget(lab("暂无删除记录", "hint"))
        for t in items:
            b = QPushButton(f"↩ 恢复    {t['name']}    ·    "
                            f"{t.get('category_name') or '?'} › "
                            f"{t.get('group_name') or '未分组'}    ·    删除于 {t['deleted_at']}")
            b.setProperty("cls", "ghost")
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, i=t["trash_id"], nm=t["name"]: self._restore(i, nm))
            self.trashBox.addWidget(b)

    # ----------------------------------------------------------- 数据
    def _build_data(self, parent):
        c, lay = card("数据", "所有内容存放在本地 SQLite 数据库中，可离线使用。")
        self.statLabel = lab("", "rowMeta", wrap=True)
        lay.addWidget(self.statLabel)
        row = QHBoxLayout()
        self.openBtn = QPushButton("打开数据库所在目录")
        self.openBtn.setProperty("cls", "ghost")
        self.openBtn.setCursor(Qt.PointingHandCursor)
        self.openBtn.clicked.connect(self._open_dir)
        row.addWidget(self.openBtn)
        row.addStretch(1)
        lay.addLayout(row)
        parent.layout().addWidget(c)

    def _open_dir(self):
        d = os.path.dirname(os.path.abspath(self.store.db_path))
        try:
            subprocess.Popen(["xdg-open", d], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            QMessageBox.information(self, "数据库目录", d)

    # ----------------------------------------------------------- 导入导出
    def _build_transfer(self, parent):
        c, lay = card("导入与导出",
                      "导出为 JSON 便于备份与分享；导入可选择合并追加或整体覆盖。")
        row = QHBoxLayout()
        b1 = QPushButton("导出 JSON 备份")
        b1.setProperty("cls", "primary")
        b1.setCursor(Qt.PointingHandCursor)
        b1.clicked.connect(self._export)
        row.addWidget(b1)
        b2 = QPushButton("导入 JSON（合并）")
        b2.setProperty("cls", "ghost")
        b2.setCursor(Qt.PointingHandCursor)
        b2.clicked.connect(lambda: self._import(merge=True))
        row.addWidget(b2)
        b3 = QPushButton("导入 JSON（覆盖）")
        b3.setProperty("cls", "ghost")
        b3.setCursor(Qt.PointingHandCursor)
        b3.clicked.connect(lambda: self._import(merge=False))
        row.addWidget(b3)
        b4 = QPushButton("恢复初始数据")
        b4.setProperty("cls", "danger")
        b4.setCursor(Qt.PointingHandCursor)
        b4.clicked.connect(self._reset)
        row.addWidget(b4)
        row.addStretch(1)
        lay.addLayout(row)
        parent.layout().addWidget(c)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出备份",
            os.path.expanduser(f"~/linux手册备份-{time.strftime('%Y%m%d')}.json"),
            "JSON 文件 (*.json)")
        if not path:
            return
        n = self.store.export_json(path)
        QMessageBox.information(self, "导出完成", f"已导出 {n} 条词条到\n{path}")

    def _import(self, merge):
        path, _ = QFileDialog.getOpenFileName(self, "导入 JSON",
                                              os.path.expanduser("~"),
                                              "JSON 文件 (*.json)")
        if not path:
            return
        if not merge:
            if QMessageBox.question(self, "覆盖导入",
                                    "覆盖导入会清空当前全部词条，确定继续？",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No) != QMessageBox.Yes:
                return
        try:
            self.store.import_json(path, replace=not merge)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "导入失败", f"JSON 解析失败：{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
            return
        self.reloaded.emit()
        QMessageBox.information(self, "导入完成",
                                "词条已导入数据库。" if merge else "数据库已按导入文件重建。")

    def _reset(self):
        if QMessageBox.question(self, "恢复初始数据",
                                "将清空当前词条并重新灌入初始种子数据，确定继续？",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        seed = os.path.join(self.app_dir, "data", "seed.json")
        if not os.path.exists(seed):
            QMessageBox.warning(self, "缺少种子", f"未找到种子文件：\n{seed}")
            return
        self.store.seed_from_json(seed, replace=True)
        self.reloaded.emit()
        QMessageBox.information(self, "完成", "已恢复初始数据。")

    # ----------------------------------------------------------- 历史
    def _build_history(self, parent):
        c, lay = card("浏览历史", "记录最近浏览的词条，点击可直接打开。")
        self.histBox = QVBoxLayout()
        self.histBox.setSpacing(4)
        lay.addLayout(self.histBox)
        row = QHBoxLayout()
        hb = QPushButton("清空浏览历史")
        hb.setProperty("cls", "ghost")
        hb.setCursor(Qt.PointingHandCursor)
        hb.clicked.connect(self._clear_history)
        row.addWidget(hb)
        row.addStretch(1)
        lay.addLayout(row)
        parent.layout().addWidget(c)

    def _clear_history(self):
        self.store.clear_history()
        self.refresh()

    # ----------------------------------------------------------- 关于
    def _build_about(self, parent):
        c, lay = card("关于")
        txt = ("Linux 手册 · 单机离线版\n\n"
               "· 数据：本地 SQLite（data/linux.db），支持增删改、收藏、全文搜索\n"
               "· 内容来源：本地《Linux 命令速查表》+ 菜鸟教程 runoob.com 公开页面\n"
               "· 快捷键：Ctrl+F 搜索 · Ctrl+N 新增 · Ctrl+R 切换主题 · "
               "Ctrl+1~9 切换分类 · Ctrl+0 设置 · Esc 清空搜索\n"
               "· 单实例运行：重复启动会自动聚焦已打开的窗口")
        lab_txt = lab(txt, "cardDesc", wrap=True)
        lab_txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(lab_txt)
        parent.layout().addWidget(c)

    # ----------------------------------------------------------- 刷新
    def set_mode(self, mode):
        """主题切换：颜色交给全局 QSS，这里只更新自绘部分与按钮文字。"""
        self.mode = mode
        self.pal = theme.palette(mode)
        self.themeBtn.setText("切换到浅色" if mode == "dark" else "切换到深色")
        for w in self.catList.findChildren(QLabel):
            pm = w.pixmap()
            if pm and not pm.isNull() and w.toolTip() == "按住拖动可排序":
                w.setPixmap(icons.grip(self.pal["text3"], 16).pixmap(14, 14))

    def refresh(self):
        s = self.store.stats()
        per = "，".join(f"{k} {v}" for k, v in s["per_category"].items() if k != "settings")
        self.statLabel.setText(
            f"数据库：{self.store.db_path}\n"
            f"词条 {s['entries']} 条 · 分组 {s['groups']} 个 · 收藏 {s['fav']} 条 "
            f"· 文件大小 {s['db_size_kb']} KB\n分类分布：{per}")

        while self.histBox.count():
            it = self.histBox.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        hist = self.store.history(12)
        if not hist:
            self.histBox.addWidget(lab("暂无浏览记录", "hint"))
        for h in hist:
            b = QPushButton(f"{h['viewed_at']}   ·   {h['category_name']} › {h['name']}")
            b.setProperty("cls", "ghost")
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, i=h["id"]: self.open_entry.emit(i))
            self.histBox.addWidget(b)
        self.set_mode(self.store.setting("theme", "light"))
        self._refresh_categories()
        self._refresh_trash()
