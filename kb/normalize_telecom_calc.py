# -*- coding: utf-8 -*-
"""
normalize_telecom_calc.py — 《电信电缆检验员培训试题》题库细化（"规范子空 / 再解析切分"）。

在 convert_telecom_exam.py 产出的基础 JSON 之上做精修：
  1. 修 OCR 误判的题型：
       - TJ_K001 实为"公式选择题"（含 A、B 选项）→ 归入 choice
       - TJ_K002 是 3 道选择题被 OCR 粘在一起（绝缘电阻目的 / 135 串联谐振条件 / 136 tgδ 仪器）
         → 拆成 3 道 choice
       - TJ_K003~K007 是"推导/画图说明"题，无数值答案 → 归入 essay（开放题·答案待核）
  2. 给真正的数值计算题（TJ_K008~K015 中可识别结果的）填写规范 subs 子空。
       target 一律从题干"解:"过程里转录（不另编造），网上题库仍标"答案待核"、不自动判分。
  3. 全部 id 按题型重新单调编号（TJ_C / TJ_J / TJ_F / TJ_K / TJ_E），保证全局唯一。

只动 public/data/telecom_exam_questions.json，不改 convert 脚本（convert 仍是 OCR→raw 的来源）。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "public", "data", "telecom_exam_questions.json")

SRC_TAG = "网上题库·电信电缆检验员培训试题"


def load():
    return json.load(open(SRC, encoding="utf-8"))


def save(d):
    tmp = SRC + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, SRC)


# ---- 计算题子空（从题干解题过程转录，target 为字符串，tol 容差仅作占位，网上题库不判分）----
# 每项: [label(含单位), target, tol, pts]
CALC_SUBS = {
    "TJ_K008": [["R20 (Ω)", "0.02171", 0.0005, 10]],
    "TJ_K009": [],  # 文字推导比较，无单一数值结果
    "TJ_K010": [],  # 测量数据表，需自行计算抗张强度/伸长率，无现成结果
    "TJ_K011": [["第二盘绝缘电阻 R2 (MΩ)", "250", 1, 10]],
    "TJ_K012": [["Rx (Ω)", "4.97e-3", 2e-5, 5], ["最大相对误差 (%)", "1.1", 0.1, 5]],
    "TJ_K013": [["每米电容 C (pF/m)", "303.2", 2, 10]],
    "TJ_K014": [["95mm² 电缆长度 (m)", "955", 2, 5], ["120mm² 电缆长度 (m)", "1206", 2, 5]],
    "TJ_K015": [],  # 解题过程被 OCR 截断，无最终结果
}

# 需要重新归类的计算题
# choice 拆分项（K002 的三道）
K002_CHOICES = [
    {"q": "在测量电线绝缘电阻时，将试样放入水中，露出的绝缘表面应保持干燥和洁净，其目的是（）。",
     "options": ["防止表面产生泄漏电流", "防止表面闪络", "防止表面击穿"]},
    {"q": "目前绝大多数工厂，在进行局部放电测量时，所用的电源是串联谐振系统，串联谐振的条件是（）。",
     "options": ["感抗=容抗", "电抗=回路的纯电阻", "容抗=回路的纯电路"]},
    {"q": "测介质损耗角正切值 tgδ，常用仪器是（）。",
     "options": ["惠司登电桥", "开尔文电桥", "西林电桥"]},
]
K001_CHOICE = {"q": "每公里长度的绝缘电阻计算公式（ ）。",
               "options": ["R1=Rx/L", "R1=RxL"]}


def main():
    d = load()
    meta = d.get("meta", {})
    choice, judge, fill, calc, essay = [], [], [], [], []

    # 把原有各类先收集，期间对 calc 做重归类
    for it in d.get("choice", []):
        choice.append(it)
    for it in d.get("judge", []):
        judge.append(it)
    for it in d.get("fill", []):
        fill.append(it)
    for it in d.get("essay", []):
        essay.append(it)

    for it in d.get("calc", []):
        cid = it.get("id")
        if cid == "TJ_K001":
            choice.append({
                "id": "_tmp", "q": K001_CHOICE["q"],
                "options": K001_CHOICE["options"], "answer": None,
                "points": 2, "src": SRC_TAG,
            })
        elif cid == "TJ_K002":
            for c in K002_CHOICES:
                choice.append({
                    "id": "_tmp", "q": c["q"],
                    "options": c["options"], "answer": None,
                    "points": 2, "src": SRC_TAG,
                })
        elif cid in ("TJ_K003", "TJ_K004", "TJ_K005", "TJ_K006", "TJ_K007"):
            essay.append({
                "id": "_tmp", "q": it.get("stem", ""), "points": 5, "src": SRC_TAG,
            })
        else:
            # 真数值计算题：填 subs
            subs = CALC_SUBS.get(cid, [])
            calc.append({
                "id": "_tmp", "title": it.get("title", ""),
                "stem": it.get("stem", ""), "subs": subs,
                "explain": "", "points": 10, "src": SRC_TAG,
            })

    # 重新单调编号，保证全局唯一 & 题型前缀一致
    def re_id(prefix, arr):
        for i, it in enumerate(arr, start=1):
            it["id"] = f"{prefix}{i:03d}"

    re_id("TJ_C", choice)
    re_id("TJ_J", judge)
    re_id("TJ_F", fill)
    re_id("TJ_K", calc)
    re_id("TJ_E", essay)

    out = {
        "meta": meta,
        "choice": choice, "judge": judge, "fill": fill, "calc": calc, "essay": essay,
    }
    save(out)

    total = len(choice) + len(judge) + len(fill) + len(calc) + len(essay)
    print(f"细化完成: choice={len(choice)} judge={len(judge)} fill={len(fill)} "
          f"calc={len(calc)} essay={len(essay)} 总计={total}")
    print(f"计算题带 subs 数: {sum(1 for c in calc if c.get('subs'))}")


if __name__ == "__main__":
    main()
