# -*- coding: utf-8 -*-
"""
build_links.py — 把 link_index.json 的三层结构化链接真正落进 kb.db。
让知识库本体（而非仅展示层 JSON）具备可检索的结构化关系：

  大纲条目(S0xx) ──实验(exp)──▶ 方法/产品标准(std) ──▶ 知识单元(ku)
  大纲条目(S0xx) ──实验(exp)──▶ 产品标准特殊规定(product_special)

落库内容：
  1) knowledge_units 增加列：experiment / ref_standards / syllabus_ids /
     ref_route / weight / tier / product_special （每个知识单元自描述）
  2) ku_links 关联表（ku_id ↔ syllabus_id ↔ experiment，多对多，完全可追溯）
  3) product_special 表（syllabus_id × experiment × product_std 的特殊规定，第三层）

实验归属采用【内容匹配】：对知识单元正文用实验关键词判定它到底属于哪个实验，
避免“标准→大纲→大纲的全部实验”造成的爆炸式误关联。

幂等：重复运行会先 DROP 新建表/列再填充，可随时重跑（教材入库后重跑即可接入第三层）。
用法：python kb/build_links.py
"""
import sqlite3, json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LI = os.path.join(ROOT, "public", "data", "link_index.json")
DB = os.path.join(ROOT, "kb", "kb.db")


def norm_std(s):
    if not s:
        return None
    s = s.replace('∕', '/').replace('／', '/').replace('\\', '/')
    s = re.sub(r'\s+', '', s)
    m = re.match(r'(GB/T|JB/T|GB|JB)(\d+(?:\.\d+)*)', s)
    return (m.group(1) + m.group(2)) if m else None


def base_std(s):
    m = re.match(r'(GB/T|JB/T|GB|JB)(\d+)', s or '')
    return m.group(1) + m.group(2) if m else s


# 实验 -> 关键词（用于按知识单元正文判定实验归属）。
# 每个实验：(名称关键词, 子关键词)。
#   命中任一名称关键词 ⇒ 强匹配（实验之名即正文核心词，如“局部放电”“导体电阻”）；
#   仅靠子关键词 ⇒ 需 >=2 个不同子关键词才匹配，避免前言/术语里零散提到“厚度/电压”被误挂。
EXP_KEYWORDS = {
    "局部放电检测": (["局部放电", "局放", "视在放电量"], ["放电量", "partial discharge", "放电试验"]),
    "交流耐电压试验": (["交流耐电压", "交流电压试验", "交流耐压", "工频电压试验"], ["耐电压试验", "工频耐压", "工频电压", "工频"]),
    "绝缘、护套厚度测量": (["绝缘厚度", "护套厚度", "平均厚度", "最薄点厚度"], ["厚度测量", "外形尺寸", "宽度", "外径", "截面", "厚度"]),
    "绝缘、护套拉伸试验": (["抗张强度", "断裂伸长率", "拉伸试验"], ["拉伸强度", "断裂伸长", "拉伸速度"]),
    "导体电阻测量": (["导体电阻", "导体直流电阻", "直流电阻"], ["电阻测量", "测量导体", "电阻值"]),
    "绝缘电阻检测": (["绝缘电阻", "绝缘阻值", "体积电阻率", "表面电阻率"], ["高阻计", "绝缘电阻值"]),
    "聚氯乙烯高温压力、热冲击试验": (["高温压力", "热冲击试验", "热冲击"], ["压力试验", "热稳定性试验", "失重试验", "热变形"]),
    "电缆介质损耗检测": (["介质损耗", "介质损耗角正切", "损耗角正切"], ["tanδ", "tgδ", "损耗角", "tan ", "tg "]),
    "冲击电压试验": (["冲击电压试验", "雷电冲击", "操作冲击"], ["冲击试验", "impulse"]),
    "半导体电阻率检测": (["体积电阻率", "表面电阻率", "半导电层电阻率"], ["半导体", "电阻率", "半导电", "屏蔽电阻率"]),
    "交联聚乙烯绝缘热延伸和热收缩试验": (["热延伸", "热收缩试验", "热收缩"], ["交联聚乙烯", "XLPE", "负荷下伸长率", "永久变形", "熔体流动速率"]),
    "绝缘和护套老化试验": (["老化试验", "热老化试验", "空气弹", "氧弹"], ["热老化", "人工气候老化", "气候老化"]),
    "直流耐电压试验": (["直流耐电压", "直流电压试验", "直流耐压"], ["耐直流电压", "直流电压试验方法"]),
    "低温冲击、低温拉伸和低温卷绕试验": (["低温冲击", "低温拉伸", "低温卷绕"], ["低温试验", "卷绕试验", "低温脆化"]),
    "单根燃烧试验": (["单根燃烧试验", "单根垂直燃烧", "垂直燃烧"], ["延燃", "阻燃", "炭化", "上夹具", "单根"]),
    "基础知识（单位制与基本术语）": (["单位制", "计量单位", "基本术语"], ["SI", "导出单位", "物理量", "国际单位"]),
    "弹性体专用性能试验": (["耐臭氧试验", "浸矿物油试验", "弹性体专用"], ["弹性体", "耐臭氧", "浸矿物油", "臭氧试验", "橡皮绝缘", "橡塑"]),
    "误差与不确定度": (["测量误差", "不确定度", "数值修约"], ["系统误差", "随机误差", "有效数字", "准确度等级"]),
    "检验记录与报告": (["检验记录", "检验报告", "原始记录"], ["记录表", "报告编号", "结论"]),
    "特殊性能检测": (["烟密度", "卤酸气体", "耐火试验", "特殊性能"], ["pH", "电导率", "矿物油", "填充膏", "透光率"]),
}


# ---------------- 载入 link_index ----------------
LI_DATA = json.load(open(LI, encoding='utf-8'))
syllabus = LI_DATA['syllabus']
by_exp = LI_DATA['by_experiment']
by_std = LI_DATA['by_standard']
product_standards = LI_DATA['product_standards']
by_exp_products = LI_DATA['by_experiment_products']
weight_map = LI_DATA['meta'].get('weight_map', {"了解": 1, "熟悉": 2, "掌握": 3, "熟练掌握": 4})

# 1) 标准号 -> 大纲条目（含 base 回退）
std_to_syl = {}
for k, sids in by_std.items():
    ns = norm_std(k) or k
    std_to_syl.setdefault(ns, set()).update(sids)
    std_to_syl.setdefault(base_std(ns), set()).update(sids)

# 2) 产品标准集合（归一化）
product_std_set = set()
for k in product_standards:
    product_std_set.add(norm_std(k) or k)
    product_std_set.add(base_std(norm_std(k) or k))

# 3) 方法标准 -> 实验 边（来自产品标准/实验-产品映射里列出的 method_stds）
method_std_edges = {}
for P, body in product_standards.items():
    for exp, info in body.get('experiments', {}).items():
        for ms in info.get('method_stds', []):
            method_std_edges.setdefault(norm_std(ms) or ms, set()).add(exp)
for exp, lst in by_exp_products.items():
    for item in lst:
        for ms in item.get('method_stds', []):
            method_std_edges.setdefault(norm_std(ms) or ms, set()).add(exp)

# 4) 实验 -> 涉及该实验的产品标准及其特殊规定
exp_to_products = {}
for P, body in product_standards.items():
    np = norm_std(P) or P
    for exp, info in body.get('experiments', {}).items():
        exp_to_products.setdefault(exp, []).append((np, info))

# 5) 大纲 -> 实验
syl_to_exps = {}
for exp, sids in by_exp.items():
    for s in sids:
        syl_to_exps.setdefault(s, set()).add(exp)
for sid, body in syllabus.items():
    for exp in body.get('experiments', []):
        syl_to_exps.setdefault(sid, set()).add(exp)

# 6) 教材识别
TEXTBOOK_MARK = ('电缆产品检验', '教材', '性能检验')

_CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7,
           '八': 8, '九': 9, '十': 10, '十一': 11, '十二': 12, '十三': 13,
           '十四': 14, '十五': 15, '十六': 16}


def is_textbook(title):
    return any(m in (title or '') for m in TEXTBOOK_MARK)


def textbook_book_key(title):
    t = title or ''
    if '非电性能' in t:
        return '非电性能检验'
    if '电性能' in t:
        return '电性能检验'
    if '电缆产品检验' in t:
        return '电缆产品检验'
    return None


def parse_chapter(text):
    if not text:
        return None
    m = re.search(r'第\s*([一二三四五六七八九十\d]+)\s*章', text)
    if not m:
        return None
    s = m.group(1)
    return int(s) if s.isdigit() else _CN_NUM.get(s)


# ---------------- 连接 kb.db ----------------
c = sqlite3.connect(DB)
cur = c.cursor()
cur.execute("SELECT id,title,source FROM documents")
doc_std, doc_is_textbook = {}, {}
for did, title, src in cur.fetchall():
    doc_std[did] = norm_std(title)
    doc_is_textbook[did] = is_textbook(title)

# 取知识单元 + 其正文（sections.content），用于内容匹配实验
cur.execute("""SELECT ku.id,ku.document_id,ku.title,ku.key_requirements,s.content
               FROM knowledge_units ku LEFT JOIN sections s ON ku.section_id=s.id""")
kus = cur.fetchall()

# 教材章节预扫描：对每个教材文档，按 page_start 顺序扫 sections，跟踪当前「第X章」，
# 把每个知识单元映射到其所属章节，用于把教材 KU 精确挂到对应大纲章节（而非整本书）。
textbook_doc_ids = [did for did, t in doc_std.items() if doc_is_textbook.get(did, False)]
ku_chapter = {}
for did in textbook_doc_ids:
    rows = cur.execute(
        """SELECT ku.id, s.content FROM knowledge_units ku
           JOIN sections s ON ku.section_id=s.id
           WHERE ku.document_id=? ORDER BY s.page_start, s.id""", (did,)).fetchall()
    cur_ch = None
    for ku_id, content in rows:
        ch = parse_chapter(content)
        if ch:
            cur_ch = ch
        ku_chapter[ku_id] = cur_ch

book_to_syl = {}
book_chapter_to_syl = {}  # (book_key, chapter_no) -> set(sid)
for sid, b in syllabus.items():
    topic = b.get('topic', '')
    for key in ('电性能检验', '非电性能检验', '电缆产品检验'):
        if key in topic:
            book_to_syl.setdefault(key, set()).add(sid)
            ch = parse_chapter(topic)
            if ch:
                book_chapter_to_syl.setdefault((key, ch), set()).add(sid)


def dominant_route(routes):
    rs = set(r for r in routes if r)
    if not rs:
        return 'content-derived'
    for pref in ('product-condition', 'method', 'content-derived'):
        if pref in rs:
            return pref
    return sorted(rs)[0]


def weight_of(sid):
    b = syllabus.get(sid, {})
    if isinstance(b.get('weight'), (int, float)):
        return int(b['weight'])
    return int(weight_map.get(b.get('cognitive_level'), 1))


def match_experiments(text):
    if not text:
        return set()
    hits = {}
    for exp, (name_kw, sub_kw) in EXP_KEYWORDS.items():
        # 名称关键词命中 -> 强匹配
        if any(kw in text for kw in name_kw):
            hits[exp] = 99
            continue
        # 仅靠子关键词 -> 需 >=2 个不同子关键词才算，降低前言/术语误挂
        n = sum(1 for kw in sub_kw if kw in text)
        if n >= 2:
            hits[exp] = n
    return set(hits.keys())


# ---------------- 建表 + 加列 ----------------
cur.executescript("""
DROP TABLE IF EXISTS ku_links;
CREATE TABLE ku_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ku_id INTEGER, syllabus_id TEXT, experiment TEXT, standard_no TEXT,
  ref_route TEXT, weight INTEGER, tier TEXT,
  UNIQUE(ku_id, syllabus_id, experiment)
);
DROP TABLE IF EXISTS product_special;
CREATE TABLE product_special (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  syllabus_id TEXT, experiment TEXT, product_std TEXT,
  clauses_json TEXT, method_stds_json TEXT, special_params_json TEXT
);
""")
for col in ('experiment', 'ref_standards', 'syllabus_ids', 'ref_route', 'weight', 'tier', 'product_special'):
    if cur.execute("SELECT COUNT(*) FROM pragma_table_info('knowledge_units') WHERE name=?", (col,)).fetchone()[0] == 0:
        cur.execute(f"ALTER TABLE knowledge_units ADD COLUMN {col} TEXT")

# ---------------- 逐知识单元落链接 ----------------
ku_rows, ku_update = [], {}
stats = {'linked_ku': 0, 'method': 0, 'product': 0, 'textbook': 0, 'reference': 0, 'with_product_special': 0}

for ku_id, did, ku_title, key_req, content in kus:
    std = doc_std.get(did)
    textbook = doc_is_textbook.get(did, False)
    if std in product_std_set:
        tier = 'product'
    elif std is not None:
        tier = 'method'
    elif textbook:
        tier = 'textbook'
    else:
        tier = 'reference'
    stats[tier] = stats.get(tier, 0) + 1

    sids = set()
    if std:
        sids |= set(std_to_syl.get(std, []))
        if not sids and base_std(std) in std_to_syl:
            sids |= set(std_to_syl[base_std(std)])
    if textbook:
        bk = textbook_book_key(cur.execute(
            "SELECT title FROM documents WHERE id=?", (did,)).fetchone()[0])
        if bk:
            ch = ku_chapter.get(ku_id)
            if bk and ch and (bk, ch) in book_chapter_to_syl:
                sids |= set(book_chapter_to_syl[(bk, ch)])
            elif bk in book_to_syl:
                sids |= set(book_to_syl[bk])

    # 内容匹配实验（判定此知识单元到底讲哪个实验）
    text = " ".join([ku_title or '', key_req or '', content or ''])
    matched = match_experiments(text)
    # 回退：内容未命中时，用方法标准边 / 大纲实验
    if not matched:
        if std and std in method_std_edges:
            matched = set(method_std_edges[std])
        else:
            matched = set()
            for s in sids:
                matched |= syl_to_exps.get(s, set())

    # 仅保留“既与本单元内容相关、又属于该大纲实验”的交集，避免爆炸
    routes, weights = [], []
    for sid in sids:
        exps_for_link = matched & syl_to_exps.get(sid, set())
        if not exps_for_link:
            # 内容与大纲实验无交集：仍保留标准级链接（实验留空），保证可追溯
            exps_for_link = {''}
        for exp in exps_for_link:
            ku_rows.append((ku_id, sid, exp, std, dominant_route([syllabus.get(sid, {}).get('ref_route')]), weight_of(sid), tier))
        routes.append(syllabus.get(sid, {}).get('ref_route'))
        weights.append(weight_of(sid))

    if sids:
        stats['linked_ku'] += 1

    # 产品特殊规定：仅挂到本单元命中的实验上
    psp = []
    for exp in matched:
        for (P, info) in exp_to_products.get(exp, []):
            sp = info.get('special_params', [])
            if isinstance(sp, list) and sp:
                psp.append({'product_std': P, 'experiment': exp,
                            'clauses': info.get('clauses', []),
                            'special_params': sp})
    if psp:
        stats['with_product_special'] += 1

    ku_update[ku_id] = {
        'experiment': json.dumps(sorted(matched), ensure_ascii=False) if matched else None,
        'ref_standards': json.dumps([std], ensure_ascii=False) if std else None,
        'syllabus_ids': json.dumps(sorted(sids), ensure_ascii=False) if sids else None,
        'ref_route': dominant_route(routes),
        'weight': (max(weights) if weights else None),
        'tier': tier,
        'product_special': json.dumps(psp, ensure_ascii=False) if psp else None,
    }

cur.executemany(
    "INSERT OR IGNORE INTO ku_links (ku_id,syllabus_id,experiment,standard_no,ref_route,weight,tier) VALUES (?,?,?,?,?,?,?)",
    ku_rows)
for ku_id, cols in ku_update.items():
    cur.execute(
        "UPDATE knowledge_units SET experiment=?,ref_standards=?,syllabus_ids=?,ref_route=?,weight=?,tier=?,product_special=? WHERE id=?",
        (cols['experiment'], cols['ref_standards'], cols['syllabus_ids'], cols['ref_route'],
         cols['weight'], cols['tier'], cols['product_special'], ku_id))

# product_special 表（第三层，按大纲可查）
psp_rows = []
for sid, exps in syl_to_exps.items():
    for exp in exps:
        for (P, info) in exp_to_products.get(exp, []):
            psp_rows.append((
                sid, exp, P,
                json.dumps(info.get('clauses', []), ensure_ascii=False),
                json.dumps(info.get('method_stds', []), ensure_ascii=False),
                json.dumps(info.get('special_params', []), ensure_ascii=False),
            ))
cur.executemany(
    "INSERT INTO product_special (syllabus_id,experiment,product_std,clauses_json,method_stds_json,special_params_json) VALUES (?,?,?,?,?,?)",
    psp_rows)
c.commit()

print("=== build_links 完成（内容匹配实验） ===")
print("knowledge_units 总数:", len(kus))
print("已落大纲链接的 KU:", stats['linked_ku'])
print("tier 分布:", {k: v for k, v in stats.items() if k in ('method', 'product', 'textbook', 'reference')})
print("挂有产品特殊规定的 KU:", stats['with_product_special'])
print("ku_links 行数:", len(ku_rows))
print("product_special 行数:", len(psp_rows))
c.close()
