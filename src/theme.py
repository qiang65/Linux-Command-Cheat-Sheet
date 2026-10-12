#!/usr/bin/env python3
"""主题：浅色 / 深色两套配色 + 全局 QSS。"""

PALETTES = {
    "light": {
        "win":      "#f4f6f9",
        "card":     "#ffffff",
        "card2":    "#fafbfc",
        "border":   "#e4e8ef",
        "border2":  "#eef1f5",
        "text":     "#1f2937",
        "text2":    "#69707d",
        "text3":    "#98a1ae",
        "accent":   "#16a34a",
        "accent2":  "#15803d",
        "accentBg": "#e7f4ec",
        "accentBg2": "#f1f8f4",
        "code":     "#f7f9fb",
        "codeBorder": "#e6ebf1",
        "warn":     "#fff6e7",
        "warnBorder": "#f2c07a",
        "warnText": "#8a5a12",
        "sel":      "#e3f1e9",
        "hover":    "#f0f3f7",
        "tab":      "#eef1f5",
        "shadow":   "#d8dde5",
        "link":     "#15803d",
    },
    "dark": {
        "win":      "#14181f",
        "card":     "#1b2028",
        "card2":    "#171c23",
        "border":   "#2b323d",
        "border2":  "#242b35",
        "text":     "#e6e9ee",
        "text2":    "#9aa4b2",
        "text3":    "#6f7987",
        "accent":   "#2ecc71",
        "accent2":  "#27ae60",
        "accentBg": "#1c3126",
        "accentBg2": "#18261f",
        "code":     "#11151b",
        "codeBorder": "#2a313c",
        "warn":     "#2b2317",
        "warnBorder": "#5c4620",
        "warnText": "#e8b56a",
        "sel":      "#22301f",
        "hover":    "#222834",
        "tab":      "#1f242d",
        "shadow":   "#0d1014",
        "link":     "#3ddc84",
    },
}


def palette(mode="light"):
    return PALETTES.get(mode, PALETTES["light"])


def qss(mode="light", base_pt=10.5, code_pt=9.0):
    p = palette(mode)
    fam = '"Noto Sans CJK SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "PingFang SC", sans-serif'
    mono = '"DejaVu Sans Mono", "Noto Sans Mono", "Consolas", "Courier New", monospace'
    return f"""
* {{
    font-family: {fam};
    font-size: {base_pt}pt;
    outline: none;
}}
QMainWindow, QWidget#root {{ background: {p['win']}; }}
QToolTip {{
    background: {p['card']}; color: {p['text']};
    border: 1px solid {p['border']}; padding: 5px 8px;
}}

/* ---------------- 顶部栏 ---------------- */
QFrame#topbar {{
    background: {p['card']};
    border-bottom: 1px solid {p['border']};
}}
QLabel#appTitle {{ font-size: {base_pt + 2.5}pt; font-weight: 700; color: {p['accent']}; }}
QLabel#appSub  {{ font-size: {base_pt - 1}pt; color: {p['text3']}; }}

QPushButton[cls="tab"] {{
    background: transparent; color: {p['text2']};
    border: none; border-radius: 9px;
    padding: 8px 16px; font-weight: 600;
}}
QPushButton[cls="tab"]:hover {{ background: {p['hover']}; color: {p['text']}; }}
QPushButton[cls="tab"]:checked {{
    background: {p['accent']}; color: #ffffff;
}}

QLineEdit#search {{
    background: {p['card2']}; color: {p['text']};
    border: 1px solid {p['border']}; border-radius: 9px;
    padding: 7px 12px; selection-background-color: {p['accent']};
}}
QLineEdit#search:focus {{ border: 1px solid {p['accent']}; background: {p['card']}; }}

QPushButton[cls="icon"] {{
    background: {p['card2']}; color: {p['text2']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 6px 11px; font-weight: 600;
}}
QPushButton[cls="icon"]:hover {{ background: {p['hover']}; color: {p['text']}; border-color: {p['accent']}; }}
QPushButton[cls="primary"] {{
    background: {p['accent']}; color: #ffffff;
    border: none; border-radius: 8px; padding: 7px 15px; font-weight: 700;
}}
QPushButton[cls="primary"]:hover {{ background: {p['accent2']}; }}
QPushButton[cls="ghost"] {{
    background: transparent; color: {p['text2']};
    border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 13px;
}}
QPushButton[cls="ghost"]:hover {{ color: {p['accent']}; border-color: {p['accent']}; }}
QPushButton[cls="danger"] {{
    background: transparent; color: #d9534f;
    border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 13px;
}}
QPushButton[cls="danger"]:hover {{ border-color: #d9534f; background: {p['hover']}; }}

QToolButton[cls="icon"] {{
    background: {p['card2']}; color: {p['text2']};
    border: 1px solid {p['border']}; border-radius: 8px;
    min-width: 34px; min-height: 34px; padding: 4px;
}}
QToolButton[cls="icon"]:hover {{ background: {p['hover']}; color: {p['text']}; border-color: {p['accent']}; }}
QToolButton[cls="icon"]:checked {{
    background: {p['accentBg']}; border: 1px solid {p['accent']};
}}

QToolButton[cls="arrow"] {{
    background: transparent; border: none; border-radius: 6px;
    min-width: 26px; min-height: 30px; padding: 2px;
}}
QToolButton[cls="arrow"]:hover {{ background: {p['hover']}; }}
QToolButton[cls="arrow"]:disabled {{ background: transparent; }}

QToolButton[cls="mini"] {{
    background: transparent; border: 1px solid transparent;
    border-radius: 7px; min-width: 26px; min-height: 26px; padding: 2px;
}}
QToolButton[cls="mini"]:hover {{ background: {p['hover']}; border-color: {p['border']}; }}
QToolButton[cls="mini"]:checked {{
    background: {p['accentBg']}; border-color: {p['accent']};
}}

/* ---------------- 左侧词条列表 ---------------- */
QFrame#listPanel {{
    background: {p['card']};
    border-right: 1px solid {p['border']};
}}
QSplitter#contentSplitter::handle:horizontal {{ background: {p['border']}; }}
QSplitter#contentSplitter::handle:horizontal:hover {{ background: {p['accent']}; }}
QScrollArea#listArea {{ background: transparent; border: none; }}
QWidget#listInner {{ background: transparent; }}

QPushButton[cls="group"] {{
    background: {p['tab']}; color: {p['text2']};
    border: 1px solid {p['border2']}; border-radius: 8px;
    padding: 7px 11px; text-align: left; font-weight: 700;
}}
QPushButton[cls="group"]:hover {{ background: {p['hover']}; color: {p['accent']}; }}

QFrame[cls="item"] {{
    background: {p['card']};
    border: 1px solid {p['border2']};
    border-radius: 8px;
}}
QFrame[cls="item"]:hover {{ background: {p['hover']}; border-color: {p['border']}; }}
QFrame[cls="item"][active="1"] {{
    background: {p['sel']}; border: 1px solid {p['accent']};
}}
/* itemName 的字号与粗体由代码 setFont 设置：QSS 里设 font-weight 时，
   QLabel 的 sizeHint 按非粗体计算，粗体实际更宽，末尾字符会被切掉半截 */
QLabel[cls="itemName"] {{ color: {p['text']}; font-size: {base_pt + 0.5}pt; }}
QLabel[cls="itemSum"]  {{ color: {p['text3']}; font-size: {max(7.0, base_pt - 1.5)}pt; }}
QLabel[cls="itemFav"]  {{ color: {p['accent']}; font-size: {base_pt}pt; }}
QLabel[cls="cardTitle"] {{ font-weight:800; font-size:{base_pt + 1.5}pt; color:{p['text']}; }}
QLabel[cls="pageTitle"] {{ font-weight:800; font-size:{base_pt + 4}pt; color:{p['text']}; }}
QLabel[cls="cardDesc"]  {{ color:{p['text2']}; }}
QLabel[cls="rowName"]   {{ font-weight:700; color:{p['text']}; }}
QLabel[cls="rowMeta"]   {{ color:{p['text3']}; }}
QLabel[cls="hint"]      {{ color:{p['text3']}; }}

QFrame[cls="card"] {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 12px;
}}

QListWidget {{
    background: {p['card2']};
    border: 1px solid {p['border']};
    border-radius: 9px;
    padding: 4px;
    color: {p['text']};
    outline: 0;
}}
QListWidget::item {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 7px;
    margin: 2px;
    padding: 2px;
    color: {p['text']};
}}
QListWidget::item:selected {{
    background: {p['accentBg']};
    border: 1px solid {p['accent']};
    color: {p['text']};
}}
QListWidget::item:hover {{ background: {p['hover']}; }}
QListView {{ outline: 0; }}
QLabel[cls="groupCount"] {{ color: {p['text3']}; font-size: {base_pt - 2}pt; }}

/* ---------------- 右侧详情 ---------------- */
QScrollArea#detailArea {{ background: transparent; border: none; }}
QAbstractScrollArea#detailArea::viewport {{ background: {p['win']}; }}
QWidget#settingsInner {{ background: {p['win']}; }}
QWidget#detailInner {{ background: {p['win']}; }}
QFrame#detailCard {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 12px;
}}
QLabel#detailTitle {{ font-size: {base_pt + 9}pt; font-weight: 800; color: {p['text']}; }}
QLabel#detailMeta  {{ font-size: {base_pt - 1}pt; color: {p['text3']}; }}
QLabel[cls="emptyTitle"] {{ font-size: {base_pt + 6}pt; font-weight: 800; color: {p['text']}; }}
QLabel[cls="emptyDesc"]  {{ font-size: {base_pt + 1}pt; color: {p['text2']}; }}
QLabel#detailSummary {{
    font-size: {base_pt + 1}pt; color: {p['text']};
    padding: 4px 0px;
}}
QFrame#metaBar {{ background: {p['card2']}; border: 1px solid {p['border2']}; border-radius: 9px; }}
QLabel[cls="chip"] {{
    background: {p['accentBg']}; color: {p['accent2']};
    border-radius: 7px; padding: 3px 9px; font-size: {base_pt - 1}pt; font-weight: 600;
}}
QLabel[cls="chipGray"] {{
    background: {p['tab']}; color: {p['text2']};
    border-radius: 7px; padding: 3px 9px; font-size: {base_pt - 1}pt;
}}
QFrame[cls="note"] {{
    background: {p['warn']}; border: 1px solid {p['warnBorder']}; border-radius: 9px;
}}
QLabel[cls="noteText"] {{ color: {p['warnText'] }; font-weight: 600; }}

QLabel[cls="h2"] {{ font-size: {base_pt + 3}pt; font-weight: 800; color: {p['text']}; padding-top: 6px; }}
QLabel[cls="h3"] {{ font-size: {base_pt + 1.5}pt; font-weight: 700; color: {p['accent2']}; }}
QLabel[cls="h4"] {{ font-size: {base_pt + 0.5}pt; font-weight: 700; color: {p['text2']}; }}
QLabel[cls="body"] {{ color: {p['text']}; font-size: {base_pt}pt; }}
QLabel[cls="body"] code {{
    background: {p['accentBg2']}; color: {p['accent2']};
    font-family: {mono}; border-radius: 4px;
}}
QLabel[cls="body"] a {{ color: {p['link']}; }}
QLabel[cls="body"] table {{ border-collapse: collapse; }}
QLabel[cls="body"] th, QLabel[cls="body"] td {{
    border: 1px solid {p['border']}; padding: 4px 8px;
}}

/* ---------------- 代码卡片 ---------------- */
QFrame[cls="codeCard"] {{
    background: {p['code']};
    border: 1px solid {p['codeBorder']};
    border-radius: 10px;
}}
QLabel[cls="codeHead"] {{ color: {p['text2']}; font-size: {base_pt - 0.5}pt; font-weight: 700; }}
QPlainTextEdit[cls="codeBody"] {{
    background: transparent; border: none;
    color: {p['text']}; font-family: {mono}; font-size: {code_pt}pt;
    selection-background-color: {p['accentBg']};
}}
QPushButton[cls="copy"] {{
    background: {p['card2']}; color: {p['text2']};
    border: 1px solid {p['border']}; border-radius: 6px;
    padding: 3px 10px; font-size: {base_pt - 1.5}pt; font-weight: 600;
}}
QPushButton[cls="copy"]:hover {{ color: {p['accent']}; border-color: {p['accent']}; }}
QPushButton[cls="copy"][done="1"] {{ color: {p['accent']}; border-color: {p['accent']}; }}

/* ---------------- 状态栏 ---------------- */
QStatusBar {{ background: {p['card']}; border-top: 1px solid {p['border']}; }}
QStatusBar::item {{ border: none; }}
QLabel[cls="status"] {{ color: {p['text3']}; font-size: {base_pt - 1.5}pt; }}

/* ---------------- 对话框 ---------------- */
QDialog {{ background: {p['win']}; }}
QLabel[cls="formLabel"] {{ color: {p['text2']}; font-weight: 700; font-size: {base_pt - 0.5}pt; }}
QLineEdit[cls="form"], QTextEdit[cls="form"], QPlainTextEdit[cls="form"], QComboBox[cls="form"] {{
    background: {p['card']}; color: {p['text']};
    border: 1px solid {p['border']}; border-radius: 8px; padding: 7px 10px;
}}
QLineEdit[cls="form"]:focus, QTextEdit[cls="form"]:focus,
QPlainTextEdit[cls="form"]:focus, QComboBox[cls="form"]:focus {{ border: 1px solid {p['accent']}; }}
QComboBox[cls="form"]::drop-down {{ border: none; width: 22px; }}
QComboBox[cls="form"] QAbstractItemView {{
    background: {p['card']}; color: {p['text']};
    border: 1px solid {p['border']}; selection-background-color: {p['accentBg']};
    selection-color: {p['text']};
}}
QFrame[cls="card"] {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}

/* ---------------- 滚动条 ---------------- */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {p['border']}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {p['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollArea {{ background: transparent; border: none; }}
"""
