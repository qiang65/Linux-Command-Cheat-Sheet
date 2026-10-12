#!/usr/bin/env python3
"""把 runoob.com 文章正文 HTML 提取为干净的 Markdown 文本。

只依赖标准库 html.parser，对 runoob 的脏 HTML（如 <h1>x</h2>）做容错。
"""
import re
from html.parser import HTMLParser

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5}
CODE_MARK = "\x00"                    # 内联代码占位符，避免与 ``` 围栏冲突
NOISE_LINES = {"运行实例 »", "尝试实例 »", "在线实例 »", "实例运行 »"}
SKIP_TAGS = {"script", "style", "noscript", "iframe", "ins", "form", "button",
             "svg", "head", "link", "meta", "select", "option", "nav", "footer"}
CODE_DIV_HINT = ("example_code", "highlight", "hl", "code-box", "pre-scrollable")
AD_HINT = ("adsbygoogle", "ad-", "banner", "sidebar", "comment", "share", "note")


def extract_article(html):
    """返回正文容器内的 HTML 片段（按 div 嵌套平衡截取）。"""
    m = re.search(r'<div[^>]*class="[^"]*article-intro[^"]*"[^>]*>', html)
    if not m:
        m = re.search(r'<div[^>]*id="content"[^>]*>', html)
    if not m:
        return ""
    start = m.end()
    depth = 1
    for tag in re.finditer(r'<(/?)div\b[^>]*>', html[start:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[start:start + tag.start()]
    return html[start:]


class MdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []          # [(kind, text)]
        self.skip = []            # 正在跳过的标签栈
        self.cur_kind = None      # 当前行内块类型
        self.cur = []             # 行内文本缓冲
        self.pre_depth = 0        # >0 表示在代码块内
        self.code_buf = []
        self.list_stack = []
        self.ol_idx = []
        self.rows = None          # 表格所有行
        self.row = None           # 当前行
        self.cell = None          # 当前单元格
        self.div_stack = []       # 记录每个 div 是否为代码容器
        self.bold = 0

    # ---------- 输出 ----------
    def flush(self):
        text = re.sub(r'[ \t\u00a0]+', ' ', ''.join(self.cur)).strip()
        kind = self.cur_kind
        self.cur, self.cur_kind = [], None
        if not text:
            return
        if kind in HEADINGS:
            self.blocks.append((f"h{HEADINGS[kind]}", text))
        elif kind == "li":
            self.blocks.append(("li", "  " * max(0, len(self.list_stack) - 1) + "- " + text))
        elif kind == "p":
            self.blocks.append(("p", text))
        elif kind == "cell":
            if self.cell is not None:
                self.cell.append(text)
        else:
            # 游离文本按段落处理
            self.blocks.append(("p", text))

    def flush_code(self):
        code = "".join(self.code_buf)
        self.code_buf = []
        lines = [l.rstrip() for l in code.replace("\r", "").split("\n")]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            self.blocks.append(("code", "\n".join(lines)))

    # ---------- 标签处理 ----------
    def handle_starttag(self, tag, attrs):
        attrd = dict(attrs)
        cls = attrd.get("class", "")
        aid = attrd.get("id", "")

        if tag in SKIP_TAGS:
            self.skip.append(tag)
            return
        if self.skip:
            return
        if tag == "br":
            if self.pre_depth:
                self.code_buf.append("\n")
            elif self.cell is None:
                self.cur.append(" ")
            return
        if tag == "hr":
            return
        if tag in HEADINGS:
            self.flush()
            self.cur_kind = tag
            return
        if tag == "p":
            self.flush()
            self.cur_kind = "p"
            return
        if tag in ("ul", "ol"):
            self.flush()
            self.list_stack.append(tag)
            self.ol_idx.append(0)
            return
        if tag == "li":
            self.flush()
            if self.list_stack and self.list_stack[-1] == "ol":
                self.ol_idx[-1] += 1
            self.cur_kind = "li"
            return
        if tag == "pre":
            self.flush()
            self.pre_depth += 1
            return
        if tag == "table":
            self.flush()
            self.rows = []
            return
        if tag == "tr":
            self.row = []
            return
        if tag in ("td", "th"):
            self.cell = []
            self.cur_kind = "cell"
            return
        if tag == "div":
            self.flush()
            is_code = any(h in cls for h in CODE_DIV_HINT)
            self.div_stack.append(is_code)
            if is_code:
                self.pre_depth += 1
            return
        if tag == "span" and self.pre_depth == 0 and "marked" in cls:
            self.cur.append(CODE_MARK)
            return
        if tag == "code" and self.pre_depth == 0:
            self.cur.append(CODE_MARK)
            return
        if tag in ("strong", "b") and self.pre_depth == 0:
            self.cur.append("**")
            self.bold += 1
            return
        # a / img / span 等：保留文本，丢弃标签
        if tag == "img":
            return

    def handle_endtag(self, tag):
        if self.skip:
            if self.skip[-1] == tag:
                self.skip.pop()
            return
        if tag in HEADINGS:
            self.flush()
            return
        if tag == "p":
            self.flush()
            return
        if tag in ("ul", "ol"):
            self.flush()
            if self.list_stack:
                self.list_stack.pop()
                self.ol_idx.pop()
            return
        if tag == "li":
            self.flush()
            return
        if tag == "pre":
            self.pre_depth = max(0, self.pre_depth - 1)
            self.flush_code()
            return
        if tag == "div":
            is_code = self.div_stack.pop() if self.div_stack else False
            if is_code:
                self.pre_depth = max(0, self.pre_depth - 1)
                self.flush_code()
            else:
                self.flush()
            return
        if tag in ("td", "th"):
            self.flush()
            if self.cell is not None and self.row is not None:
                self.row.append(" ".join(self.cell).strip())
            self.cell = None
            return
        if tag == "tr":
            self.flush()
            if self.row is not None and self.rows is not None:
                self.rows.append(self.row)
            self.row = None
            return
        if tag == "table":
            self.flush()
            self.emit_table()
            return
        if tag in ("strong", "b") and self.bold and self.pre_depth == 0:
            self.cur.append("**")
            self.bold -= 1
            return
        if tag == "code" and self.pre_depth == 0:
            self.cur.append(CODE_MARK)
            return
        if tag == "span" and self.pre_depth == 0:
            self.cur.append(CODE_MARK)
            return

    def emit_table(self):
        rows = [r for r in (self.rows or []) if any(c.strip() for c in r)]
        self.rows = None
        if not rows:
            return
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        out = []
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in rows[0]) + " |")
        out.append("|" + " --- |" * width)
        for r in rows[1:]:
            out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
        self.blocks.append(("table", "\n".join(out)))

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre_depth:
            self.code_buf.append(data)
        elif self.cell is not None:
            self.cell.append(data)
        else:
            self.cur.append(data)


def html_to_markdown(fragment):
    p = MdParser()
    p.feed(fragment)
    p.flush()
    p.flush_code()

    # 连续的列表项合并为一个块，避免列表项之间出现空行
    merged = []
    for kind, text in p.blocks:
        if kind == "li" and merged and merged[-1][0] == "li":
            merged[-1] = ("li", merged[-1][1] + "\n" + text)
        else:
            merged.append((kind, text))

    out = []
    for kind, text in merged:
        if kind == "h1":
            continue                      # 页面标题单独保存
        if kind == "code":
            out.append("```bash\n" + text + "\n```")
        elif kind == "table":
            out.append(text)
        elif kind.startswith("h"):
            lvl = int(kind[1])
            out.append("#" * min(lvl, 4) + " " + text)
        elif kind == "li":
            # 列表块保留换行，只清理每行多余空白
            lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in text.split("\n")]
            out.append("\n".join(l for l in lines if l))
        else:
            # 压缩正文空白
            t = re.sub(r'\s+', ' ', text).strip()
            if t and t not in NOISE_LINES:
                out.append(t)
    md = "\n\n".join(out)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r'^\s*(运行实例|尝试实例)\s*»?\s*$', '', md, flags=re.M)
    md = re.sub(r'\*\*\s*\*\*', '', md)
    md = re.sub(CODE_MARK + r'{2,}', CODE_MARK, md)
    return md.replace(CODE_MARK, "`").strip()


def convert(html):
    return html_to_markdown(extract_article(html))
