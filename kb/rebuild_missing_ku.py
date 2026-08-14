# -*- coding: utf-8 -*-
"""
rebuild_missing_ku.py — 修复「全补」时批量脚本 make_ku=False 留下的洞：
部分产品标准只有 sections、没有 knowledge_units，导致 nav_standard / 大纲反查
这些产品标准时拿不到内容。

修复：对「属于产品标准、且 KU 数为 0」的文档，删掉旧 sections，用已有
kb/raw/pages_*.json 重新 build_kb(make_ku=True) 落库，保证与库内其余标准
（exam 模式 KU）结构一致。幂等：仅处理 KU=0 的产品标准文档。

必须在 kb.db 无其他写入者时运行（避免 SQLite 锁冲突）。
用法：python kb/rebuild_missing_ku.py
"""
import os, sys, re, sqlite3, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from _build_kb import build_kb, write_sqlite

DB = os.path.join(ROOT, "kb", "kb.db")
RAW = os.path.join(ROOT, "kb", "raw")


def norm_std(s):
    if not s:
        return None
    s = s.replace('∕', '/').replace('／', '/').replace('\\', '/')
    s = re.sub(r'\s+', '', s)
    m = re.match(r'(GB/T|JB/T|GB|JB)(\d+(?:\.\d+)*)', s)
    return (m.group(1) + m.group(2)) if m else None


def find_pages(title):
    # 从标题抽标准号（如 18890.2 / 12706.3），去 kb/raw 找匹配的 pages 文件
    nums = re.findall(r'\d+(?:\.\d+)+', title)
    for n in nums:
        cand = os.path.join(RAW, f"pages_{n}.json")
        if os.path.isfile(cand) and os.path.getsize(cand) > 1:
            return cand
    return None


def main():
    c = sqlite3.connect(DB)
    c.execute("PRAGMA busy_timeout=30000")
    cur = c.cursor()
    # 产品标准集合：与 build_links 一致（从 link_index 取）
    import json
    li = json.load(open(os.path.join(ROOT, "public", "data", "link_index.json"), encoding="utf-8"))
    pset = set()

    def add_norm(k):
        n = norm_std(k)
        if n:
            pset.add(n)
            m = re.match(r'(GB/T|JB/T|GB|JB)(\d+)', k or '')
            if m:
                pset.add(m.group(1) + m.group(2))
    for k in li["product_standards"]:
        add_norm(k)

    # 目标：文档标题归一化属于产品标准集，且 KU 数=0
    cur.execute("""SELECT d.id, d.title FROM documents d
                   WHERE (SELECT COUNT(*) FROM knowledge_units k WHERE k.document_id=d.id)=0""")
    targets = []
    for did, title in cur.fetchall():
        ns = norm_std(title)
        m = re.match(r'(GB/T|JB/T|GB|JB)(\d+)', title or '')
        base = (m.group(1) + m.group(2)) if m else None
        if ns in pset or base in pset:
            targets.append((did, title))

    print(f"待修复产品标准文档（KU=0）: {len(targets)} 个")
    fixed = 0
    for did, title in targets:
        pages = find_pages(title)
        if not pages:
            print(f"  [skip] 找不到 pages：{title}")
            continue
        # 删旧 sections / document_pages / knowledge_units（KU 本就为 0，无可惜内容）
        cur.execute("DELETE FROM sections WHERE document_id=?", (did,))
        cur.execute("DELETE FROM document_pages WHERE document_id=?", (did,))
        cur.execute("DELETE FROM knowledge_units WHERE document_id=?", (did,))
        cur.execute("DELETE FROM documents WHERE id=?", (did,))
        c.commit()
        # 重新落库（exam 模式，与库内一致）
        kb = build_kb(pages, normative_mode="strict", chunk_mode="clause", make_ku=True, ku_mode="exam")
        write_sqlite(kb, DB)
        print(f"  [ok] {title[:50]} -> sections={len(kb['sections'])} units={len(kb['units'])}")
        fixed += 1
    print(f"\n[done] 修复 {fixed}/{len(targets)} 个产品标准文档。随后请重跑 build_links.py 重建链接。")
    c.close()


if __name__ == "__main__":
    main()
