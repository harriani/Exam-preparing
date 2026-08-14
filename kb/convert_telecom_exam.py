# -*- coding: utf-8 -*-
"""doc2kb OCR 出的《电信电缆检验员培训试题》→ 题库 JSON。
策略：整篇按"行首 数字、."流式切题，按内容判定题型（含 A/B/C/D 选项→选择；
含解题'解/答'→计算；末尾( )且无选项→判断；其余→填空/问答）。该 PDF 无答案键，
answer 一律留空，由 meta.online_bank 标记"网上题库·答案待核"。
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "kb", "raw", "pages_telecom_exam.json")
OUT = os.path.join(ROOT, "public", "data", "telecom_exam_questions.json")
SRC_TAG = "网上题库·电信电缆检验员培训试题"

d = json.load(open(SRC, encoding="utf-8"))
full = "\n".join(p.get("text", "") for p in d["pages"])

# 章节标题位置（仅用于剔除标题行本身）
HEAD_PAT = re.compile(r"^[一二三四五六七八九十]+、[一-龥]{2,10}?(?:题|空|择|算|答|验|料|问答)", re.M)

def clean(s):
    s = s.replace("\u3000", " ").strip()
    s = re.sub(r"\[公式区域:[^\]]*\]", "", s)
    s = re.sub(r"\[公式#\d+\]", "", s)
    return s.strip()

# 1) 流式切题：行首 数字[、.．)] 开启新题，后续非题头行并入
items = []  # (num, text)
cur = None
for ln in full.split("\n"):
    m = re.match(r"^\s*(\d+)[、.．)]\s*(.*)$", ln)
    if m:
        if cur is not None:
            items.append(cur)
        cur = [int(m.group(1)), clean(m.group(2))]
    else:
        if cur is not None and ln.strip():
            cur[1] += " " + clean(ln)
if cur is not None:
    items.append(cur)

# 2) 分类
bank = {
    "meta": {
        "name": "电信电缆检验员培训试题（网上题库）",
        "online_bank": True,
        "reliability": "unverified",
        "answer_note": "网上搜集的题库：题目/答案未经权威标准逐一核对，出题前请人工核对答案。",
    },
    "choice": [], "judge": [], "fill": [], "essay": [], "calc": [],
}

OPT_RE = re.compile(r"([A-D])[、.．]\s*")
SOLVE_RE = re.compile(r"(解[：:1-9]?|答[：:]|计算[：:]?|根据)", )

def split_options(text):
    """返回 (stem_without_options, [opt_texts])。选项按出现顺序保留前 4 项(A-D)，
    去掉 OCR 串入的后续题选项噪声。"""
    parts = re.split(r"(?=[A-D][、.．])", text)
    seen = []
    for p in parts:
        pm = re.match(r"^\s*([A-D])[、.．]\s*(.*)$", p, re.S)
        if pm and pm.group(2).strip():
            seen.append(clean(pm.group(2)))
    opts = seen[:4]
    stem = re.split(r"[A-D][、.．]", text)[0]
    stem = clean(stem)
    stem = re.sub(r"[（(]\s*[）)]?\s*$", "", stem)
    return stem, opts

# 每题型独立单调计数，避免 OCR 题号在各章节重复导致 id 重号
cc = jf = ff = kf = ef = 0

for num, text in items:
    if not text:
        continue
    low = text
    # 计算题：含"解："且有数值/等号，或等号密集且带单位
    is_calc = bool(re.search(r"解[：:1-9]", text)) and text.count("=") >= 1 or \
              (text.count("=") >= 2 and ("Ω" in text or "mm" in text or "km" in text
               or "电阻" in text or "电容" in text or "强度" in text))
    if is_calc:
        kf += 1
        bank["calc"].append({
            "id": f"TJ_K{kf:03d}", "title": f"计算题 {kf}",
            "stem": text, "explain": "", "points": 10, "src": SRC_TAG,
        })
        continue
    # 选择题：含 ≥2 个不同选项字母
    opts_present = set(OPT_RE.findall(text))
    if len(opts_present) >= 2:
        stem, opts = split_options(text)
        if stem and len(opts) >= 2:
            cc += 1
            bank["choice"].append({
                "id": f"TJ_C{cc:03d}", "q": stem,
                "options": opts, "answer": None, "points": 2, "src": SRC_TAG,
            })
        continue
    # 判断题：末尾 ( ) 且无选项
    if re.search(r"[（(]\s*[）)]\s*$", text) or re.search(r"[）)]\s*$", text):
        t = re.sub(r"[（(]\s*[）)]?\s*$", "", text)
        t = re.sub(r"\s*[）)]\s*$", "", t)
        if t:
            jf += 1
            bank["judge"].append({
                "id": f"TJ_J{jf:03d}", "q": t,
                "answer": None, "points": 1, "src": SRC_TAG,
            })
        continue
    # 问答 / 填空：其余。含"？"或多问句 → 问答；否则填空
    if "？" in text or "?" in text:
        ef += 1
        bank["essay"].append({
            "id": f"TJ_E{ef:03d}", "q": text, "points": 5, "src": SRC_TAG,
        })
    else:
        ff += 1
        bank["fill"].append({
            "id": f"TJ_F{ff:02d}", "q": text,
            "answers": [], "syn": [], "points": 2, "src": SRC_TAG,
        })

cnt = {k: len(bank[k]) for k in ("choice", "judge", "fill", "essay", "calc")}
bank["meta"]["_count"] = sum(cnt.values())
json.dump(bank, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("写出:", OUT)
print("各题型:", cnt, " 总计:", bank["meta"]["_count"])
