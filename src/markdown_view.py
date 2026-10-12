#!/usr/bin/env python3
"""把词条的 Markdown 正文渲染成现代风格组件（含带复制按钮的代码卡片）。"""
import re

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
                             QPushButton, QSizePolicy, QVBoxLayout, QWidget,
                             QApplication)


# ------------------------------------------------------------------ 内联 Markdown
def strip_dup_lead(body, summ):
    """正文开头与摘要重复时，只剥掉重复的那一段，其余正文照常保留。

    教程页的摘要通常就是正文首段，若据此判定"整块正文都是重复"，
    会把后面几千字正文一起砍掉（表现为内容不全）。
    """
    if not body:
        return body
    if not summ:
        return body

    def norm(t):
        return t.replace("**", "").replace("`", "").replace(" ", "").strip()

    nb, ns = norm(body), norm(summ)
    if nb == ns:                      # 正文就是摘要本身
        return ""
    parts = body.split("\n", 1)
    first, rest = parts[0], (parts[1] if len(parts) > 1 else "")
    nf = norm(first)
    # 首段与摘要等价（相等 / 互相包含前缀）→ 只去掉首段
    if nf and (nf == ns
               or (len(ns) > 8 and ns[:8] in nf)
               or (len(nf) > 8 and nf[:8] in ns)):
        return rest.strip()
    return body


def inline_html(text, pal):
    t = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    # Qt 富文本只可靠支持 background-color / color，不支持 background 简写与 border-radius
    t = re.sub(r"`([^`]+)`",
               r'<span style="background-color:%s;color:%s;font-family:monospace;">\1</span>'
               % (pal["accentBg2"], pal["accent2"]), t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    return t


# ------------------------------------------------------------------ 代码卡片
class CodeCard(QFrame):
    """只读代码块 + 一键复制。"""

    def __init__(self, code, pal, caption="示例", parent=None):
        super().__init__(parent)
        self.setProperty("cls", "codeCard")
        self.code = code.rstrip()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(6)

        head = QHBoxLayout()
        cap = QLabel(caption)
        cap.setProperty("cls", "codeHead")
        # 字号与粗体显式设置：QSS 的 font-weight 不反映到 sizeHint，
        # 标题宽度会被低估，"示例"这类短标题会被切字
        cf = QFont(self.font())
        cf.setPointSizeF(max(7.0, self.font().pointSizeF() - 2))
        cf.setBold(True)
        cap.setFont(cf)
        cap.setMinimumWidth(cap.fontMetrics().horizontalAdvance(caption) + 10)
        cap.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        head.addWidget(cap)
        head.addStretch(1)
        self.btn = QPushButton("复制")
        self.btn.setProperty("cls", "copy")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._copy)
        head.addWidget(self.btn)
        lay.addLayout(head)

        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSizeF(mono.pointSizeF() * 0.95)
        self.view = QPlainTextEdit()
        self.view.setProperty("cls", "codeBody")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.view.setFont(mono)
        self.view.setPlainText(self.code)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lay.addWidget(self.view)

        lines = self.code.split("\n")
        lh = self.view.fontMetrics().height()
        rows = min(len(lines), 14)
        self.view.setFixedHeight(rows * lh + 14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _copy(self):
        QApplication.clipboard().setText(self.code)
        self.btn.setText("已复制 ✓")
        self.btn.setProperty("done", "1")
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)
        QTimer.singleShot(1600, self._reset)

    def _reset(self):
        self.btn.setText("复制")
        self.btn.setProperty("done", None)
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)


# ------------------------------------------------------------------ Markdown 分块
def split_blocks(md):
    """把 Markdown 文本切成块：('code'|'h2'|'h3'|'h4'|'list'|'table'|'p', text)。"""
    blocks = []
    lines = (md or "").replace("\r", "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        m = re.match(r"^```(\w*)\s*$", s)
        if m:
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(buf).strip("\n")))
            continue
        m = re.match(r"^(#{2,6})\s+(.*)$", s)
        if m:
            blocks.append((f"h{min(len(m.group(1)), 4)}", m.group(2).strip()))
            i += 1
            continue
        if s.startswith("- ") or re.match(r"^\d+\.\s", s):
            buf = []
            while i < len(lines):
                t = lines[i].strip()
                if t.startswith("- ") or re.match(r"^\d+\.\s", t):
                    buf.append(re.sub(r"^(-|\d+\.)\s+", "", t))
                    i += 1
                elif t == "" and i + 1 < len(lines) and (
                        lines[i + 1].strip().startswith("- ")
                        or re.match(r"^\d+\.\s", lines[i + 1].strip())):
                    i += 1
                else:
                    break
            blocks.append(("list", buf))
            continue
        if s.startswith("|"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                buf.append(lines[i].strip())
                i += 1
            blocks.append(("table", buf))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(
                ("```", "#", "- ", "|")) and not re.match(r"^\d+\.\s", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            blocks.append(("p", " ".join(buf)))
        else:
            # 兜底：未识别的行按段落收下。缺这一步时 i 不前进，
            # 遇到「以 | 开头但不以 | 结尾」的行会死循环卡死界面。
            blocks.append(("p", s))
            i += 1
    return blocks


def table_html(rows, pal):
    cells = []
    for r in rows:
        if re.match(r"^\|[\s:|-]+\|$", r):
            continue
        cells.append([c.strip() for c in r.strip("|").split("|")])
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    bd = f"border:1px solid {pal['border']};padding:4px 9px;"
    out = [f"<table style=\"border-collapse:collapse;width:100%;font-size:9pt;\">"]
    for idx, row in enumerate(cells):
        row = row + [""] * (width - len(row))
        tag = "th" if idx == 0 else "td"
        style = f"{bd}background:{pal['tab']};font-weight:700;" if idx == 0 else bd
        out.append("<tr>" + "".join(
            f"<{tag} style=\"{style}\">{inline_html(c, pal)}</{tag}>" for c in row)
            + "</tr>")
    out.append("</table>")
    return "".join(out)


def render(md, lay, pal, base_pt=10.5, caption="示例"):
    """把 markdown 渲染进给定布局。"""
    for kind, data in split_blocks(md):
        if kind == "code":
            lay.addWidget(CodeCard(data, pal, caption))
        elif kind in ("h2", "h3", "h4"):
            lab = QLabel(data)
            lab.setProperty("cls", kind)
            lab.setWordWrap(True)
            lab.setTextFormat(Qt.RichText)
            lab.setText(inline_html(data, pal))
            lay.addWidget(lab)
        elif kind == "list":
            html = ("<ul style=\"margin:2px 0px 6px 20px;padding-left:0px;\">"
                    + "".join(f"<li style=\"margin:3px 0;\">{inline_html(x, pal)}</li>"
                              for x in data) + "</ul>")
            lab = QLabel()
            lab.setProperty("cls", "body")
            lab.setTextFormat(Qt.RichText)
            lab.setText(html)
            lab.setWordWrap(True)
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(lab)
        elif kind == "table":
            lab = QLabel()
            lab.setProperty("cls", "body")
            lab.setTextFormat(Qt.RichText)
            lab.setText(table_html(data, pal))      # 必须先设格式再设文本
            lab.setWordWrap(True)
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(lab)
        else:
            lab = QLabel()
            lab.setProperty("cls", "body")
            lab.setTextFormat(Qt.RichText)
            lab.setText(inline_html(data, pal))      # 必须先设格式再设文本
            lab.setWordWrap(True)
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(lab)
