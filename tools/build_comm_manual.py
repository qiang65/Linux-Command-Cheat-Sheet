#!/usr/bin/env python3
"""抓取 runoob《Linux 命令大全》全部命令详情页，生成 data/comm_seed.json。

数据源：https://www.runoob.com/wp-content/themes/runoob/assets/linux-command-data.json
结构：11 个分类 / 441 个命令，每条含 name、desc（一句话说明）、link（详情页）
详情页含：说明、语法、参数、实例。

抓取结果缓存在 .cache/comm/，重复运行不再请求网络。
"""
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from html2md import convert                                          # noqa: E402

CACHE = os.path.join(ROOT, ".cache", "comm")
DATA = os.path.join(ROOT, ".cache", "linux-command-data.json")
OUT = os.path.join(ROOT, "data", "comm_seed.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}
CAT_KEY = "commmanual"
CAT_NAME = "Linux 命令大全"


def fetch(link):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, os.path.basename(link))
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        return open(fn, encoding="utf-8").read()
    if link.startswith("http"):
        url = link
    elif link.startswith("/"):
        url = "https://www.runoob.com" + link
    else:
        # 数据源里部分链接是裸文件名，需要补上 /linux/ 目录
        url = "https://www.runoob.com/linux/" + link
    last = ""
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
            if len(html) > 2000:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(html)
                return html
            last = f"页面过短 {len(html)}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(1.0 + i)
    print(f"  抓取失败 {link}: {last}")
    return ""


def section(md, title):
    """取 markdown 里某个三级标题下的内容。"""
    m = re.search(r"^###\s+" + re.escape(title) + r"\s*$(.*?)(?=^###\s|^##\s|\Z)",
                  md, re.M | re.S)
    return m.group(1).strip() if m else ""


def code_blocks(text):
    out = re.findall(r"```bash\n(.*?)```", text, re.S)
    return [b.strip() for b in out if b.strip()]


def strip_fence(text):
    """去掉代码围栏标记，保留纯文本（用于参数/语法字段）。"""
    t = re.sub(r"```bash\n", "", text)
    t = t.replace("```", "")
    return re.sub(r"\n{3,}", "\n\n", t).strip()


NOISE_HEAD = {"Linux 命令大全", "Linux 命令速查", "Linux 命令手册"}


def clean_body(md, name, desc):
    """正文：去掉页面标题行、导航噪音，以及与摘要完全重复的首句。"""
    lines = md.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and (lines[0].startswith("# ")
                     or lines[0].strip() in NOISE_HEAD
                     or "Linux 命令大全" in lines[0] and len(lines[0].strip()) < 14):
        lines.pop(0)
    body = "\n".join(lines).strip()
    if desc:
        d = desc.strip()
        idx = body.find("\n")
        first = (body[:idx] if idx > 0 else body).strip()
        # 首句只是摘要的复述时去掉，避免详情页同一段显示两遍
        if d and d in first and len(first) <= len(d) + 16:
            body = body[idx + 1:].strip() if idx > 0 else ""
    return body


def build_entry(cmd, html):
    name = cmd["name"]
    desc = (cmd.get("desc") or "").strip()
    md = convert(html) if html else ""
    syntax = strip_fence(section(md, "语法"))
    example_sec = section(md, "实例")
    blocks = code_blocks(example_sec)
    if not blocks:
        blocks = code_blocks(md)
    example = "\n\n".join(blocks[:4]).strip()
    note = ""
    m = re.search(r"(注意[：:]\s*[^\n]{4,160})", md)
    if m:
        note = m.group(1).strip()
    body = clean_body(md, name, desc)
    return {
        "name": name,
        "summary": desc,
        "content": body,
        "params": syntax,
        "example": example,
        "note": note,
        "tags": cmd.get("category", ""),
        "source": "runoob " + os.path.basename(cmd["link"]),
    }


def main():
    if not os.path.exists(DATA):
        print("缺少数据源缓存，先抓取索引数据")
        url = ("https://www.runoob.com/wp-content/themes/runoob/"
               "assets/linux-command-data.json")
        req = urllib.request.Request(url, headers=dict(UA, Referer=(
            "https://www.runoob.com/linux/linux-command-manual.html")))
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        open(DATA, "w", encoding="utf-8").write(raw)
    os.makedirs(CACHE, exist_ok=True)
    data = json.load(open(DATA, encoding="utf-8"))

    links = [c["link"] for g in data for c in g["commands"]]
    print(f"待抓取详情页 {len(links)} 个（已缓存 "
          f"{sum(1 for l in links if os.path.exists(os.path.join(CACHE, os.path.basename(l))))} 个）")
    t0 = time.time()
    pages = {}
    done = [0]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch, l): l for l in links}
        for f in futs:
            pass
        for fut, l in futs.items():
            pages[l] = fut.result()
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"  已抓取 {done[0]}/{len(links)}  用时 {time.time() - t0:.0f}s")

    groups, ok, empty = [], 0, 0
    for g in data:
        entries = []
        for cmd in g["commands"]:
            e = build_entry(cmd, pages.get(cmd["link"], ""))
            if e["content"] or e["example"] or e["params"]:
                ok += 1
            else:
                empty += 1
            entries.append(e)
        groups.append({"name": g["category"], "entries": entries})
        print(f"  {g['category']:8} {len(entries):3} 条")

    seed = {"version": 1, "categories": [
        {"key": CAT_KEY, "name": CAT_NAME, "groups": groups}]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=1)
    total = sum(len(g["entries"]) for g in groups)
    lens = [len(e["content"]) for g in groups for e in g["entries"]]
    print(f"\n写入 {OUT}\n分类 1 组 {len(groups)} 词条 {total}  有正文 {ok}  空正文 {empty}")
    if lens:
        print(f"正文长度 平均 {sum(lens) // len(lens)}  最短 {min(lens)}  最长 {max(lens)}")
    print(f"用时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
