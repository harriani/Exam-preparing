# -*- coding: utf-8 -*-
"""
题库内容纠错 v2 —— 依据 kb/raw/pages_2951.12.json OCR 正文核对热老化部分。

修正清单：
  E7 F06「烘箱温度±2℃」无源可溯   GB/T 2951.12 全文未规定通用温度偏差，8.1.3 只说
                                  "温度和时间按有关电缆产品标准的规定" → 属幻觉题，改造为
                                  有原文依据的「试件间距≥20mm」
  E8 C07 容积限值缺场景限定        0.5% 只针对失重试验试件(8.1.3.1)；线芯/成品电缆是 2%
                                  (8.1.3.4/8.1.4)；空气弹、氧弹是有效容积 1/10(8.2/8.3)
  E9 氧气纯度表述不严谨            8.3 原文为"纯度不低于 97% 的工业氧气"，非"纯氧"

新增题（原文明确参数，原题库漏考）：
  空气弹压力 (0.55±0.02)MPa / 弹内试件占有效容积≤1/10 / 卸压时间≥5min

用法: python kb/fix_content_errors2.py [--dry]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "rules", "gbt_2951_11_12.json")
STD12 = "GB/T 2951.12-2008"


def find(bank, qid):
    for t in ("choice", "judge", "fill", "calc"):
        for it in bank.get(t, []) or []:
            if it.get("id") == qid:
                return it
    return None


def main():
    dry = "--dry" in sys.argv
    if dry:
        print("*** DRY RUN，不写盘 ***")
    b = json.load(open(P, encoding="utf-8"))
    print("== gbt_2951_11_12.json（热老化部分）")

    # ---- E7 幻觉题改造
    it = find(b, "B2951AB_F06")
    it["q"] = "空气烘箱老化时，试件垂直悬挂于烘箱中部，每个试件与相邻试件的间距至少应为 ___ mm。"
    it["answers"] = ["20"]
    it["syn"] = [["20mm", "二十"]]
    it["explain"] = ("GB/T 2951.12 第 8.1.3 条：试件间距至少 20mm。间距不足会互相遮挡气流，"
                     "造成局部氧浓度和温度不均，老化程度失真。"
                     "注：本标准并未规定通用的烘箱温度偏差，老化温度和时间一律"
                     "「按有关电缆产品标准的规定」，不要背一个通用的 ±X℃。")
    it["src"] = {"standard_no": STD12, "clause": "8.1.3"}
    print("  [E7] F06: 幻觉题「烘箱温度±2℃」→ 改造为有原文依据的「试件间距≥20mm」")

    # ---- E8 容积限值加场景
    it = find(b, "B2951AB_C07")
    it["q"] = "空气烘箱老化中，用于失重试验的试件，其所占烘箱容积应不大于？"
    it["options"] = ["0.5%", "2%", "10%", "20%"]
    it["answer"] = 0
    it["explain"] = ("第 8.1.3 条：失重试验试件占烘箱容积 ≤0.5%。三档限值别混："
                     "① 失重试验试件 ≤0.5%（8.1.3）；② 绝缘线芯卷绕试件、成品电缆样段 ≤2%"
                     "（8.1.3.4 / 8.1.4）；③ 空气弹、氧弹内试件 ≤有效容积的 1/10（8.2 / 8.3）。"
                     "失重试验限得最严，因为它直接称重，样品多会显著改变箱内挥发物分压。")
    it["src"] = {"standard_no": STD12, "clause": "8.1.3"}
    print("  [E8] C07: 题干补场景限定（0.5% 仅适用失重试验试件），解析列全三档限值")

    # ---- E9 氧气纯度
    it = find(b, "B2951AB_F07")
    it["explain"] = ("第 8.3 条：氧弹应充满纯度不低于 97% 的工业氧气，压力 (2.1±0.07)MPa。"
                     "严格说是「工业氧气」而非实验室纯氧。区别于空气弹（无油无潮气的空气，"
                     "(0.55±0.02)MPa）。")
    it = find(b, "B2951AB_F08")
    it["explain"] = ("第 8.2 条：空气弹充无油无潮气的空气，压力 (0.55±0.02)MPa。"
                     "与氧弹的差别在介质和压力，老化温度同样由产品标准规定，"
                     "不存在「空气弹温度一定更低」的通用结论。")
    it = find(b, "B2951AB_J04")
    it["q"] = "氧弹老化应充入纯度不低于 97% 的工业氧气，压力为 (2.1±0.07) MPa。"
    it["explain"] = ("第 8.3 条原文。注意是纯度≥97% 的工业氧气，不是实验室级纯氧；"
                     "高氧分压把材料的氧化诱导过程按倍数压缩，才能在几天内看出几十年的劣化趋势。")
    print("  [E9] F07/F08/J04: 氧气纯度与空气弹参数按原文校准")

    # ---- 新增题
    new_choice = [
        dict(id="B2951AB_C16",
             q="空气弹老化试验中，充入的无油无潮气空气压力应为多少？",
             options=["(0.55±0.02) MPa", "(2.1±0.07) MPa", "(1.0±0.05) MPa", "(0.20±0.01) MPa"],
             answer=0,
             explain=("第 8.2 条：(0.55±0.02)MPa。空气弹靠压缩空气中约 21% 的氧加速氧化，"
                      "氧分压远低于氧弹，因此压力档也低一个量级。"
                      "记法：空气弹 0.55、氧弹 2.1，差约 4 倍。"),
             src={"standard_no": STD12, "clause": "8.2"}),
        dict(id="B2951AB_C17",
             q="空气弹和氧弹老化时，试件所占弹体有效容积应不大于？",
             options=["十分之一", "二分之一", "五分之一", "百分之零点五"],
             answer=0,
             explain=("第 8.2、8.3 条：均为有效容积的 1/10，且试件之间不得接触。"
                      "装载过多会使气体总量不足以维持恒定氧分压，老化速率随时间衰减。"),
             src={"standard_no": STD12, "clause": "8.2"}),
        dict(id="B2951AB_C18",
             q="空气弹/氧弹老化结束后卸压，正确做法是？",
             options=["立即快速放空以终止老化", "在不少于 5 min 内逐渐降至大气压",
                      "自然冷却 24 h 后再放空", "先充氮气置换再放空"],
             answer=1,
             explain=("第 8.2、8.3 条：老化结束后立即在不少于 5min 内逐渐降至大气压。"
                      "快速卸压会让溶解在材料中的气体骤然析出，在试件内部形成气孔，"
                      "拉伸时从气孔处提前断裂，测得强度和伸长率虚低。"),
             src={"standard_no": STD12, "clause": "8.3"}),
    ]
    exist = {x["id"] for x in b.get("choice", [])}
    added = [c for c in new_choice if c["id"] not in exist]
    b.setdefault("choice", []).extend(added)
    print(f"  [新增] choice {len(added)} 题（空气弹压力 / 有效容积 1/10 / 卸压≥5min）")

    if not dry:
        json.dump(b, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n完成。" + ("（未写盘）" if dry else "已写回 rules/"))


if __name__ == "__main__":
    main()
