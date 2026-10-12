#!/usr/bin/env python3
"""词条新增 / 编辑对话框。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFrame,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton, QVBoxLayout, QMessageBox)


def _form(rows=2, mono=False):
    w = QPlainTextEdit()
    w.setProperty("cls", "form")
    w.setPlaceholderText("支持 Markdown：## 标题、- 列表、``` 代码块 ```、**加粗**、`行内代码`")
    lh = w.fontMetrics().height()
    w.setFixedHeight(lh * rows + 22)
    if mono:
        from PyQt5.QtGui import QFontDatabase
        f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        w.setFont(f)
    return w


class EntryDialog(QDialog):
    def __init__(self, store, cat_key, pal, parent=None, entry_id=None):
        super().__init__(parent)
        self.store = store
        self.pal = pal
        self.entry_id = entry_id
        self._saved = None
        e = store.entry(entry_id) if entry_id else {}

        self.setWindowTitle("编辑词条" if entry_id else "新增词条")
        self.setModal(True)
        self.resize(760, 700)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)

        title = QLabel("编辑词条：" + (e.get("name") or "") if entry_id else "新增词条")
        title.setProperty("cls", "pageTitle")
        lay.addWidget(title)

        card = QFrame()
        card.setProperty("cls", "card")
        form = QFormLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.name = QLineEdit(e.get("name", ""))
        self.name.setProperty("cls", "form")
        self.name.setPlaceholderText("如 ls / Shell 变量 / 管道与重定向")
        form.addRow(self._lab("名称 *"), self.name)

        self.cat = QComboBox()
        self.cat.setProperty("cls", "form")
        self.cat.setEditable(False)
        cats = store.categories(with_settings=False)
        for c in cats:
            self.cat.addItem(c["name"], c["key"])
        keys = [c["key"] for c in cats]
        want = e.get("category_key") or cat_key
        self.cat.setCurrentIndex(max(0, keys.index(want)) if want in keys else 0)
        self.cat.currentIndexChanged.connect(self._reload_groups)
        form.addRow(self._lab("所属分类"), self.cat)

        self.group = QComboBox()
        self.group.setProperty("cls", "form")
        self.group.setEditable(True)
        self.group.setInsertPolicy(QComboBox.NoInsert)
        self.group.lineEdit().setPlaceholderText("选择分组，或直接输入新分组名")
        form.addRow(self._lab("分组"), self.group)
        self._reload_groups()
        if e.get("group_name"):
            self.group.setEditText(e["group_name"])

        self.summary = _form(rows=2)
        self.summary.setPlainText(e.get("summary", ""))
        self.summary.setPlaceholderText("一句话说明这个命令/知识点做什么")
        form.addRow(self._lab("摘要"), self.summary)

        self.params = _form(rows=3, mono=True)
        self.params.setPlainText(e.get("params", ""))
        self.params.setPlaceholderText("逐行列出常用参数，如：-l  详细信息")
        form.addRow(self._lab("常用参数"), self.params)

        self.example = _form(rows=3, mono=True)
        self.example.setPlainText(e.get("example", ""))
        self.example.setPlaceholderText("示例命令，可多行；详情页可一键复制")
        form.addRow(self._lab("示例"), self.example)

        self.note = QLineEdit(e.get("note", ""))
        self.note.setProperty("cls", "form")
        self.note.setPlaceholderText("风险提示 / 注意事项，如：⚠️ 慎用 rm -rf /")
        form.addRow(self._lab("注意"), self.note)

        self.tags = QLineEdit(e.get("tags", ""))
        self.tags.setProperty("cls", "form")
        self.tags.setPlaceholderText("逗号分隔，如：文件,目录,常用")
        form.addRow(self._lab("标签"), self.tags)

        self.content = _form(rows=10)
        self.content.setPlainText(e.get("content", ""))
        form.addRow(self._lab("正文详情"), self.content)

        lay.addWidget(card)

        row = QHBoxLayout()
        self.delBtn = QPushButton("删除此词条")
        self.delBtn.setProperty("cls", "danger")
        self.delBtn.setVisible(bool(entry_id))
        self.delBtn.clicked.connect(self._delete)
        row.addWidget(self.delBtn)
        row.addStretch(1)
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._save)
        box.rejected.connect(self.reject)
        sb = box.button(QDialogButtonBox.Save)
        sb.setProperty("cls", "primary")
        sb.setText("保存")
        cb = box.button(QDialogButtonBox.Cancel)
        cb.setProperty("cls", "ghost")
        cb.setText("取消")
        for b in box.buttons():
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumWidth(96)
        row.addWidget(box)
        lay.addLayout(row)

        self.name.setFocus()

    def _lab(self, text):
        lb = QLabel(text)
        lb.setProperty("cls", "formLabel")
        return lb

    def _reload_groups(self):
        key = self.cat.currentData()
        cur = self.group.currentText()
        self.group.blockSignals(True)
        self.group.clear()
        for g in self.store.groups(key, only_with_entries=False):
            self.group.addItem(g["name"])
        self.group.setEditText(cur)
        self.group.blockSignals(False)

    def saved_id(self):
        return self._saved

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "提示", "名称不能为空。")
            self.name.setFocus()
            return
        data = {
            "id": self.entry_id,
            "category_key": self.cat.currentData(),
            "group_name": self.group.currentText().strip(),
            "name": self.name.text().strip(),
            "summary": self.summary.toPlainText().strip(),
            "params": self.params.toPlainText().strip(),
            "example": self.example.toPlainText().strip(),
            "note": self.note.text().strip(),
            "tags": self.tags.text().strip(),
            "content": self.content.toPlainText(),
            "source": "手动录入",
        }
        self._saved = self.store.save_entry(data)
        self.accept()

    def _delete(self):
        if not self.entry_id:
            return
        nm = self.name.text()
        if QMessageBox.question(
                self, "删除词条 · 第 1 步（共 2 步）",
                f"确定要删除「{nm}」吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        if QMessageBox.question(
                self, "删除词条 · 第 2 步（共 2 步）",
                f"再次确认：删除「{nm}」。\n\n"
                "词条会移入「设置 › 删除记录」，可以在那里恢复。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.store.to_trash(self.entry_id)
        self.reject()
