#!/usr/bin/env python3
"""生成种子数据 data/seed.json

数据来源：
  1. Linux 命令速查表 —— 解析用户提供的《Linux 命令速查表.md》
  2. Shell 教程 / Linux 参考手册 —— 抓取 www.runoob.com 对应页面正文
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from html2md import convert  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
OUT = os.path.join(ROOT, "data", "seed.json")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# ---------------------------------------------------------------- 抓取清单
SHELL_GROUPS = [
    ("Shell 基础与脚本", [
        ("linux-shell.html", "Shell 教程"),
        ("linux-shell-echo.html", "Shell echo 命令"),
        ("linux-shell-printf.html", "Shell printf 命令"),
    ]),
    ("变量、参数与数组", [
        ("linux-shell-variable.html", "Shell 变量"),
        ("linux-shell-passing-arguments.html", "Shell 传递参数"),
        ("linux-shell-array.html", "Shell 数组"),
    ]),
    ("运算符与条件测试", [
        ("linux-shell-basic-operators.html", "Shell 运算符"),
        ("linux-shell-test.html", "Shell test 命令"),
    ]),
    ("流程控制与函数", [
        ("linux-shell-process-control.html", "Shell 流程控制"),
        ("linux-shell-func.html", "Shell 函数"),
    ]),
    ("重定向与文件包含", [
        ("linux-shell-io-redirections.html", "Shell 输入/输出重定向"),
        ("linux-shell-include-file.html", "Shell 文件包含"),
    ]),
]

MANUAL_GROUPS = [
    ("系统基础与启动", [
        ("linux-intro.html", "Linux 简介"),
        ("linux-install.html", "Linux 安装"),
        ("linux-system-boot.html", "Linux 系统启动过程"),
        ("linux-system-contents.html", "Linux 系统目录结构"),
        ("windows-wsl-linux.html", "WSL 安装 Linux"),
        ("linux-cloud-server.html", "Linux 云服务器"),
    ]),
    ("文件属性与目录管理", [
        ("linux-file-attr-permission.html", "Linux 文件基本属性"),
        ("linux-file-content-manage.html", "Linux 文件与目录管理"),
        ("linux-remote-login.html", "Linux 远程登录"),
        ("linux-forget-password.html", "Linux 忘记密码解决方法"),
    ]),
    ("用户与用户组管理", [
        ("linux-user-manage.html", "Linux 用户和用户组管理"),
    ]),
    ("磁盘管理", [
        ("linux-filesystem.html", "Linux 磁盘管理"),
    ]),
    ("包管理工具", [
        ("linux-yum.html", "Linux yum 命令"),
        ("linux-comm-apt.html", "Linux apt 命令"),
    ]),
    ("vi / vim 编辑器", [
        ("linux-vim.html", "Linux vi/vim"),
    ]),
]


def fetch(url, cache_name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, cache_name)
    if os.path.exists(path) and os.path.getsize(path) > 20000:
        return open(path, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    for attempt in range(3):
        try:
            html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            time.sleep(0.5)
            return html
        except Exception as exc:
            print(f"    retry {attempt + 1} {url}: {exc}")
            time.sleep(2)
    print(f"    !! 抓取失败 {url}")
    return ""


def strip_code_fence(md):
    """去掉代码块围栏标记，保留纯代码文本（供示例字段使用）。"""
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", md, re.S)
    return "\n\n".join(b.strip() for b in blocks if b.strip())


def make_entry(title, md, source_url, group):
    """把整页 Markdown 变成一个词条。summary 取第一段正文。"""
    summary = ""
    for line in md.split("\n"):
        t = line.strip()
        if not t or t.startswith(("#", "```", "|", "-", "!", ">")):
            continue
        summary = re.sub(r"[`*]", "", t)
        break
    if len(summary) > 150:
        summary = summary[:150].rstrip() + "…"
    return {
        "name": title,
        "summary": summary,
        "content": md,
        "params": "",
        "example": strip_code_fence(md),
        "note": "",
        "tags": group,
        "source": source_url,
    }


def build_web_category(key, name, groups):
    out_groups = []
    for gname, pages in groups:
        entries = []
        for fname, title in pages:
            url = f"https://www.runoob.com/linux/{fname}"
            print(f"  [{name}] {title}  <-  {fname}")
            html = fetch(url, fname)
            md = convert(html) if html else ""
            if len(md) < 40:
                print(f"      !! 正文过短，跳过 ({len(md)})")
                continue
            entries.append(make_entry(title, md, url, gname))
        if entries:
            out_groups.append({"name": gname, "entries": entries})
    return {"key": key, "name": name, "groups": out_groups}


# ---------------------------------------------------------------- 附件解析
def parse_attachment(path):
    """解析《Linux 命令速查表.md》→ 分组词条列表。"""
    if not os.path.exists(path):
        print(f"  !! 未找到附件 {path}")
        return []
    text = open(path, encoding="utf-8").read()
    groups, current = [], None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith("### "):
            current = {"name": line[4:].strip(), "entries": []}
            groups.append(current)
            continue
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "entries": []}
            groups.append(current)
            continue
        if line.startswith("# "):
            continue
        if current is None:
            current = {"name": "其他", "entries": []}
            groups.append(current)

        # 符号条目：- `|` 管道：前命令输出交给后命令 `ps aux | grep nginx`
        bullet = line.startswith("- ")
        body = line[2:].strip() if bullet else line
        name, desc = "", body
        m = re.match(r"^`([^`]+)`\s*[:：]?\s*(.*)$", body)
        if m:
            name, desc = m.group(1), m.group(2)
        elif re.match(r"^[A-Za-z0-9_.+-]{1,20}\s*[:：]", body):
            head, tail = re.split(r"[:：]", body, 1)
            name, desc = head.strip(), tail.strip()
        if not name:
            name = body[:24]
        note = "⚠️ 高风险操作" if "⚠️" in desc else ""
        example = ""
        ex = re.findall(r"`([^`]+)`", desc)
        if ex:
            example = "  ".join(x for x in ex if len(x) > 2)[:160]
        current["entries"].append({
            "name": name,
            "summary": desc,
            # 速查表词条只有一句说明：正文留空，避免详情页把摘要再渲染一遍
            "content": "",
            "params": "",
            "example": example,
            "note": note,
            "tags": current["name"],
            "source": "本地速查表",
        })
    return [g for g in groups if g["entries"]]


def main():
    attachment = sys.argv[1] if len(sys.argv) > 1 else None
    if not attachment:
        cands = [p for p in os.listdir(ROOT) if p.endswith(".md") and "速查" in p]
        attachment = os.path.join(ROOT, cands[0]) if cands else None

    print("== 解析本地速查表 ==")
    cheat_groups = parse_attachment(attachment) if attachment else []
    print(f"  分组 {len(cheat_groups)} 个，词条 "
          f"{sum(len(g['entries']) for g in cheat_groups)} 条")

    print("== 抓取 Shell 教程 ==")
    shell = build_web_category("shell", "Shell 教程", SHELL_GROUPS)
    print("== 抓取 Linux 参考手册 ==")
    manual = build_web_category("manual", "Linux 参考手册", MANUAL_GROUPS)

    seed = {
        "version": 1,
        "source": "本地速查表 + www.runoob.com",
        "categories": [
            {"key": "cheatsheet", "name": "Linux 命令速查表", "groups": cheat_groups},
            shell,
            manual,
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=1)

    total = sum(len(g["entries"]) for c in seed["categories"] for g in c["groups"])
    print(f"\n已写入 {OUT}\n分类 {len(seed['categories'])} 组 "
          f"{sum(len(c['groups']) for c in seed['categories'])} 词条 {total}")


if __name__ == "__main__":
    main()
