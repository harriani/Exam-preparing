# -*- coding: utf-8 -*-
"""
题库内容纠错 v1 —— 依据 kb/raw/pages_2951.11.json OCR 正文逐条核对后的修正。

修正清单（每条都注明标准原文依据，不凭记忆）：
  E1 质量法截面积公式写反       9.1.4 b2) 原文 A = 1000m/(ρ·L)，题库误作 A = m/(1000ρl)
  E2 绝缘厚度报告值答案错       8.1.5 原文"厚度的平均值δ 应按 6 个测量值计算"，题库误答"中间值"
  E3 中间值定义溯源错          "中间值"定义在 7.5，非 8.1.5
  E4 哑铃试件型号术语错        2951.11 无"1A型"（那是 GB/T 1040 塑料标准），原文为"大/小哑铃试件"
  E5 夹头断裂作废溯源错        规定在 9.1.7 c)，非 9.1.8
  E6 上标字符丢失（mojibake）  ² ³ 被写成 ?

用法: python kb/fix_content_errors.py [--dry]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "rules")

# ---------------------------------------------------------------- E6 上标修复
# 逐条精确替换，不做正则全局替换（? 在正常题干里也可能是问号）
SUP_FIX = [
    ("N/mm?", "N/mm²"),
    ("g/cm?", "g/cm³"),
    ("kg/m?", "kg/m³"),
    ("g/mm?", "g/mm³"),
    ("cm?→mm?", "cm³→mm³"),
    ("(mm?)", "(mm²)"),
    ("（mm?）", "（mm²）"),
    ("结果mm?", "结果mm²"),
    ("π(R?-r?)", "π(R²-r²)"),
    ("面积(mm?)", "面积(mm²)"),
]

fixed_log = []


def log(code, where, msg):
    fixed_log.append((code, where, msg))
    print(f"  [{code}] {where}: {msg}")


def find(bank, qid):
    for t in ("choice", "judge", "fill", "match", "calc"):
        for it in bank.get(t, []) or []:
            if it.get("id") == qid:
                return it
    return None


def fix_superscript(obj, path="") -> int:
    """递归修 mojibake，返回修复处数"""
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                nv = v
                for a, b in SUP_FIX:
                    nv = nv.replace(a, b)
                if nv != v:
                    obj[k] = nv
                    n += 1
            else:
                n += fix_superscript(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                nv = v
                for a, b in SUP_FIX:
                    nv = nv.replace(a, b)
                if nv != v:
                    obj[i] = nv
                    n += 1
            else:
                n += fix_superscript(v, f"{path}[{i}]")
    return n


def fix_2951ab(dry):
    p = os.path.join(RULES, "gbt_2951_11_12.json")
    b = json.load(open(p, encoding="utf-8"))
    print("== gbt_2951_11_12.json")

    # ---- E1 质量法公式：A = 1000m/(ρ·l)
    it = find(b, "B2951AB_C15")
    it["q"] = "用质量法 A=1000m/(ρ·l) 计算试样截面积时，密度 ρ 应取什么单位？"
    it["explain"] = ("ρ 用 g/cm³、l 用 mm、m 用 g。m/ρ 得体积（cm³），乘 1000 换成 mm³，"
                     "再除以标距 l(mm) 得 mm²。单位不统一是质量法最常见的翻车点。")
    log("E1", "C15", "题干公式 m/(1000ρl) → 1000m/(ρ·l)")

    it = find(b, "B2951AB_F05")
    it["answers"] = ["1000m/(ρl)"]
    it["syn"] = [["1000m/(ρ·l)", "1000*m/(ρ*l)", "1000m/ρl", "m/(ρl)×1000", "m/(ρ·l)*1000"]]
    it["explain"] = ("A = 1000m/(ρ·l)。m 为标距段质量(g)、ρ 密度(g/cm³)、l 标距(mm)，"
                     "1000 是 cm³→mm³ 的换算系数，结果单位 mm²。"
                     "校验：m=0.560g、ρ=1.40、l=20.0 → A=1000×0.56/(1.4×20)=20.0mm²。")
    log("E1", "F05", "标准答案 m/(1000ρl) → 1000m/(ρl)（原答案量纲差 10⁶ 倍）")

    it = find(b, "B2951AB_CALC2")
    it["subs"][0][0] = "截面积 A=1000m/(ρ·l) (mm²)"
    log("E1", "CALC2", "子题公式修正（目标值 20.0 本就按正确公式算，无需改）")

    it = find(b, "B2951AB_J08")
    it["explain"] = ("正确式为 A = 1000m/(ρ·l)：密度确实在分母，但系数 1000 在分子（cm³→mm³ 换算）。"
                     "题面把 ρ 放到分子，量纲直接错。")
    log("E1", "J08", "解析中的公式同步修正")

    # ---- E2 绝缘厚度报告值 = 平均值（8.1.5 原文）
    it = find(b, "B2951AB_C02")
    it["q"] = "进行机械性能试验时，同一试件上测得的 6 个绝缘厚度值，用于后续计算的是？"
    it["options"] = ["算术平均值", "最大值", "排序后的中间值", "最小值"]
    it["answer"] = 0
    it["explain"] = ("GB/T 2951.11 第 8.1.5 条：进行机械性能试验时，每个试件厚度的平均值 δ "
                     "应按该试件上测得的 6 个测量值计算。注意区分——'中间值'（7.5）用于"
                     "抗张强度、断裂伸长率等试验结果的汇总（9.1.8），不是用于厚度。"
                     "另外压印标记凹痕处的厚度不计入平均值，但仍须单独满足产品标准的最小值。")
    log("E2", "C02", "答案 中间值 → 算术平均值（原答案与 8.1.5 原文相反）")

    # ---- E3 中间值定义溯源
    it = find(b, "B2951AB_C12")
    it["q"] = "按 GB/T 2951.11 对“中间值”的定义，当有效数据个数为偶数时，中间值应如何确定？"
    it["src"] = {"standard_no": "GB/T 2951.11-2008", "clause": "7.5"}
    it["explain"] = ("第 7.5 条定义：数据递增或递减排序后，个数为奇数时取正中间一个；"
                     "为偶数时取中间两个数值的平均值。中间值抗离群点干扰，"
                     "适合汇总 5 个试件的强度/伸长率结果。")
    log("E3", "C12", "src 8.1.5 → 7.5（中间值定义所在条款）")

    # ---- E4 哑铃试件术语
    it = find(b, "B2951AB_C04")
    it["q"] = "GB/T 2951.11 规定，图 12 所示大哑铃试件拉力试验前标记的两条标记线间距为多少？"
    it["explain"] = ("第 9.1.3 条：大哑铃试件标记线间距 20mm，小哑铃试件（图 13 小冲模）为 10mm。"
                     "标距是伸长率的基准 L0，标错会让 ε=(Lf-L0)/L0 整体漂移。"
                     "注：2951.11 并无“1A 型”这一称谓，1A/1B 是 GB/T 1040 塑料拉伸标准的试样型号。")
    log("E4", "C04", "题干术语'1A型哑铃' → '图12大哑铃试件'（2951.11 无 1A 型号）")

    # ---- E5 夹头断裂作废溯源
    it = find(b, "B2951AB_C11")
    it["src"] = {"standard_no": "GB/T 2951.11-2008", "clause": "9.1.7"}
    it["explain"] = ("第 9.1.7 c) 条：在夹头处拉断的任何试件其结果均应作废。"
                     "夹持端存在应力集中，测得值不反映材料本体性能。"
                     "作废后计算抗张强度和断裂伸长率至少需保留 4 个有效数据，否则整组重做。")
    log("E5", "C11", "src 9.1.8 → 9.1.7（规定在拉力试验步骤 c 项）")

    n = fix_superscript(b)
    log("E6", "全库", f"上标字符修复 {n} 处")

    if not dry:
        json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def fix_others(dry):
    for name in ("gbt_3956.json", "gbt_2951_kb_mvp.json", "gbt_3048_8.json"):
        p = os.path.join(RULES, name)
        b = json.load(open(p, encoding="utf-8"))
        n = fix_superscript(b)
        if n:
            print(f"== {name}")
            log("E6", name, f"上标字符修复 {n} 处")
            if not dry:
                json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    dry = "--dry" in sys.argv
    if dry:
        print("*** DRY RUN，不写盘 ***")
    fix_2951ab(dry)
    fix_others(dry)
    print(f"\n共修正 {len(fixed_log)} 项。" + ("（未写盘）" if dry else "已写回 rules/"))


if __name__ == "__main__":
    main()
