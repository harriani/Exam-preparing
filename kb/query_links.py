# -*- coding: utf-8 -*-
"""
query_links.py — 在 kb.db 上查询「大纲→实验→标准→产品特殊规定→知识单元」的结构化链接。
这是把 link_index 的三层结构真正落进知识库后的【查询消费层】：
  - nav_syllabus(sid)  一个大纲条目涉及哪些实验、标准、产品特殊规定、知识单元
  - nav_experiment(exp) 一个实验涉及哪些标准、产品特殊规定、知识单元
  - nav_standard(std)  一个标准里有哪些知识单元、归属哪些实验/大纲
  - search_kb(kw)      全文检索知识单元（带其大纲/实验归属）
既能被命令行调用验证，也能被 server.py 作为只读 API 暴露给前端。
"""
import os, sqlite3, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "kb", "kb.db")
LI = os.path.join(ROOT, "public", "data", "link_index.json")


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _li():
    return json.load(open(LI, encoding="utf-8"))


def nav_syllabus(sid):
    c = _conn()
    li = _li()
    info = li["syllabus"].get(sid)
    if not info:
        return {"error": f"未知大纲 {sid}"}
    # 关联的知识单元
    kus = c.execute(
        """SELECT DISTINCT ku.id, ku.title, ku.unit_type, ku.tier, ku.experiment,
                ku.ref_standards, ku.weight, d.title AS doc_title
           FROM ku_links k
           JOIN knowledge_units ku ON ku.id=k.ku_id
           JOIN documents d ON d.id=ku.document_id
           WHERE k.syllabus_id=?""", (sid,)).fetchall()
    # 实验分布
    exp_dist = c.execute(
        "SELECT experiment,COUNT(*) n FROM ku_links WHERE syllabus_id=? AND experiment<>'' GROUP BY experiment ORDER BY n DESC",
        (sid,)).fetchall()
    # 标准分布
    std_dist = c.execute(
        "SELECT standard_no,COUNT(*) n FROM ku_links WHERE syllabus_id=? AND standard_no IS NOT NULL GROUP BY standard_no ORDER BY n DESC",
        (sid,)).fetchall()
    # 产品特殊规定
    ps = c.execute(
        "SELECT experiment,product_std,clauses_json,method_stds_json,special_params_json FROM product_special WHERE syllabus_id=?",
        (sid,)).fetchall()
    c.close()
    return {
        "syllabus_id": sid,
        "topic": info.get("topic") or info.get("requirement"),
        "cognitive_level": info.get("cognitive_level"),
        "weight": info.get("weight"),
        "ref_route": info.get("ref_route"),
        "experiments": [e["experiment"] for e in exp_dist],
        "experiment_dist": [dict(e) for e in exp_dist],
        "standard_dist": [dict(s) for s in std_dist],
        "product_special": [
            {"experiment": p["experiment"], "product_std": p["product_std"],
             "clauses": json.loads(p["clauses_json"]), "method_stds": json.loads(p["method_stds_json"]),
             "special_params": json.loads(p["special_params_json"])}
            for p in ps
        ],
        "knowledge_units": [
            {"id": k["id"], "title": k["title"], "unit_type": k["unit_type"], "tier": k["tier"],
             "experiment": json.loads(k["experiment"]) if k["experiment"] else [],
             "ref_standards": json.loads(k["ref_standards"]) if k["ref_standards"] else [],
             "weight": k["weight"], "doc": k["doc_title"]}
            for k in kus
        ],
        "ku_count": len(kus),
    }


def nav_experiment(exp):
    c = _conn()
    kus = c.execute(
        """SELECT DISTINCT ku.id, ku.title, ku.tier, ku.ref_standards, ku.syllabus_ids, d.title AS doc_title
           FROM knowledge_units ku
           JOIN documents d ON d.id=ku.document_id
           WHERE ku.experiment LIKE ?""", (f'%"{exp}"%',)).fetchall()
    # 该产品实验涉及的产品标准特殊规定（跨大纲汇总）
    ps = c.execute(
        """SELECT DISTINCT product_std, clauses_json, method_stds_json, special_params_json
           FROM product_special WHERE experiment=?""", (exp,)).fetchall()
    syllabi = c.execute(
        "SELECT DISTINCT syllabus_id FROM ku_links WHERE experiment=?", (exp,)).fetchall()
    c.close()
    return {
        "experiment": exp,
        "knowledge_units": [
            {"id": k["id"], "title": k["title"], "tier": k["tier"],
             "ref_standards": json.loads(k["ref_standards"]) if k["ref_standards"] else [],
             "syllabus_ids": json.loads(k["syllabus_ids"]) if k["syllabus_ids"] else [],
             "doc": k["doc_title"]}
            for k in kus
        ],
        "ku_count": len(kus),
        "related_syllabus": [s["syllabus_id"] for s in syllabi],
        "product_special": [
            {"product_std": p["product_std"], "clauses": json.loads(p["clauses_json"]),
             "method_stds": json.loads(p["method_stds_json"]),
             "special_params": json.loads(p["special_params_json"])}
            for p in ps
        ],
    }


def nav_standard(std):
    c = _conn()
    # 归一化匹配
    kus = c.execute(
        """SELECT ku.id, ku.title, ku.tier, ku.experiment, ku.syllabus_ids, d.title AS doc_title
           FROM knowledge_units ku JOIN documents d ON d.id=ku.document_id
           WHERE ku.ref_standards LIKE ?""", (f'%"{std}"%',)).fetchall()
    syllabi = c.execute(
        "SELECT DISTINCT syllabus_id FROM ku_links WHERE standard_no=?", (std,)).fetchall()
    # 该产品标准本身写入库的特殊规定（即使暂无 KU 也能查到）
    ps = c.execute(
        """SELECT experiment, clauses_json, method_stds_json, special_params_json
           FROM product_special WHERE product_std=?""", (std,)).fetchall()
    c.close()
    return {
        "standard": std,
        "knowledge_units": [
            {"id": k["id"], "title": k["title"], "tier": k["tier"],
             "experiment": json.loads(k["experiment"]) if k["experiment"] else [],
             "syllabus_ids": json.loads(k["syllabus_ids"]) if k["syllabus_ids"] else [],
             "doc": k["doc_title"]}
            for k in kus
        ],
        "ku_count": len(kus),
        "related_syllabus": [s["syllabus_id"] for s in syllabi],
        "product_special": [
            {"experiment": p["experiment"], "clauses": json.loads(p["clauses_json"]),
             "method_stds": json.loads(p["method_stds_json"]),
             "special_params": json.loads(p["special_params_json"])}
            for p in ps
        ],
    }


def search_kb(keyword, limit=30):
    c = _conn()
    like = f"%{keyword}%"
    rows = c.execute(
        """SELECT ku.id, ku.title, ku.tier, ku.experiment, ku.syllabus_ids, ku.ref_standards,
                ku.product_special, d.title AS doc_title
           FROM knowledge_units ku JOIN documents d ON d.id=ku.document_id
           WHERE ku.title LIKE ? OR ku.key_requirements LIKE ? OR ku.interpretation LIKE ?
                 OR ku.product_special LIKE ?
           LIMIT ?""", (like, like, like, like, limit)).fetchall()
    c.close()
    out = []
    for r in rows:
        # 若命中来自 product_special，顺带回带命中的特殊规定片段
        ps_hit = []
        if r["product_special"]:
            try:
                arr = json.loads(r["product_special"])
                for item in arr:
                    sp = item.get("special_params", [])
                    hit = [s for s in sp if keyword in s]
                    if hit:
                        ps_hit.append({"experiment": item.get("experiment"),
                                       "product_std": item.get("product_std"),
                                       "matched": hit})
            except Exception:
                pass
        out.append({"id": r["id"], "title": r["title"], "tier": r["tier"],
             "experiment": json.loads(r["experiment"]) if r["experiment"] else [],
             "syllabus_ids": json.loads(r["syllabus_ids"]) if r["syllabus_ids"] else [],
             "ref_standards": json.loads(r["ref_standards"]) if r["ref_standards"] else [],
             "doc": r["doc_title"], "product_special_hit": ps_hit})
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python kb/query_links.py <syllabus|experiment|standard|search> <值>")
        sys.exit(1)
    mode, val = sys.argv[1], sys.argv[2]
    fn = {"syllabus": nav_syllabus, "experiment": nav_experiment, "standard": nav_standard, "search": search_kb}[mode]
    res = fn(val) if mode != "search" else fn(val)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:4000])
