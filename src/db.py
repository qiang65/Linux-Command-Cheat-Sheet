#!/usr/bin/env python3
"""数据层：SQLite 建库、种子灌入、增删改查、搜索、收藏、历史、导入导出。"""
import json
import os
import sqlite3
import time

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY,
    key  TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    sort        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    summary     TEXT DEFAULT '',
    content     TEXT DEFAULT '',
    params      TEXT DEFAULT '',
    example     TEXT DEFAULT '',
    note        TEXT DEFAULT '',
    tags        TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    fav         INTEGER DEFAULT 0,
    views       INTEGER DEFAULT 0,
    created     TEXT DEFAULT (datetime('now','localtime')),
    updated     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS history (
    id        INTEGER PRIMARY KEY,
    entry_id  INTEGER NOT NULL,
    viewed_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS trash (
    id           INTEGER PRIMARY KEY,
    entry_json   TEXT NOT NULL,
    deleted_at   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_entries_cat   ON entries(category_id);
CREATE INDEX IF NOT EXISTS idx_entries_group ON entries(group_id);
CREATE INDEX IF NOT EXISTS idx_entries_name  ON entries(name);
CREATE INDEX IF NOT EXISTS idx_groups_cat    ON groups(category_id);
CREATE INDEX IF NOT EXISTS idx_history_entry ON history(entry_id);
"""

DEFAULT_CATEGORIES = [
    ("cheatsheet", "Linux 命令速查表"),
    ("shell", "Shell 教程"),
    ("manual", "Linux 参考手册"),
    ("settings", "设置"),
]


class Store:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ------------------------------------------------------------- 基础
    def close(self):
        try:
            self.db.commit()
        finally:
            self.db.close()

    def is_empty(self):
        return self.db.execute("SELECT COUNT(*) c FROM entries").fetchone()["c"] == 0

    def categories(self, with_settings=True):
        rows = self.db.execute(
            "SELECT * FROM categories ORDER BY sort, id").fetchall()
        out = [dict(r) for r in rows]
        if not with_settings:
            out = [c for c in out if c["key"] != "settings"]
        return out

    def ensure_categories(self):
        for i, (key, name) in enumerate(DEFAULT_CATEGORIES):
            self.db.execute(
                "INSERT OR IGNORE INTO categories(key,name,sort) VALUES(?,?,?)",
                (key, name, i))
        self.db.commit()

    def category_id(self, key):
        r = self.db.execute(
            "SELECT id FROM categories WHERE key=?", (key,)).fetchone()
        return r["id"] if r else None

    # ------------------------------------------------------------- 读取
    def groups(self, cat_key, only_with_entries=True):
        cid = self.category_id(cat_key)
        if cid is None:
            return []
        sql = ("SELECT g.id, g.name, g.sort, COUNT(e.id) n "
               "FROM groups g LEFT JOIN entries e ON e.group_id=g.id "
               "WHERE g.category_id=? ")
        if only_with_entries:
            sql += "GROUP BY g.id HAVING n>0 "
        else:
            sql += "GROUP BY g.id "
        sql += "ORDER BY g.sort, g.id"
        return [dict(r) for r in self.db.execute(sql, (cid,))]

    def group_id_by_name(self, cat_key, name):
        cid = self.category_id(cat_key)
        if cid is None:
            return None
        r = self.db.execute(
            "SELECT id FROM groups WHERE category_id=? AND name=?",
            (cid, name)).fetchone()
        return r["id"] if r else None

    def ensure_group(self, cat_key, name):
        gid = self.group_id_by_name(cat_key, name)
        if gid:
            return gid
        cid = self.category_id(cat_key)
        sort = self.db.execute(
            "SELECT COALESCE(MAX(sort),0)+1 s FROM groups WHERE category_id=?",
            (cid,)).fetchone()["s"]
        cur = self.db.execute(
            "INSERT INTO groups(category_id,name,sort) VALUES(?,?,?)", (cid, name, sort))
        self.db.commit()
        return cur.lastrowid

    def entries(self, cat_key, query="", fav_only=False, group_id=None, limit=0):
        """按分类取词条；query 走 LIKE 并按匹配强度排序。"""
        cid = self.category_id(cat_key)
        if cid is None:
            return []
        params = [cid]
        where = "e.category_id=?"
        if group_id is not None:
            where += " AND e.group_id=?"
            params.append(group_id)
        if fav_only:
            where += " AND e.fav=1"
        order = "COALESCE(g.sort,9999), g.id, e.rowid"
        if query.strip():
            q = query.strip()
            like = f"%{q}%"
            where += (" AND (e.name LIKE ? OR e.summary LIKE ? "
                      "OR e.tags LIKE ? OR e.content LIKE ? OR e.example LIKE ?)")
            params += [like] * 5
            order = (
                "CASE WHEN lower(e.name)=lower(?) THEN 0 "
                "WHEN lower(e.name) LIKE ? THEN 1 "
                "WHEN lower(e.name) LIKE ? THEN 2 "
                "WHEN lower(e.summary) LIKE ? THEN 3 ELSE 4 END, "
                "COALESCE(g.sort,9999), g.id, e.name")
            params += [q, f"{q.lower()}%", f"%{q.lower()}%", f"%{q.lower()}%"]
        sql = (f"SELECT e.*, g.name group_name FROM entries e "
               f"LEFT JOIN groups g ON g.id=e.group_id "
               f"WHERE {where} ORDER BY {order}")
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [dict(r) for r in self.db.execute(sql, params)]

    def entry(self, entry_id):
        r = self.db.execute(
            "SELECT e.*, g.name group_name, c.name category_name, c.key category_key "
            "FROM entries e LEFT JOIN groups g ON g.id=e.group_id "
            "LEFT JOIN categories c ON c.id=e.category_id WHERE e.id=?",
            (entry_id,)).fetchone()
        return dict(r) if r else None

    def view(self, entry_id):
        self.db.execute("UPDATE entries SET views=views+1 WHERE id=?", (entry_id,))
        self.db.execute("INSERT INTO history(entry_id) VALUES(?)", (entry_id,))
        self.db.execute(
            "DELETE FROM history WHERE id NOT IN "
            "(SELECT id FROM history ORDER BY id DESC LIMIT 500)")
        self.db.commit()

    def history(self, limit=30):
        sql = ("SELECT h.viewed_at, e.id, e.name, c.name category_name "
               "FROM history h JOIN entries e ON e.id=h.entry_id "
               "JOIN categories c ON c.id=e.category_id "
               "ORDER BY h.id DESC LIMIT ?")
        return [dict(r) for r in self.db.execute(sql, (limit,))]

    def clear_history(self):
        self.db.execute("DELETE FROM history")
        self.db.commit()

    # ------------------------------------------------------------- 写入
    def save_entry(self, data):
        """新增或更新词条。data 需含 category_key；有 id 则更新。"""
        cid = self.category_id(data.get("category_key") or "cheatsheet")
        if cid is None:
            raise ValueError("分类不存在")
        gid = data.get("group_id")
        if not gid and data.get("group_name"):
            gid = self.ensure_group(data.get("category_key") or "cheatsheet",
                                    data["group_name"])
        row = {
            "category_id": cid,
            "group_id": gid,
            "name": (data.get("name") or "未命名").strip(),
            "summary": data.get("summary") or "",
            "content": data.get("content") or "",
            "params": data.get("params") or "",
            "example": data.get("example") or "",
            "note": data.get("note") or "",
            "tags": data.get("tags") or "",
            "source": data.get("source") or "",
            "fav": 1 if data.get("fav") else 0,
        }
        if data.get("id"):
            self.db.execute(
                "UPDATE entries SET category_id=:category_id, group_id=:group_id, "
                "name=:name, summary=:summary, content=:content, params=:params, "
                "example=:example, note=:note, tags=:tags, source=:source, "
                "fav=:fav, updated=datetime('now','localtime') "
                "WHERE id=:id", {**row, "id": data["id"]})
            self.db.commit()
            return data["id"]
        cur = self.db.execute(
            "INSERT INTO entries(category_id,group_id,name,summary,content,params,"
            "example,note,tags,source,fav) VALUES(:category_id,:group_id,:name,"
            ":summary,:content,:params,:example,:note,:tags,:source,:fav)", row)
        self.db.commit()
        return cur.lastrowid

    def delete_entry(self, entry_id):
        self.db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.db.commit()

    # ------------------------------------------------------------- 删除记录
    def to_trash(self, entry_id):
        """删除词条并留存完整快照，可从删除记录恢复。"""
        e = self.entry(entry_id)
        if not e:
            return None
        self.db.execute(
            "INSERT INTO trash(entry_json) VALUES(?)",
            (json.dumps(e, ensure_ascii=False),))
        self.db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.db.execute("DELETE FROM history WHERE entry_id=?", (entry_id,))
        self.db.commit()
        return e

    def trash_list(self, limit=200):
        rows = self.db.execute(
            "SELECT id, deleted_at, entry_json FROM trash ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        out = []
        for r in rows:
            try:
                d = json.loads(r["entry_json"])
            except json.JSONDecodeError:
                continue
            d["trash_id"] = r["id"]
            d["deleted_at"] = r["deleted_at"]
            out.append(d)
        return out

    def trash_count(self):
        return self.db.execute("SELECT COUNT(*) c FROM trash").fetchone()["c"]

    def restore_from_trash(self, trash_id):
        """从删除记录恢复词条，尽量还原到原分组。"""
        r = self.db.execute(
            "SELECT entry_json FROM trash WHERE id=?", (trash_id,)).fetchone()
        if not r:
            return None
        d = json.loads(r["entry_json"])
        cid = d.get("category_id")
        if not self.db.execute("SELECT 1 FROM categories WHERE id=?", (cid,)).fetchone():
            # 原分类已被删除：按快照补建分类，保证恢复后词条不丢
            key, name = d.get("category_key"), d.get("category_name")
            if key and key != "settings":
                self.add_category(key, name or key)
                cid = self.category_id(key)
            else:
                cid = self.category_id("cheatsheet")
        gid = d.get("group_id")
        if gid and not self.db.execute("SELECT 1 FROM groups WHERE id=?", (gid,)).fetchone():
            gid = None
        if not gid and d.get("group_name"):
            key = self.db.execute(
                "SELECT key FROM categories WHERE id=?", (cid,)).fetchone()["key"]
            gid = self.ensure_group(key, d["group_name"])
        self.db.execute("DELETE FROM trash WHERE id=?", (trash_id,))
        cur = self.db.execute(
            "INSERT INTO entries(category_id,group_id,name,summary,content,params,"
            "example,note,tags,source,fav) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (cid, gid, d.get("name", "未命名"), d.get("summary", ""),
             d.get("content", ""), d.get("params", ""), d.get("example", ""),
             d.get("note", ""), d.get("tags", ""), d.get("source", ""),
             int(d.get("fav") or 0)))
        self.db.commit()
        return cur.lastrowid

    def clear_trash(self):
        self.db.execute("DELETE FROM trash")
        self.db.commit()

    def toggle_fav(self, entry_id):
        self.db.execute("UPDATE entries SET fav = 1 - fav WHERE id=?", (entry_id,))
        self.db.commit()
        r = self.db.execute("SELECT fav FROM entries WHERE id=?", (entry_id,)).fetchone()
        return r["fav"] if r else 0

    def delete_group(self, group_id):
        self.db.execute("DELETE FROM groups WHERE id=?", (group_id,))
        self.db.commit()

    def rename_group(self, group_id, name):
        self.db.execute("UPDATE groups SET name=? WHERE id=?", (name, group_id))
        self.db.commit()

    def move_group(self, group_id, cat_key):
        cid = self.category_id(cat_key)
        if cid is None:
            return
        self.db.execute("UPDATE groups SET category_id=? WHERE id=?", (cid, group_id))
        self.db.commit()

    def add_category(self, key, name):
        sort = self.db.execute(
            "SELECT COALESCE(MAX(sort),0)+1 s FROM categories").fetchone()["s"]
        self.db.execute("INSERT OR IGNORE INTO categories(key,name,sort) VALUES(?,?,?)",
                        (key, name, sort))
        self.db.commit()
        return self.category_id(key)

    def add_category_named(self, name, key=None):
        """按显示名新增分类，自动生成唯一 key。"""
        name = (name or "").strip()
        if not name:
            return None, "分类名称不能为空"
        key = (key or "").strip() or "cat" + str(
            abs(hash(name)) % 100000)
        if self.category_id(key) or self.db.execute(
                "SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
            return None, f"分类「{name}」已存在"
        return self.add_category(key, name), ""

    def rename_category(self, cat_id, name):
        name = (name or "").strip()
        if not name:
            return False
        self.db.execute("UPDATE categories SET name=? WHERE id=?", (name, cat_id))
        self.db.commit()
        return True

    def reorder_categories(self, ordered_keys):
        """按给定的 key 顺序写入 sort（分类拖拽排序）。"""
        for i, key in enumerate(ordered_keys):
            self.db.execute("UPDATE categories SET sort=? WHERE key=?", (i, key))
        # 设置分类不占列表位，固定排在最后，避免与知识库分类撞同一个 sort 值
        self.db.execute("UPDATE categories SET sort=? WHERE key='settings'",
                        (len(ordered_keys),))
        self.db.commit()
        return len(ordered_keys)

    def delete_category(self, cat_id, keep_in_trash=True):
        """删除分类及其分组；词条快照存入删除记录，可恢复。"""
        row = self.db.execute(
            "SELECT key,name FROM categories WHERE id=?", (cat_id,)).fetchone()
        if not row or row["key"] == "settings":
            return 0
        ids = [r["id"] for r in self.db.execute(
            "SELECT id FROM entries WHERE category_id=?", (cat_id,))]
        if keep_in_trash:
            for i in ids:
                self.to_trash(i)
        else:
            self.db.execute("DELETE FROM entries WHERE category_id=?", (cat_id,))
        self.db.execute("DELETE FROM groups WHERE category_id=?", (cat_id,))
        self.db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.db.commit()
        return len(ids)

    def category_entry_count(self, cat_key):
        cid = self.category_id(cat_key)
        if cid is None:
            return 0
        return self.db.execute(
            "SELECT COUNT(*) c FROM entries WHERE category_id=?", (cid,)).fetchone()["c"]

    # ------------------------------------------------------------- 设置
    def setting(self, key, default=None):
        r = self.db.execute(
            "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key, value):
        self.db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.db.commit()

    # ------------------------------------------------------------- 统计
    def stats(self):
        out = {}
        out["entries"] = self.db.execute(
            "SELECT COUNT(*) c FROM entries").fetchone()["c"]
        out["groups"] = self.db.execute(
            "SELECT COUNT(*) c FROM groups").fetchone()["c"]
        out["fav"] = self.db.execute(
            "SELECT COUNT(*) c FROM entries WHERE fav=1").fetchone()["c"]
        out["per_category"] = {
            r["key"]: r["c"] for r in self.db.execute(
                "SELECT c.key, COUNT(e.id) c FROM categories c "
                "LEFT JOIN entries e ON e.category_id=c.id GROUP BY c.id")}
        out["db_size_kb"] = (os.path.getsize(self.db_path) // 1024
                             if os.path.exists(self.db_path) else 0)
        return out

    # ------------------------------------------------------------- 种子
    def seed_from_json(self, json_path, replace=False):
        """把 seed.json 灌入数据库。replace=True 时清空现有词条。"""
        if not os.path.exists(json_path):
            return False
        seed = json.load(open(json_path, encoding="utf-8"))
        self.ensure_categories()
        if replace:
            self.db.execute("DELETE FROM entries")
            self.db.execute("DELETE FROM groups")
        for cat in seed.get("categories", []):
            cid = self.category_id(cat["key"])
            if cid is None:
                self.add_category(cat["key"], cat["name"])
                cid = self.category_id(cat["key"])
            for gi, group in enumerate(cat.get("groups", [])):
                gid = self.ensure_group(cat["key"], group["name"])
                for ent in group.get("entries", []):
                    self.db.execute(
                        "INSERT INTO entries(category_id,group_id,name,summary,content,"
                        "params,example,note,tags,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (cid, gid, ent.get("name", ""), ent.get("summary", ""),
                         ent.get("content", ""), ent.get("params", ""),
                         ent.get("example", ""), ent.get("note", ""),
                         ent.get("tags", group["name"]), ent.get("source", "")))
        self.db.commit()
        return True

    # ------------------------------------------------------------- 导入导出
    def export_json(self, path):
        data = {"version": 1, "exported": time.strftime("%Y-%m-%d %H:%M:%S"),
                "categories": []}
        for cat in self.categories(with_settings=False):
            groups = []
            for g in self.groups(cat["key"], only_with_entries=False):
                ents = [{"name": e["name"], "summary": e["summary"],
                         "content": e["content"], "params": e["params"],
                         "example": e["example"], "note": e["note"],
                         "tags": e["tags"], "source": e["source"],
                         "fav": e["fav"]}
                        for e in self.entries(cat["key"], group_id=g["id"])]
                if ents:
                    groups.append({"name": g["name"], "entries": ents})
            data["categories"].append({"key": cat["key"], "name": cat["name"],
                                       "groups": groups})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return sum(len(g["entries"]) for c in data["categories"]
                   for g in c["groups"])

    def import_json(self, path, replace=False):
        if replace:
            self.db.execute("DELETE FROM entries")
            self.db.execute("DELETE FROM groups")
        return self.seed_from_json(path, replace=False)
