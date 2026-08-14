# -*- coding: utf-8 -*-
import json, re, os, glob

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

# 大纲 resource 部分要求的 13 个标准 + 9 个教材章节
SYLL_STD = [
    "GB/T 2951", "GB/T 3048", "GB/T 3956", "GB/T 5013", "GB/T 5023",
    "GB/T 9330", "GB/T 19666", "JB/T 8734", "JB/T 8735", "JB/T 10491.4",
    "GB/T 12706", "GB/T 11017", "GB/T 18890",
]
SYLL_TEXTBOOK = ["教材", "电缆产品检验"]

# 部署的资产
BANKS = {
    "gbt_2951_11_12": "data/gbt_2951_11_12.json",
    "gbt_3048_8": "data/gbt_3048_8.json",
    "gbt_3956": "data/gbt_3956.json",
    "gbt_2951_full": "data/gbt_2951_full.json",
    "gbt_3048_full": "data/gbt_3048_full.json",
    "gbt_others_full": "data/gbt_others_full.json",
    "gbt_5023_full": "data/gbt_5023_full.json",
    "gbt_8734_full": "data/gbt_8734_full.json",
    "gbt_10491_full": "data/gbt_10491_full.json",
}
DECKS = {
    "gbt_2951_11_12": "data/gbt_2951_flashcards.json",
    "gbt_3048_8": "data/gbt_3048_8_flashcards.json",
    "gbt_3956": "data/gbt_3956_flashcards.json",
    "gbt_2951_full": "data/gbt_2951_full_flashcards.json",
    "gbt_3048_full": "data/gbt_3048_full_flashcards.json",
    "gbt_others_full": "data/gbt_others_full_flashcards.json",
    "gbt_5023_full": "data/gbt_5023_full_flashcards.json",
    "gbt_8734_full": "data/gbt_8734_full_flashcards.json",
    "gbt_10491_full": "data/gbt_10491_full_flashcards.json",
}
MATS = {
    "gbt_2951_11_12": "data/gbt_2951_materials.json",
    "gbt_3048_8": "data/gbt_3048_8_materials.json",
    "gbt_3956": "data/gbt_3956_materials.json",
    "gbt_2951_full": "data/gbt_2951_full_materials.json",
    "gbt_3048_full": "data/gbt_3048_full_materials.json",
    "gbt_others_full": "data/gbt_others_full_materials.json",
    "gbt_5023_full": "data/gbt_5023_full_materials.json",
    "gbt_8734_full": "data/gbt_8734_full_materials.json",
    "gbt_10491_full": "data/gbt_10491_full_materials.json",
}

std_re = re.compile(r"(?:GB/T|GB|JB/T|JB|T/?[A-Z]+)\s*[\d]{3,6}(?:\.\d+)?")

def collect_text(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("src", "standard_no", "std", "family", "topic", "requirement", "title", "name", "q", "stem", "front", "back", "section", "clause", "ref_standards"):
                acc.append(str(v))
            collect_text(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect_text(v, acc)
    else:
        acc.append(str(obj))

def norm(s):
    return s.replace(" ", "").replace("/", "/")

def std_in(text, std):
    # 归一化后做前缀子串匹配：GB/T 2951 命中 GB/T2951 / GB/T2951.11 等
    return norm(std) in norm(text)

def analyze(filemap, label):
    print("\n===== %s =====" % label)
    # 每个资产 -> 命中的大纲标准集合
    asset_cov = {}
    for name, rel in filemap.items():
        p = os.path.join(DATA, rel)
        if not os.path.exists(p):
            print("  [缺失] %s -> %s" % (name, rel))
            asset_cov[name] = set()
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        acc = []
        collect_text(data, acc)
        text = "\n".join(acc)
        hit = set(s for s in SYLL_STD if std_in(text, s))
        # 额外发现的其他标准
        extra = set()
        for m in std_re.findall(text):
            mm = m.replace(" ", "")
            if mm.startswith(("GB/T", "JB/T", "GB", "JB")) and mm not in hit:
                extra.add(mm)
        asset_cov[name] = hit
        # 统计题/卡/节数量
        cnt = None
        for key in ("questions", "cards", "sections"):
            if isinstance(data, dict) and key in data:
                cnt = len(data[key])
        print("  %-18s 命中标准: %s" % (name, ", ".join(sorted(hit)) if hit else "—"))
        if extra:
            print("                      额外标准: %s" % ", ".join(sorted(extra)))
    return asset_cov

bank_cov = analyze(BANKS, "题库 (出卷器/自测卷数据源)")
deck_cov = analyze(DECKS, "闪卡 (闪卡卡组)")
mat_cov = analyze(MATS, "学习材料 (学习板块)")

# 全局：统计每个大纲标准在全部资产中具体出现哪些分篇
VARIANT = {s: set() for s in SYLL_STD}
all_files = {}
all_files.update(BANKS); all_files.update(DECKS); all_files.update(MATS)
for rel in all_files.values():
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        continue
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    acc = []
    collect_text(data, acc)
    text = norm("\n".join(acc))
    for m in std_re.findall("\n".join(acc)):
        mm = norm(m)
        for s in SYLL_STD:
            if mm == norm(s) or mm.startswith(norm(s) + "."):
                VARIANT[s].add(mm)

# 汇总：每个大纲标准是否被 题库/闪卡/材料 任一覆盖
print("\n\n############ 大纲 13 标准 覆盖矩阵 ############")
print("%-16s %-8s %-8s %-8s %-8s" % ("标准", "题库", "闪卡", "材料", "覆盖?"))
allcov = {}
for s in SYLL_STD:
    in_bank = any(s in v for v in bank_cov.values())
    in_deck = any(s in v for v in deck_cov.values())
    in_mat = any(s in v for v in mat_cov.values())
    covered = in_bank or in_deck or in_mat
    allcov[s] = (in_bank, in_deck, in_mat, covered)
    print("%-16s %-8s %-8s %-8s %-8s" % (
        s, "✓" if in_bank else "✗", "✓" if in_deck else "✗",
        "✓" if in_mat else "✗", "全覆盖" if covered else "❌缺失"))

missing = [s for s, cov in allcov.items() if not cov[3]]
print("\n❌ 完全缺失的标准 (%d): %s" % (len(missing), ", ".join(missing) if missing else "无"))

print("\n############ 各标准覆盖深度（实际出现分篇） ############")
for s in SYLL_STD:
    parts = sorted(VARIANT[s])
    if not parts:
        depth = "❌ 完全缺失"
    elif len(parts) == 1 and parts[0] != norm(s):
        depth = "⚠ 仅个别分篇: " + ", ".join(parts)
    else:
        depth = "✓ 覆盖 (%d处: %s)" % (len(parts), ", ".join(parts[:8]) + ("..." if len(parts) > 8 else ""))
    print("  %-16s %s" % (s, depth))

# 教材章节覆盖
print("\n############ 大纲 9 教材章节 覆盖检查 ############")
for tb in SYLL_TEXTBOOK:
    in_bank = any(tb in "\n".join(str(x) for x in []) for _ in [0])
    print("  关键词 '%s'：需人工/看 theory 部分是否以标准题覆盖（教材原文未入库）" % tb)

# 大纲 theory/practical 命题点 -> 标准映射覆盖
print("\n############ theory/practical 命题点 -> 标准 覆盖 ############")
theory_map = {
    "基础知识(有效数字/误差/不确定度)": [],
    "2.1 导体电阻": ["GB/T 3048", "GB/T 3956"],
    "2.2 绝缘电阻": ["GB/T 3048"],
    "2.3 交流耐电压": ["GB/T 3048"],
    "2.4 直流耐电压": ["GB/T 3048"],
    "2.5 介质损耗": ["GB/T 3048"],
    "2.6 局部放电": ["GB/T 3048"],
    "2.7 冲击电压": ["GB/T 3048"],
    "2.8 半导体电阻率": ["GB/T 3048"],
    "3.1 厚度测量": ["GB/T 2951"],
    "3.2 拉伸试验": ["GB/T 2951"],
    "3.3 老化试验": ["GB/T 2951"],
    "3.4 热延伸/热收缩": ["GB/T 2951"],
    "3.5 高温压力/热冲击": ["GB/T 2951"],
    "3.6 低温试验": ["GB/T 2951"],
    "实操6 单根燃烧": ["GB/T 19666"],
    "实操7 高温压力": ["GB/T 2951"],
}
for k, stds in theory_map.items():
    if not stds:
        print("  %-30s [教材/通用知识，无标准号，需教材原文]" % k)
        continue
    ok = all(allcov.get(s, (False,)*4)[3] for s in stds)
    print("  %-30s -> %s %s" % (k, ", ".join(stds), "✓覆盖" if ok else "❌缺:"+",".join(s for s in stds if not allcov.get(s,(False,)*4)[3])))
