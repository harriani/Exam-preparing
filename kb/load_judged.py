#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 LLM 判断结果(judged.json)写入 kb.db，替换旧 exam 模式产出的 KU。"""
import sqlite3, json, os

KB="F:/WorkBuddy/2026-08-04-11-22-11/learning-system-v2/kb"
DB=os.path.join(KB,"kb.db")
judged=json.load(open(os.path.join(KB,"judged.json"),encoding="utf-8"))

conn=sqlite3.connect(DB)
conn.execute("ALTER TABLE knowledge_units ADD COLUMN is_exam_point INTEGER DEFAULT 1")
conn.execute("DELETE FROM knowledge_units")  # 清空旧 exam 模式 KU

docs={r[1]:r[0] for r in conn.execute("SELECT id,title FROM documents")}

def match_doc(std):
    for title,did in docs.items():
        # std 形如 GB/T 2951.13-2008 ；title 形如 GB∕T 2951.13-2008 ...
        key=std.replace("GB/T ","GB∕T ")
        if key in title:
            return did
    return None

n_point=0
for k in judged:
    did=match_doc(k["standard_no"])
    if did is None:
        print("WARN 未匹配文档:",k["standard_no"]); continue
    is_pt=1 if k.get("is_exam_point") else 0
    if is_pt: n_point+=1
    conn.execute("""INSERT INTO knowledge_units
        (document_id,section_id,unit_type,title,source_ref,raw_text,key_requirements,interpretation,exam_relevance,is_exam_point,status)
        VALUES (?,?,?,?,?,?,?,?,?,?,'active')""",
        (did, None, k["type"], k["title"], k["clause"], "",
         json.dumps(k["key_requirements"],ensure_ascii=False),
         k["interpretation"], k.get("priority",""), is_pt))
conn.commit()
tot=conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0]
print(f"已写入 KU 共 {tot} 条，其中 is_exam_point=1 的考点 {n_point} 条，非考点 {tot-n_point} 条")
conn.close()
