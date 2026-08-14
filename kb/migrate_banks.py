# -*- coding: utf-8 -*-
"""
题库迁移器 v1 —— 把历史题库对齐到 bank/2.0 契约。

修复系统测试暴露的 4 类缺陷：
  1) match 题型前端 grade.js 不支持 → 转为 judge（一对一映射，不编造干扰项）
  2) src 缺失或为字符串 → 统一为 {"standard_no": ..., "clause": ...}
  3) 题号跨库重复（C01/F01 撞车）→ 加库前缀
  4) meta 缺 bank_version / scoring

用法: python kb/migrate_banks.py [--dry]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "rules")

SCORING = {"choice": 2, "judge": 1, "fill": 2, "calc": "by_sub"}

# ---------------------------------------------------------------- 溯源映射表
# 条款号来自 kb/raw/pages_*.json 的 OCR 正文目录，非臆造。
SRC_3956 = {
    "C01": "3", "C02": "6", "C03": "前言", "C04": "4",
    "F01": "1", "F02": "表2", "F03": "7", "CALC1": "附录A",
}
STD_3956 = "GB/T 3956-2008"

# 2951 复合库：题目分属 .11（尺寸/机械性能）与 .12（热老化）两分部
SRC_2951AB = {
    # id: (分部, 条款)
    "C01": ("11", "8.1.2"), "C02": ("11", "8.1.5"), "C03": ("11", "9.1.3"),
    "C04": ("11", "9.1.3"), "C05": ("11", "9.1.7"), "C06": ("12", "8.1.2"),
    "C07": ("12", "8.1.3"), "C08": ("12", "8.1.3"), "C09": ("11", "9.1.4"),
    "C10": ("12", "8.3"), "C11": ("11", "9.1.8"), "C12": ("11", "8.1.5"),
    "C13": ("11", "9.1.4"), "C14": ("11", "9.1.3"), "C15": ("11", "9.1.4"),
    "F01": ("11", "8.1.4"), "F02": ("11", "8.1.4"), "F03": ("11", "9.1.8"),
    "F04": ("11", "9.1.8"), "F05": ("11", "9.1.4"), "F06": ("12", "8.1.2"),
    "F07": ("12", "8.3"), "F08": ("12", "8.2"), "F09": ("11", "8.1.4"),
    "F10": ("11", "9.1.4"), "F11": ("11", "9.1.8"), "F12": ("11", "9.1.7"),
    "F13": ("11", "9.1.7"), "F14": ("11", "9.1.3"), "F15": ("11", "9.1.4"),
    "CALC1": ("11", "9.1.4"), "CALC2": ("11", "9.1.4"),
}

# ---------------------------------------------------------------- match→judge
# 一半设为"错误命题"，考察真实掌握而非全选对。答案与解析均源自原 match 配对。
JUDGE_3956 = [
    dict(id="J01", q="GB/T 3956-2008 中第 1 种导体为实心导体，用于固定敷设的电缆。",
         answer=True, clause="5.1",
         explain="第1种=实心导体，只用于固定敷设。实心截面大时刚性强，无法反复弯曲。"),
    dict(id="J02", q="第 2 种导体属于软导体，主要用于软电缆和软线。",
         answer=False, clause="5.2",
         explain="说反了。第2种是绞合导体，仍属固定敷设类；软导体是第5种和第6种。"),
    dict(id="J03", q="第 5 种和第 6 种导体为软导体，用于软电缆和软线。",
         answer=True, clause="6",
         explain="第5/6种单丝更细、根数更多，柔软性满足反复移动弯曲的需求。"),
]

JUDGE_2951AB = [
    dict(id="J01", q="测量绝缘厚度应使用投影仪或读数显微镜，放大倍率不小于 10 倍。",
         answer=True, part="11", clause="8.1.2",
         explain="薄绝缘需 0.01mm 级读数精度，光学放大是达到该精度的前提。"),
    dict(id="J02", q="除 PE、PP 外的一般橡塑绝缘哑铃试样，拉力试验速度为 25±5 mm/min。",
         answer=False, part="11", clause="9.1.7",
         explain="应为 250±50 mm/min。25±5 mm/min 是 PE、PP 等聚烯烃专用的慢速。"),
    dict(id="J03", q="空气烘箱老化时，烘箱的换气率应保持在每小时 8~20 次。",
         answer=True, part="12", clause="8.1.2",
         explain="换气过少则挥发物积聚改变气氛，过多则带走热量致温度不均。"),
    dict(id="J04", q="氧弹老化的试验介质为纯氧，压力为 (2.1±0.07) MPa。",
         answer=True, part="12", clause="8.3",
         explain="纯氧加压提高氧分压，成倍加速氧化降解，缩短老化考核周期。"),
    dict(id="J05", q="空气弹老化与氧弹老化使用相同的试验介质。",
         answer=False, part="12", clause="8.2",
         explain="空气弹用压缩空气（约0.55MPa），氧弹用纯氧。介质与压力都不同。"),
    dict(id="J06", q="热老化处理后的试样，在进行拉力试验前应在室温下放置至少 16 h。",
         answer=True, part="12", clause="8.1.3",
         explain="回温以消除热历史与残余应力，否则测得的强度和伸长率偏离真值。"),
    dict(id="J07", q="整绝缘试件的截面积可用近似公式 A=π(D-δ)δ 计算，其中 D 为绝缘外径、δ 为平均绝缘厚度。",
         answer=True, part="11", clause="9.1.4",
         explain="圆环面积 π/4·(D²-d²) 在 d=D-2δ 时恰好化简为 π(D-δ)δ，是精确等式而非近似。"),
    dict(id="J08", q="质量法计算哑铃试样截面积的公式为 A = m·ρ/(1000·l)。",
         answer=False, part="11", clause="9.1.4",
         explain="密度在分母：A = m/(1000·ρ·l)。密度越大，同质量对应的体积越小、截面积越小。"),
]


def to_src(std, clause):
    return {"standard_no": std, "clause": str(clause)}


def parse_str_src(s):
    """'GB/T 2951.13-2008 §5 预处理' → {standard_no, clause}"""
    if not isinstance(s, str) or not s.strip():
        return None
    m = re.match(r"\s*(GB/T[\s\d\.\-]+|JB/T[\s\d\.\-]+|IEC[\s\d\.\-:]+)\s*(.*)$", s)
    if not m:
        return {"standard_no": s.strip(), "clause": ""}
    std = m.group(1).strip()
    rest = (m.group(2) or "").strip()
    cl = re.findall(r"§\s*([\d\.]+(?:\s*/\s*§\s*[\d\.]+)*)", rest)
    clause = cl[0].replace(" ", "") if cl else rest
    return {"standard_no": std, "clause": clause}


def prefix_ids(bank, pfx):
    n = 0
    for t in ("choice", "judge", "fill", "match", "calc"):
        for it in bank.get(t, []) or []:
            i = it.get("id")
            if i and not str(i).startswith(pfx):
                it["id"] = pfx + str(i)
                n += 1
    return n


def report(tag, msg):
    print(f"  [{tag}] {msg}")


def migrate_3956(dry):
    p = os.path.join(RULES, "gbt_3956.json")
    b = json.load(open(p, encoding="utf-8"))
    print("== gbt_3956.json")

    for t in ("choice", "fill", "calc"):
        for it in b.get(t, []) or []:
            cl = SRC_3956.get(it.get("id"))
            if cl:
                it["src"] = to_src(STD_3956, cl)
    report("src", f"补溯源 {sum(len(b.get(t) or []) for t in ('choice','fill','calc'))} 题")

    b["judge"] = [dict(id=j["id"], q=j["q"], answer=j["answer"], points=1,
                       explain=j["explain"], src=to_src(STD_3956, j["clause"]))
                  for j in JUDGE_3956]
    b.pop("match", None)
    report("match→judge", f"{len(JUDGE_3956)} 题（原 3 组连线）")

    n = prefix_ids(b, "B3956_")
    report("id", f"加前缀 B3956_ 共 {n} 题")

    meta = b.setdefault("meta", {})
    meta["bank_version"] = "bank/2.0"
    meta.setdefault("standard", [STD_3956])
    meta["scoring"] = SCORING
    meta["migrated"] = "match→judge; src结构化; id加前缀"

    if not dry:
        json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return b


def migrate_2951ab(dry):
    p = os.path.join(RULES, "gbt_2951_11_12.json")
    b = json.load(open(p, encoding="utf-8"))
    print("== gbt_2951_11_12.json")

    miss = []
    for t in ("choice", "fill", "calc"):
        for it in b.get(t, []) or []:
            hit = SRC_2951AB.get(it.get("id"))
            if hit:
                it["src"] = to_src(f"GB/T 2951.{hit[0]}-2008", hit[1])
            else:
                miss.append(it.get("id"))
    report("src", f"补溯源完成，未命中 {miss if miss else '无'}")

    b["judge"] = [dict(id=j["id"], q=j["q"], answer=j["answer"], points=1,
                       explain=j["explain"],
                       src=to_src(f"GB/T 2951.{j['part']}-2008", j["clause"]))
                  for j in JUDGE_2951AB]
    b.pop("match", None)
    report("match→judge", f"{len(JUDGE_2951AB)} 题（原 8 组连线，其中 3 题设为错误命题）")

    n = prefix_ids(b, "B2951AB_")
    report("id", f"加前缀 B2951AB_ 共 {n} 题")

    meta = b.setdefault("meta", {})
    meta["bank_version"] = "bank/2.0"
    meta.setdefault("standard", ["GB/T 2951.11-2008", "GB/T 2951.12-2008"])
    meta["scoring"] = SCORING
    meta["migrated"] = "match→judge; src结构化; id加前缀"

    if not dry:
        json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return b


def migrate_mvp(dry):
    p = os.path.join(RULES, "gbt_2951_kb_mvp.json")
    b = json.load(open(p, encoding="utf-8"))
    print("== gbt_2951_kb_mvp.json")

    conv = 0
    for t in ("choice", "judge", "fill", "calc"):
        for it in b.get(t, []) or []:
            s = it.get("src")
            if isinstance(s, str):
                it["src"] = parse_str_src(s)
                conv += 1
    report("src", f"字符串 src → 结构化 dict 共 {conv} 题")

    n = prefix_ids(b, "BMVP_")
    report("id", f"加前缀 BMVP_ 共 {n} 题")

    meta = b.setdefault("meta", {})
    meta["bank_version"] = "bank/2.0"
    meta["scoring"] = SCORING
    meta["migrated"] = "src结构化; id加前缀"

    if not dry:
        json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return b


def main():
    dry = "--dry" in sys.argv
    if dry:
        print("*** DRY RUN，不写盘 ***")
    migrate_3956(dry)
    migrate_2951ab(dry)
    migrate_mvp(dry)
    print("\n完成。" + ("（未写盘）" if dry else "已写回 rules/"))


if __name__ == "__main__":
    main()
