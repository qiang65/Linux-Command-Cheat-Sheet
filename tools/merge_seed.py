#!/usr/bin/env python3
"""把 data/comm_seed.json 合并进 data/seed.json（按 key 去重，保留原有分类顺序）。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "seed.json")


def merge(paths):
    seed = json.load(open(SEED, encoding="utf-8"))
    cats = seed.get("categories", [])
    index = {c["key"]: i for i, c in enumerate(cats)}
    added, updated = 0, 0
    for p in paths:
        src = json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
        for cat in src.get("categories", []):
            if cat["key"] in index:
                cats[index[cat["key"]]] = cat
                updated += 1
            else:
                cats.append(cat)
                index[cat["key"]] = len(cats) - 1
                added += 1
        print(f"合并 {p}: 分类 {len(src.get('categories', []))} "
              f"词条 {sum(len(g['entries']) for c in src.get('categories', []) for g in c['groups'])}")
    seed["categories"] = cats
    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=1)
    total = sum(len(g["entries"]) for c in cats for g in c["groups"])
    print(f"\nseed.json 现有分类 {len(cats)}（新增 {added} 更新 {updated}）"
          f"分组 {sum(len(c['groups']) for c in cats)} 词条 {total}")
    for c in cats:
        print(f"  {c['key']:12} {c['name']:16} "
              f"{len(c['groups'])} 组 {sum(len(g['entries']) for g in c['groups'])} 条")


if __name__ == "__main__":
    merge(sys.argv[1:] or ["data/comm_seed.json"])
