#!/usr/bin/env python3
"""抓取 runoob《Docker 命令大全》，生成 data/docker_seed.json。

索引页：https://www.runoob.com/docker/docker-command-manual.html
结构：<h3> 分类标题 + <a href="docker-xxx-command.html">命令名 - 说明</a>
详情页含：说明、语法、选项、实例。

抓取结果缓存在 .cache/docker/，重复运行不再请求网络。
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

from build_comm_manual import clean_body, code_blocks, section, strip_fence   # noqa: E402

CACHE = os.path.join(ROOT, ".cache", "docker")
INDEX = os.path.join(ROOT, ".cache", "docker-command-manual.html")
OUT = os.path.join(ROOT, "data", "docker_seed.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}
CAT_KEY = "docker"
CAT_NAME = "Docker 命令"
BASE = "https://www.runoob.com/docker/"
# 索引页里前两个分类的标题不是 h2/h3，按文字定位
CATS = ["容器生命周期管理", "容器操作", "容器的root文件系统（rootfs）命令",
        "镜像仓库", "本地镜像管理", "info|version", "Docker Compose",
        "网络命令", "卷命令"]
# 这两个分类在索引页里是纯文本条目，正文取自分类页
EXTRA_CATS = [("网络命令", "docker-network.html"), ("卷命令", "docker-volume.html")]
cat_kw = {"网络命令": "network", "卷命令": "volume"}


def fetch(link):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, os.path.basename(link))
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        return open(fn, encoding="utf-8").read()
    url = link if link.startswith("http") else BASE + link
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


def plain(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    s = s.replace("&quot;", '"').replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def split_sections(md):
    """把分类页正文按 ### 章节切开，返回 {章节标题: 内容}。"""
    parts = re.split(r"^###\s+(.+)$", md, flags=re.M)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        title = plain(parts[i]).strip("` ").strip()
        out[title] = parts[i + 1].strip()
    return out


def section_for(sections, name):
    """在章节里找命令对应的段落，如 docker network ls → 「docker network ls 命令」。"""
    key = name.replace("docker ", "").strip()
    for title, body in sections.items():
        t = title.replace("`", "").strip()
        if t.startswith(key) or key in t:
            return f"### {title}\n{body}"
    return ""


def parse_index(html):
    """索引页 → [(分类, 命令名, 说明, 详情页)]。"""
    i = html.find('class="article-intro"')
    j = html.find('<div class="footer"', i)
    seg = html[i:j if j > 0 else len(html)]

    marks = []
    for m in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>", seg, re.S):
        t = plain(m.group(2))
        if t and "Docker 命令大全" not in t:
            marks.append((m.start(), t))
    for c in CATS:
        for m in re.finditer(re.escape(c), seg):
            marks.append((m.start(), c))
    marks.sort()

    def cat_of(pos):
        cat = "其他命令"
        for mpos, cname in marks:
            if mpos < pos:
                cat = cname
            else:
                break
        return cat

    groups, seen = {}, set()
    pat = r'<a [^>]*href="([^"]*docker-[a-z0-9\-]+(?:-[a-z0-9\-]+)*-command\.html)"[^>]*>(.*?)</a>'
    for m in re.finditer(pat, seg, re.S):
        link = m.group(1).split("/")[-1]
        if link in seen:
            continue
        seen.add(link)
        text = plain(m.group(2))
        if " - " in text:
            name, desc = text.split(" - ", 1)
        elif "-" in text and len(text) > 6:
            name, desc = text.split("-", 1)
        else:
            name, desc = text, ""
        groups.setdefault(cat_of(m.start()), []).append({
            "name": name.strip().strip("。. ").replace("docker ", ""),
            "desc": desc.strip().strip("。. "),
            "link": link})

    # 网络命令 / 卷命令：索引页里是 <strong>命令</strong> : 说明，无独立详情页，
    # 正文取自分类页 docker-network.html / docker-volume.html 的对应章节
    for cat, page in EXTRA_CATS:
        # 实际格式：<strong><code>docker network ls</code></strong>: 列出所有网络。
        pat2 = (r"<strong>\s*(?:<code>)?\s*(docker\s+" + cat_kw[cat]
                + r"[^<]*?)(?:</code>)?\s*</strong>\s*[:：]\s*([^<\n]{2,90})")
        for m in re.finditer(pat2, seg):
            raw = plain(m.group(1)).replace("docker", "").strip()
            # 名称里的参数占位符（如 <volume>）不进命令名，留给参数说明
            args = " ".join(re.findall(r"<[^>]*>", raw))
            name = re.sub(r"<[^>]*>", "", raw).strip()
            desc = plain(m.group(2)).strip("。. ")
            if not name:
                continue
            groups.setdefault(cat, []).append({
                "name": name, "desc": desc, "link": page, "args": args})
    return groups


def build_entry(cmd, html, sections=None):
    md = ""
    if html:
        from html2md import convert
        md = convert(html)
    # 网络/卷命令取自分类页的对应章节
    if sections is not None:
        sec = section_for(sections, cmd["name"])
        if sec:
            md = sec
    syntax = strip_fence(section(md, "语法"))
    if not syntax and cmd.get("args"):
        syntax = f"docker {cmd['name']} {cmd['args']}".strip()
    example = section(md, "实例")
    blocks = code_blocks(example) or code_blocks(md)
    note = ""
    m = re.search(r"(注意[：:]\s*[^\n]{4,160})", md)
    if m:
        note = m.group(1).strip()
    return {
        "name": cmd["name"],
        "summary": cmd["desc"],
        "content": clean_body(md, cmd["name"], cmd["desc"]),
        "params": syntax,
        "example": "\n\n".join(blocks[:4]).strip(),
        "note": note,
        "tags": "Docker",
        "source": "runoob " + cmd["link"],
    }


def main():
    if not os.path.exists(INDEX):
        req = urllib.request.Request(BASE + "docker-command-manual.html", headers=UA)
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        os.makedirs(os.path.dirname(INDEX), exist_ok=True)
        open(INDEX, "w", encoding="utf-8").write(raw)
    groups = parse_index(open(INDEX, encoding="utf-8").read())
    total = sum(len(v) for v in groups.values())
    print(f"索引解析：{len(groups)} 个分类 / {total} 个命令")
    for k, v in groups.items():
        print(f"  {k:26} {len(v):2} 条  例：{v[0]['name']} — {v[0]['desc'][:26]}")

    links = [c["link"] for v in groups.values() for c in v]
    cached = sum(1 for l in links if os.path.exists(os.path.join(CACHE, os.path.basename(l))))
    print(f"\n待抓取详情页 {len(links)} 个（已缓存 {cached} 个）")
    t0 = time.time()
    pages = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch, l): l for l in links}
        for fut, l in futs.items():
            pages[l] = fut.result()

    out, ok, empty = [], 0, 0
    from html2md import convert
    extra_pages = {p: pages.get(p, "") for _, p in EXTRA_CATS}
    sections = {p: (split_sections(convert(extra_pages[p])) if extra_pages[p] else {})
                for _, p in EXTRA_CATS}
    for cat, cmds in groups.items():
        entries = []
        for c in cmds:
            page = c["link"]
            if page in extra_pages:
                e = build_entry(c, extra_pages[page], sections[page])
            else:
                e = build_entry(c, pages.get(page, ""))
            if e["content"] or e["example"] or e["params"]:
                ok += 1
            else:
                empty += 1
            entries.append(e)
        out.append({"name": cat, "entries": entries})

    seed = {"version": 1, "categories": [
        {"key": CAT_KEY, "name": CAT_NAME, "groups": out}]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=1)
    n = sum(len(g["entries"]) for g in out)
    lens = [len(e["content"]) for g in out for e in g["entries"]]
    print(f"\n写入 {OUT}\n分类 1 组 {len(out)} 词条 {n}  有正文 {ok}  空正文 {empty}")
    if lens:
        print(f"正文长度 平均 {sum(lens) // len(lens)}  最短 {min(lens)}  最长 {max(lens)}")
    print(f"用时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
