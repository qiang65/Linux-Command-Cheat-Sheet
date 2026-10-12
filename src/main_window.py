#!/usr/bin/env python3
"""主窗口：顶部横向分类页 + 左侧纵向分组词条列表 + 右侧详情。"""
import os
import re

from PyQt5.QtCore import Qt, pyqtSignal, QSize, QByteArray, QRect, QTimer, QEvent
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QPen, QFontMetrics
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
                             QStatusBar, QToolButton, QVBoxLayout, QWidget,
                             QApplication, QInputDialog, QMessageBox, QSplitter)

import icons
import theme
import markdown_view
from marquee import MarqueeLabel
from editor import EntryDialog
from settings_page import SettingsPage


# ------------------------------------------------------------------ 分组标题
class GroupHeader(QFrame):
    """自绘分组标题：整行可点击折叠/展开。

    不用 QPushButton + 内嵌布局，因为子控件会吃掉点击事件，导致 clicked 不触发。
    """

    clicked = pyqtSignal()

    def __init__(self, name, count, pal, collapsed=True, parent=None):
        super().__init__(parent)
        self.name = name
        self.count = count
        self.pal = pal
        self.collapsed = collapsed
        self._hover = False
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setToolTip("点击展开 / 收起该组词条")
        # 名称过长时鼠标停留跑马灯滚动显示
        self._off = 0
        self._marquee = QTimer(self)
        self._marquee.setInterval(120)
        self._marquee.timeout.connect(self._tick)

    def _text(self):
        return f"{'▸' if self.collapsed else '▾'}  {self.name[self._off:]}"

    def _overflow(self):
        f = QFont(self.font())
        f.setBold(True)
        fm = QFontMetrics(f)
        full = f"{'▸' if self.collapsed else '▾'}  {self.name}"
        return fm.horizontalAdvance(full) > self.width() - 145

    def enterEvent(self, ev):
        self._hover = True
        if self._overflow():
            self._off = 0
            self._marquee.start()
        self.update()

    def leaveEvent(self, ev):
        self._hover = False
        self._marquee.stop()
        self._off = 0
        self.update()

    def _tick(self):
        self._off += 2
        if self._off > len(self.name):
            self._marquee.stop()
            self._off = 0
        self.update()

    def set_collapsed(self, c):
        self.collapsed = c
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(self.pal["border2"]), 1))
        p.setBrush(QColor(self.pal["hover"] if self._hover else self.pal["tab"]))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

        f = QFont(self.font())
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(self.pal["accent"] if self._hover else self.pal["text2"]))
        p.drawText(QRect(13, 0, max(40, self.width() - 132), self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self._text())

        f2 = QFont(self.font())
        f2.setPointSizeF(max(7.0, f2.pointSizeF() - 1.5))
        p.setFont(f2)
        p.setPen(QColor(self.pal["text3"]))
        p.drawText(QRect(self.width() - 122, 0, 109, self.height()),
                   Qt.AlignVCenter | Qt.AlignRight, f"{self.count} 条")
        p.end()


# ------------------------------------------------------------------ 列表项
class EntryItem(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, entry, pal, base_pt=10.5, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.pal = pal
        self.base_pt = base_pt
        self.setProperty("cls", "item")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 6, 11, 6)
        lay.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.name = MarqueeLabel(entry["name"])
        self.name.setProperty("cls", "itemName")
        # 字体用 setFont 显式设置：QSS 里设 font-weight 时 sizeHint 按非粗体计算，
        # 粗体实际更宽，末尾字符会被切掉半截
        fn = QFont(self.font())
        fn.setPointSizeF(base_pt + 0.5)
        fn.setBold(True)
        self.name.setFont(fn)
        self.name.setMinimumHeight(QFontMetrics(fn).height() + 4)
        # 纯文本：命令名里有 | > < && !! 等符号，富文本会被当作 HTML 解析导致显示异常
        self.name.setTextFormat(Qt.PlainText)
        self.name.set_full(entry["name"])
        self.name.setTextInteractionFlags(Qt.NoTextInteraction)
        col.addWidget(self.name)
        summ = (entry.get("summary") or "").replace("\n", " ").strip()
        summ = summ.replace("**", "").replace("`", "")
        summ = re.sub(r"\s+", " ", summ)
        sub = MarqueeLabel(summ)
        sub.setProperty("cls", "itemSum")
        fs = QFont(self.font())
        fs.setPointSizeF(max(7.0, base_pt - 1.5))
        sub.setFont(fs)
        sub.setTextFormat(Qt.PlainText)
        sub.set_full(summ)
        sub.setToolTip(summ)
        sub.setTextInteractionFlags(Qt.NoTextInteraction)
        sub.setFixedHeight(18)
        self.summary = sub
        col.addWidget(sub)
        lay.addLayout(col, 1)

        self.star = QLabel("★" if entry.get("fav") else "")
        self.star.setProperty("cls", "itemFav")
        self.star.setFixedWidth(16)
        self.star.setAlignment(Qt.AlignTop | Qt.AlignRight)
        lay.addWidget(self.star)

    def paintEvent(self, ev):
        super().paintEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self.entry["id"])
        super().mousePressEvent(ev)

    def set_active(self, on):
        self.setProperty("active", "1" if on else None)
        self.style().unpolish(self)
        self.style().polish(self)

    def refresh_fav(self):
        self.star.setText("★" if self.entry.get("fav") else "")


# ------------------------------------------------------------------ 顶部栏
class TabBar(QFrame):
    """横向分类栏：左右箭头 + 可横向滚动的分类按钮。

    分类多时不会挤压搜索框，用箭头左右翻看。
    """

    tab_changed = pyqtSignal(str)

    def __init__(self, pal, parent=None):
        super().__init__(parent)
        self.pal = pal
        self.tabs = {}
        self.active = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        self.left = QToolButton()
        self.left.setProperty("cls", "arrow")
        self.left.setAutoRaise(True)
        self.left.setCursor(Qt.PointingHandCursor)
        self.left.setToolTip("查看左侧分类")
        self.left.clicked.connect(lambda: self._shift(-1))
        lay.addWidget(self.left)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(38)
        self.inner = QWidget()
        self.tabsLay = QHBoxLayout(self.inner)
        self.tabsLay.setContentsMargins(2, 0, 2, 0)
        self.tabsLay.setSpacing(6)
        self.tabsLay.addStretch(1)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)

        self.right = QToolButton()
        self.right.setProperty("cls", "arrow")
        self.right.setAutoRaise(True)
        self.right.setCursor(Qt.PointingHandCursor)
        self.right.setToolTip("查看右侧分类")
        self.right.clicked.connect(lambda: self._shift(1))
        lay.addWidget(self.right)

        self.bar = self.scroll.horizontalScrollBar()
        self.bar.valueChanged.connect(self._sync)
        # 分类增删会改变滚动范围，必须一并同步，否则箭头状态停留在旧值
        self.bar.rangeChanged.connect(self._sync)
        # 鼠标滚轮直接左右翻看分类
        self.scroll.viewport().installEventFilter(self)
        self.inner.installEventFilter(self)

    def resizeEvent(self, ev):
        self._sync()
        super().resizeEvent(ev)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel:
            d = ev.angleDelta().y() or ev.angleDelta().x()
            if d:
                step = max(60, int(self.scroll.width() * 0.25))
                self.bar.setValue(self.bar.value() - int(d / 120) * step)
                self._sync()
            return True
        return super().eventFilter(obj, ev)

    def set_pal(self, pal):
        self.pal = pal
        self._sync()

    def rebuild(self, cats, active=None):
        """分类增删后重建按钮。"""
        while self.tabsLay.count():
            it = self.tabsLay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.tabs = {}
        for c in cats:
            b = QPushButton(c["name"])
            b.setProperty("cls", "tab")
            b.setCheckable(True)
            # 不用 autoExclusive：Qt 的互斥按钮组不允许全部取消选中，
            # 进设置页时旧分类按钮会灭不掉。互斥交给 set_active() 手动保证。
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, k=c["key"]: self.tab_changed.emit(k))
            b.installEventFilter(self)      # 滚轮落在按钮上也能左右移动
            self.tabs[c["key"]] = b
            self.tabsLay.insertWidget(max(0, self.tabsLay.count() - 1), b)
        if active and active in self.tabs:
            self.set_active(active)
        else:
            self._sync()
        QTimer.singleShot(80, self._sync)

    def set_active(self, key):
        self.active = key
        for k, b in self.tabs.items():
            b.setChecked(k == key)
        b = self.tabs.get(key)
        if b is not None:
            # 让选中项保持可见
            if b.x() < self.bar.value():
                self.bar.setValue(max(0, b.x() - 6))
            elif b.x() + b.width() > self.bar.value() + self.scroll.width():
                self.bar.setValue(b.x() + b.width() - self.scroll.width() + 8)
        self._sync()

    def _shift(self, direction):
        step = max(140, int(self.scroll.width() * 0.7))
        self.bar.setValue(self.bar.value() + direction * step)
        self._sync()

    def _sync(self):
        v, mx = self.bar.value(), self.bar.maximum()
        l_on, r_on = v > 1, v < mx - 1
        self.left.setEnabled(l_on)
        self.right.setEnabled(r_on)
        self.left.setIcon(icons.chevron(
            True, self.pal["text2"] if l_on else self.pal["text3"], 16))
        self.right.setIcon(icons.chevron(
            False, self.pal["text2"] if r_on else self.pal["text3"], 16))


class TopBar(QFrame):
    tab_changed = pyqtSignal(str)
    search_changed = pyqtSignal(str)
    new_entry = pyqtSignal()
    toggle_theme = pyqtSignal()
    open_settings = pyqtSignal()

    def __init__(self, store, pal, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.store = store
        self.pal = pal
        self.mode = "light"
        self.setFixedHeight(66)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(9)

        # 应用图标用自绘矢量：本机只有位图版 emoji 字体，emoji 字符会显示成残缺方框
        logo = QLabel()
        logo.setPixmap(icons.logo(32).pixmap(32, 32))
        logo.setFixedSize(32, 32)
        lay.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel("Linux 手册")
        t.setObjectName("appTitle")
        s = QLabel("命令速查 · Shell · 参考手册")
        s.setObjectName("appSub")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col)
        lay.addSpacing(14)

        self.tabbar = TabBar(pal)
        self.tabbar.tab_changed.connect(self.tab_changed.emit)
        lay.addWidget(self.tabbar, 1)

        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("搜索命令、参数、教程…  (Ctrl+F)")
        self.search.setFixedWidth(225)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.search_changed.emit)
        lay.addWidget(self.search)

        nb = QPushButton(" 新增词条")
        nb.setProperty("cls", "primary")
        nb.setIcon(icons.plus("#ffffff", 14))
        nb.setCursor(Qt.PointingHandCursor)
        nb.clicked.connect(self.new_entry.emit)
        lay.addWidget(nb)

        # 设置按钮从横向分类栏抽出，放在右上角
        self.settings_btn = QToolButton()
        self.settings_btn.setProperty("cls", "icon")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setAutoRaise(True)
        self.settings_btn.setToolTip("设置 (Ctrl+0)")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings.emit)
        lay.addWidget(self.settings_btn)

        self.theme_btn = QToolButton()
        self.theme_btn.setProperty("cls", "icon")
        self.theme_btn.setAutoRaise(True)
        self.theme_btn.setToolTip("切换浅色 / 深色主题 (Ctrl+R)")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme.emit)
        lay.addWidget(self.theme_btn)

        self.tabbar.rebuild(store.categories(with_settings=False))
        self.set_theme(self.mode, pal)

    def set_theme(self, mode, pal):
        """主题变化时重绘所有矢量图标。"""
        self.mode = mode
        self.pal = pal
        self.tabbar.set_pal(pal)
        self.settings_btn.setIcon(icons.gear(pal["text2"], 19))
        self.theme_btn.setIcon(icons.moon(pal["text2"], 19) if mode == "light"
                               else icons.sun(pal["text2"], 19))

    def set_tab(self, key):
        if key == "settings":
            self.tabbar.set_active(None)
            self.settings_btn.setChecked(True)
        else:
            self.tabbar.set_active(key)
            self.settings_btn.setChecked(False)

    @property
    def tabs(self):
        return self.tabbar.tabs


# ------------------------------------------------------------------ 主窗口
class MainWindow(QMainWindow):
    def __init__(self, store, app_dir):
        super().__init__()
        self.store = store
        self.app_dir = app_dir
        self.mode = store.setting("theme", "light")
        self.base_pt = float(store.setting("font_pt", "10.5"))
        self.cat = store.setting("last_cat", "cheatsheet") or "cheatsheet"
        self.current_id = None
        self.items = {}
        self.expanded = set()      # 展开的分组 id；默认空 = 全部收起
        self.pal = theme.palette(self.mode)

        self.setWindowTitle("Linux 手册 · 命令速查 / Shell 教程 / 参考手册")
        self.resize(1280, 820)
        self.setMinimumSize(940, 620)
        icon = os.path.join(app_dir, "assets", "icon.svg")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self.top = TopBar(store, self.pal)
        self.top.tab_changed.connect(self.show_category)
        self.top.search_changed.connect(self.on_search)
        self.top.new_entry.connect(self.new_entry)
        self.top.toggle_theme.connect(self.toggle_theme)
        self.top.open_settings.connect(lambda: self.show_category("settings"))
        rl.addWidget(self.top)

        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)

        # 内容页：左右区域可通过分隔条调整宽度
        self.content = QSplitter(Qt.Horizontal)
        self.content.setObjectName("contentSplitter")
        self.content.setHandleWidth(6)
        self.content.setChildrenCollapsible(False)

        self.listPanel = QFrame()
        self.listPanel.setObjectName("listPanel")
        self.listPanel.setMinimumWidth(230)
        self.listPanel.setMaximumWidth(560)
        lp = QVBoxLayout(self.listPanel)
        lp.setContentsMargins(10, 12, 10, 8)
        lp.setSpacing(8)

        head = QHBoxLayout()
        self.listTitle = QLabel("词条")
        self.listTitle.setStyleSheet(
            f"font-weight:800;font-size:{self.base_pt + 2}pt;color:{self.pal['text']};")
        head.addWidget(self.listTitle)
        head.addStretch(1)
        # 图标化小按钮：悬停显示文字说明，把横向空间留给分组名
        self.toggleAllBtn = QToolButton()
        self.toggleAllBtn.setProperty("cls", "mini")
        self.toggleAllBtn.setAutoRaise(True)
        self.toggleAllBtn.setCursor(Qt.PointingHandCursor)
        self.toggleAllBtn.setFixedSize(30, 30)
        self.toggleAllBtn.setToolTip("展开全部")
        self.toggleAllBtn.clicked.connect(self.toggle_all)
        head.addWidget(self.toggleAllBtn)

        self.favBtn = QToolButton()
        self.favBtn.setProperty("cls", "mini")
        self.favBtn.setAutoRaise(True)
        self.favBtn.setCheckable(True)
        self.favBtn.setCursor(Qt.PointingHandCursor)
        self.favBtn.setFixedSize(30, 30)
        self.favBtn.setToolTip("只看收藏")
        self.favBtn.toggled.connect(lambda _: self.rebuild_list())
        head.addWidget(self.favBtn)
        lp.addLayout(head)

        self.listArea = QScrollArea()
        self.listArea.setObjectName("listArea")
        self.listArea.setWidgetResizable(True)
        self.listInner = QWidget()
        self.listInner.setObjectName("listInner")
        self.listLay = QVBoxLayout(self.listInner)
        self.listLay.setContentsMargins(2, 2, 6, 2)
        self.listLay.setSpacing(5)
        self.listLay.addStretch(1)
        self.listArea.setWidget(self.listInner)
        lp.addWidget(self.listArea, 1)
        self.content.addWidget(self.listPanel)

        self.detailArea = QScrollArea()
        self.detailArea.setObjectName("detailArea")
        self.detailArea.setWidgetResizable(True)
        self.detailInner = QWidget()
        self.detailInner.setObjectName("detailInner")
        self.detailLay = QVBoxLayout(self.detailInner)
        self.detailLay.setContentsMargins(20, 18, 20, 18)
        self.detailLay.setSpacing(10)
        self.detailLay.addStretch(1)
        self.detailArea.setWidget(self.detailInner)
        self.detailArea.setMinimumWidth(380)
        self.content.addWidget(self.detailArea)
        self.content.setStretchFactor(0, 0)
        self.content.setStretchFactor(1, 1)
        self.content.setSizes([400, 880])

        self.stack.addWidget(self.content)

        self.settings_page = SettingsPage(store, app_dir)
        self.settings_page.theme_requested.connect(self.toggle_theme)
        self.settings_page.reloaded.connect(self.reload_all)
        self.settings_page.font_changed.connect(self.set_font)
        self.settings_page.open_entry.connect(self.open_from_history)
        self.settings_page.restored.connect(self.on_restored)
        self.settings_page.categories_changed.connect(self.reload_all)
        self.stack.addWidget(self.settings_page)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.statusLabel = QLabel("")
        self.statusLabel.setProperty("cls", "status")
        self.status.addWidget(self.statusLabel)

        self.apply_style()
        self.restore_geometry()
        self.show_category(self.cat, keep_scroll=True)
        self.top.set_tab(self.cat)

    # -------------------------------------------------------------- 单实例 / 记忆
    def restore_geometry(self):
        geo = self.store.setting("geometry")
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
            except Exception:
                pass

    def save_geometry(self):
        try:
            self.store.set_setting(
                "geometry", bytes(self.saveGeometry().toBase64()).decode())
        except Exception:
            pass

    def wake_up(self):
        """被第二个实例唤醒：恢复窗口到前台。"""
        while self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self.update()

    def on_restored(self, entry_id):
        """从删除记录恢复后：刷新列表并跳到该词条。"""
        e = self.store.entry(entry_id)
        if not e:
            return
        key = e.get("category_key") or self.cat
        if key == "settings":
            key = "cheatsheet"
        self.show_category(key)
        self.top.set_tab(key)
        self.expanded.add(e.get("group_id") or 0)
        self.rebuild_list()
        self.show_entry(entry_id, record=False)

    def open_from_history(self, entry_id):
        e = self.store.entry(entry_id)
        if not e:
            return
        key = e.get("category_key") or "cheatsheet"
        self.show_category(key)
        self.top.set_tab(key)
        self.top.search.clear()
        self.show_entry(entry_id)

    def closeEvent(self, ev):
        self.save_geometry()
        super().closeEvent(ev)

    # -------------------------------------------------------------- 样式
    def apply_style(self):
        self.pal = theme.palette(self.mode)
        QApplication.instance().setStyleSheet(theme.qss(self.mode, self.base_pt))
        self.listTitle.setStyleSheet(
            f"font-weight:800;font-size:{self.base_pt + 2}pt;color:{self.pal['text']};")
        self.top.set_theme(self.mode, self.pal)
        self.settings_page.set_mode(self.mode)
        self._sync_toggle_btn()
        self._sync_fav_btn()

    def toggle_theme(self):
        self.setUpdatesEnabled(False)
        try:
            self.mode = "dark" if self.mode == "light" else "light"
            self.store.set_setting("theme", self.mode)
            self.apply_style()
            self.rebuild_list(flush=False)
            if self.current_id:
                self.show_entry(self.current_id, record=False)
            else:
                self.show_placeholder()
            self.settings_page.set_mode(self.mode)
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def set_font(self, pt):
        self.base_pt = pt
        self.store.set_setting("font_pt", pt)
        self.apply_style()
        self.rebuild_list(flush=False)
        if self.current_id:
            self.show_entry(self.current_id, record=False)

    # -------------------------------------------------------------- 分类
    def show_category(self, key, keep_scroll=False):
        self.cat = key
        self.store.set_setting("last_cat", key)
        if key == "settings":
            self.stack.setCurrentIndex(1)
            self.listPanel.hide()
            self.top.set_tab("settings")
            self.settings_page.refresh()
            self.statusLabel.setText("设置 · 外观 / 分类管理 / 数据 / 删除记录 / 浏览历史")
            return
        self.listPanel.show()
        self.stack.setCurrentIndex(0)
        self.top.set_tab(key)          # 高亮必须跟着纵向栏走（快捷键/拖拽排序后同样生效）
        name = next((c["name"] for c in self.store.categories() if c["key"] == key), key)
        self.listTitle.setText(name)
        self.rebuild_list(flush=False)
        self.show_placeholder()

    def reload_all(self):
        """分类/数据变化后刷新顶部按钮与列表。"""
        cats = self.store.categories()
        if self.cat not in [c["key"] for c in cats]:
            self.cat = "cheatsheet"
        self.top.tabbar.rebuild(self.store.categories(with_settings=False),
                                active=self.cat)
        self.top.set_tab(self.cat)
        self.rebuild_list()
        self.show_placeholder()
        self.current_id = None
        self.settings_page.refresh()

    # -------------------------------------------------------------- 列表
    def clear_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _relayout(self, inner):
        """内容变化后强制滚动区域重新计算尺寸，避免出现 0 高度卡片。"""
        if inner.layout() is not None:
            inner.layout().activate()
        inner.updateGeometry()
        QApplication.processEvents()

    def rebuild_list(self, flush=True):
        self.items = {}
        self.clear_layout(self.listLay)
        query = self.top.search.text().strip()
        fav_only = self.favBtn.isChecked()
        total = 0
        groups = self.store.groups(self.cat)
        for g in groups:
            ents = self.store.entries(self.cat, query, fav_only, group_id=g["id"])
            if not ents:
                continue
            total += len(ents)
            # 默认全部收起，鼠标点开才显示；搜索时自动展开
            collapsed = False if query else (g["id"] not in self.expanded)
            header = GroupHeader(g["name"], len(ents), self.pal, collapsed)
            self.listLay.addWidget(header)

            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 4, 0, 0)
            bl.setSpacing(4)
            for e in ents:
                item = EntryItem(e, self.pal, self.base_pt)
                item.clicked.connect(self.show_entry)
                bl.addWidget(item)
                self.items[e["id"]] = item
            box.setVisible(not collapsed)
            self.listLay.addWidget(box)
            header.clicked.connect(
                lambda gid=g["id"], b=box, h=header: self._toggle_group(gid, b, h))

        if total == 0:
            tip = QLabel("没有匹配的词条\n试试其他关键词，或点右上「＋ 新增词条」")
            tip.setProperty("cls", "hint")
            tip.setMargin(18)
            tip.setWordWrap(True)
            self.listLay.addWidget(tip)
        self.listLay.addStretch(1)
        if flush:
            self._relayout(self.listInner)
        elif self.listInner.layout() is not None:
            self.listInner.layout().activate()
            self.listInner.updateGeometry()
        self._sync_toggle_btn()
        self._sync_fav_btn()

        st = f"{self.listTitle.text()} · 共 {total} 条"
        if query:
            st += f" · 搜索「{query}」"
        if fav_only:
            st += " · 只看收藏"
        self.statusLabel.setText(st)

    def _toggle_group(self, gid, box, header):
        will_collapse = box.isVisible()
        box.setVisible(not will_collapse)
        header.set_collapsed(will_collapse)
        if will_collapse:
            self.expanded.discard(gid)
        else:
            self.expanded.add(gid)
        self._relayout(self.listInner)

    def toggle_all(self):
        """一个按钮切换：有展开的组就全收起，否则全展开。"""
        groups = self.store.groups(self.cat)
        any_open = any(g["id"] in self.expanded for g in groups)
        if any_open:
            self.expanded.clear()
        else:
            self.expanded.update(g["id"] for g in groups)
        self.rebuild_list()

    def _sync_toggle_btn(self):
        groups = self.store.groups(self.cat)
        any_open = any(g["id"] in self.expanded for g in groups)
        self.toggleAllBtn.setIcon(icons.chevrons(down=not any_open,
                                                 color=self.pal["text2"], size=18))
        self.toggleAllBtn.setToolTip("收起全部" if any_open else "展开全部")
        self.toggleAllBtn.setAccessibleName(self.toggleAllBtn.toolTip())

    def _sync_fav_btn(self):
        on = self.favBtn.isChecked()
        self.favBtn.setIcon(icons.star(filled=on,
                                       color=self.pal["accent"] if on else self.pal["text2"],
                                       size=17))
        self.favBtn.setToolTip("已只看收藏 · 点击显示全部" if on else "只看收藏")
        self.favBtn.setAccessibleName(self.favBtn.toolTip())

    def on_search(self, _text):
        if self.cat == "settings":
            self.show_category("cheatsheet")
        self.rebuild_list()

    # -------------------------------------------------------------- 详情
    def show_placeholder(self):
        self.current_id = None
        self.clear_layout(self.detailLay)
        card = QFrame()
        card.setObjectName("detailCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(26, 24, 26, 24)
        cl.setSpacing(8)
        t = QLabel("选择左侧词条查看详情")
        t.setProperty("cls", "emptyTitle")
        cl.addWidget(t)
        s = QLabel("· 顶部切换分类页，左侧按分类展开词条列表\n"
                   "· 顶部搜索框可全文检索命令、参数与教程内容\n"
                   "· 词条可新增、编辑、收藏（★ 置顶），示例命令一键复制")
        s.setProperty("cls", "emptyDesc")
        s.setWordWrap(True)
        cl.addWidget(s)
        self.detailLay.addWidget(card)
        self.detailLay.addStretch(1)
        self._relayout(self.detailInner)

    def show_entry(self, entry_id, record=True):
        e = self.store.entry(entry_id)
        if not e:
            self.show_placeholder()
            return
        self.current_id = entry_id
        for i, w in self.items.items():
            w.set_active(i == entry_id)
        if record:
            self.store.view(entry_id)

        self.clear_layout(self.detailLay)
        card = QFrame()
        card.setObjectName("detailCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 22)
        cl.setSpacing(10)

        # 标题行 + 操作按钮
        top = QHBoxLayout()
        title = QLabel(e["name"])
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        top.addWidget(title, 1)
        fav = QPushButton("★ 已收藏" if e["fav"] else "☆ 收藏")
        fav.setProperty("cls", "ghost")
        fav.setCursor(Qt.PointingHandCursor)
        fav.clicked.connect(lambda: self.on_fav(entry_id))
        top.addWidget(fav)
        ed = QPushButton("编辑")
        ed.setProperty("cls", "ghost")
        ed.setCursor(Qt.PointingHandCursor)
        ed.clicked.connect(lambda: self.edit_entry(entry_id))
        top.addWidget(ed)
        dl = QPushButton("删除")
        dl.setProperty("cls", "danger")
        dl.setCursor(Qt.PointingHandCursor)
        dl.clicked.connect(lambda: self.delete_entry(entry_id))
        top.addWidget(dl)
        cl.addLayout(top)

        meta = QFrame()
        meta.setObjectName("metaBar")
        ml = QHBoxLayout(meta)
        ml.setContentsMargins(11, 7, 11, 7)
        ml.setSpacing(6)
        seen = set()
        for txt in (e.get("category_name") or "", e.get("group_name") or "",
                    (e.get("tags") or "").strip()):
            t = (txt or "").strip()
            if t and t not in seen:          # 分组名与标签常同值，去重避免重复显示
                seen.add(t)
                c = QLabel(t)
                c.setProperty("cls", "chip")
                ml.addWidget(c)
        ml.addStretch(1)
        v = QLabel(f"浏览 {e.get('views', 0) + 1} 次 · 更新于 {e.get('updated', '')}")
        v.setObjectName("detailMeta")
        ml.addWidget(v)
        cl.addWidget(meta)

        summ = (e.get("summary") or "").strip()
        # 去重只剥掉正文开头与摘要重复的那一段，其余正文照常渲染。
        # 教程页的摘要就是正文首段，若据此判定整块重复，几千字正文会被一起砍掉。
        body = markdown_view.strip_dup_lead((e.get("content") or "").strip(), summ)
        show_body = bool(body)

        if summ:
            s = QLabel()
            s.setObjectName("detailSummary")
            s.setTextFormat(Qt.RichText)          # 先设格式，再设文本，否则 HTML 会被当字面量显示
            s.setText(markdown_view.inline_html(summ, self.pal))
            s.setWordWrap(True)
            s.setTextInteractionFlags(Qt.TextSelectableByMouse)
            cl.addWidget(s)

        if e.get("note"):
            note = QFrame()
            note.setProperty("cls", "note")
            nl = QHBoxLayout(note)
            nl.setContentsMargins(12, 9, 12, 9)
            note_txt = e["note"].strip()
            if not note_txt.startswith(("⚠", "！", "!")):
                note_txt = "⚠️ " + note_txt
            nt = QLabel(note_txt)
            nt.setProperty("cls", "noteText")
            nt.setWordWrap(True)
            nl.addWidget(nt)
            cl.addWidget(note)

        if e.get("params"):
            lab = QLabel("常用参数")
            lab.setProperty("cls", "h3")
            cl.addWidget(lab)
            cl.addWidget(markdown_view.CodeCard(e["params"], self.pal, "参数"))

        if show_body:
            markdown_view.render(body, cl, self.pal, self.base_pt)
        # 短正文词条（速查表型）把示例单独做成可复制的代码卡片；
        # 长正文教程的代码块已在正文中渲染，避免重复。
        if e.get("example") and len(body) < 300:
            cl.addWidget(markdown_view.CodeCard(e["example"], self.pal, "示例命令"))

        self.detailLay.addWidget(card)
        self.detailLay.addStretch(1)
        self._relayout(self.detailInner)
        self.detailArea.verticalScrollBar().setValue(0)
        self.statusLabel.setText(
            f"{e.get('category_name')} › {e.get('group_name') or '未分组'} › {e['name']}"
            f"  ·  浏览 {e.get('views', 0) + 1} 次")

    # -------------------------------------------------------------- 操作
    def on_fav(self, entry_id):
        self.store.toggle_fav(entry_id)
        if entry_id in self.items:
            self.items[entry_id].entry = self.store.entry(entry_id)
            self.items[entry_id].refresh_fav()
        self.show_entry(entry_id, record=False)

    def new_entry(self):
        if self.cat == "settings":
            self.show_category("cheatsheet")
        dlg = EntryDialog(self.store, self.cat, self.pal, self)
        if dlg.exec_():
            nid = dlg.saved_id()
            self.rebuild_list()
            if nid:
                self.show_entry(nid, record=False)

    def edit_entry(self, entry_id):
        dlg = EntryDialog(self.store, self.cat, self.pal, self, entry_id=entry_id)
        if dlg.exec_():
            self.rebuild_list()
            self.show_entry(entry_id, record=False)

    def delete_entry(self, entry_id):
        e = self.store.entry(entry_id)
        if not e:
            return
        # 第一级确认
        if QMessageBox.question(
                self, "删除词条 · 第 1 步（共 2 步）",
                f"确定要删除词条「{e['name']}」吗？\n"
                f"所属分类：{e.get('category_name')} › {e.get('group_name') or '未分组'}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        # 第二级确认
        if QMessageBox.question(
                self, "删除词条 · 第 2 步（共 2 步）",
                f"再次确认：删除「{e['name']}」。\n\n"
                "词条会移入「设置 › 删除记录」，可以在那里恢复。\n"
                "删除记录保留最近 200 条。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.store.to_trash(entry_id)
        self.items.pop(entry_id, None)
        self.current_id = None
        self.rebuild_list()
        self.show_placeholder()
        self.settings_page.refresh()
        QMessageBox.information(
            self, "已删除",
            f"「{e['name']}」已删除。\n如需恢复：设置 › 删除记录 › 点击该条目。")

    # -------------------------------------------------------------- 快捷键
    def keyPressEvent(self, ev):
        mods = ev.modifiers()
        if mods & Qt.ControlModifier:
            if ev.key() == Qt.Key_F:
                self.top.search.setFocus()
                self.top.search.selectAll()
                return
            if ev.key() == Qt.Key_N:
                self.new_entry()
                return
            if ev.key() == Qt.Key_R:
                self.toggle_theme()
                return
            if ev.key() == Qt.Key_0:
                self.show_category("settings")
                self.top.set_tab("settings")
                return
            if Qt.Key_1 <= ev.key() <= Qt.Key_9:
                keys = [c["key"] for c in self.store.categories(with_settings=False)]
                i = ev.key() - Qt.Key_1
                if i < len(keys):
                    self.show_category(keys[i])
                    self.top.set_tab(keys[i])
                return
        if ev.key() == Qt.Key_Escape and self.top.search.text():
            self.top.search.clear()
            return
        super().keyPressEvent(ev)
