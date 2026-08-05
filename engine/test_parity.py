# -*- coding: utf-8 -*-
"""
判分一致性测试：Python(generate.py) vs JS(grade.js)
======================================================
为什么必须有这个测试：
  试卷在浏览器里用 JS 判分（离线自测），在服务端/批改时用 Python 判分。
  两边逻辑只要差一个字符（比如 JS 的 parseFloat("4h")=4 而 Python float("4h") 报错），
  同一份答卷就会出两个分数。这是这套系统最隐蔽也最致命的 bug。

用法：
  python test_parity.py [../rules/gbt_2951_kb_mvp.json]
退出码 0 = 两边完全一致。
"""
import json, os, sys, subprocess, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate import grade_all, compute_score

NODE = r"C:/Users/ZT-052382/.workbuddy/binaries/node/versions/22.22.2/node.exe"


def build_cases(bank):
    """构造覆盖各种边界的作答集"""
    cases = []
    cid = [it["id"] for it in bank.get("choice", [])]
    jid = [it["id"] for it in bank.get("judge", [])]
    fid = [it["id"] for it in bank.get("fill", [])]
    kid = [it["id"] for it in bank.get("calc", [])]

    def blank():
        return {"choice": {}, "judge": {}, "fill": {}, "calc": {}}

    # 1. 满分卷
    a = blank()
    for it in bank.get("choice", []): a["choice"][it["id"]] = it["answer"]
    for it in bank.get("judge", []): a["judge"][it["id"]] = it["answer"]
    for it in bank.get("fill", []): a["fill"][it["id"]] = list(it["answers"])
    for it in bank.get("calc", []): a["calc"][it["id"]] = [s[1] for s in it["subs"]]
    cases.append(("满分卷", a))

    # 2. 全错卷
    a = blank()
    for it in bank.get("choice", []): a["choice"][it["id"]] = (int(it["answer"]) + 1) % 4
    for it in bank.get("judge", []): a["judge"][it["id"]] = not it["answer"]
    for it in bank.get("fill", []): a["fill"][it["id"]] = ["__X__"] * len(it["answers"])
    for it in bank.get("calc", []): a["calc"][it["id"]] = ["__X__"] * len(it["subs"])
    cases.append(("全错卷", a))

    # 3. 全空卷
    a = blank()
    for i in cid: a["choice"][i] = ""
    for i in jid: a["judge"][i] = ""
    for it in bank.get("fill", []): a["fill"][it["id"]] = [""] * len(it["answers"])
    for it in bank.get("calc", []): a["calc"][it["id"]] = [""] * len(it["subs"])
    cases.append(("全空卷", a))

    # 4. 近义词/空格/全角：填空全用 syn 或加噪声
    a = blank()
    for it in bank.get("choice", []): a["choice"][it["id"]] = it["answer"]
    for it in bank.get("judge", []): a["judge"][it["id"]] = "对" if it["answer"] else "错"
    for it in bank.get("fill", []):
        vals = []
        for i, ans in enumerate(it["answers"]):
            syn = it.get("syn", [])
            if i < len(syn) and syn[i]:
                vals.append(syn[i][0])           # 用近义答案
            else:
                vals.append(" " + str(ans) + " ")  # 加前后空格
        a["fill"][it["id"]] = vals
    for it in bank.get("calc", []):
        a["calc"][it["id"]] = ["\u3000" + str(s[1]) for s in it["subs"]]  # 全角空格前缀
    cases.append(("近义词+空格噪声卷", a))

    # 5. 判断题各种写法
    a = blank()
    forms_t = ["对", "√", "正确", "true", "T", "1", "Y"]
    forms_f = ["错", "×", "错误", "false", "F", "0", "N"]
    for k, it in enumerate(bank.get("judge", [])):
        pool = forms_t if it["answer"] else forms_f
        a["judge"][it["id"]] = pool[k % len(pool)]
    cases.append(("判断题多写法卷", a))

    # 6. 判断题乱填（应全 0）
    a = blank()
    for k, i in enumerate(jid):
        a["judge"][i] = ["也许", "?", "不确定", "半对", ""][k % 5]
    cases.append(("判断题乱填卷", a))

    # 7. 数值毒性输入：Python float 和 JS parseFloat 的经典分歧点
    a = blank()
    poison = ["1_0", "inf", "nan", "4h", "0.6abc", "+4", "4.0", " 4 ", "1e0", "０.６"]
    for it in bank.get("calc", []):
        a["calc"][it["id"]] = [poison[i % len(poison)] for i in range(len(it["subs"]))]
    for it in bank.get("fill", []):
        a["fill"][it["id"]] = [poison[i % len(poison)] for i in range(len(it["answers"]))]
    cases.append(("数值毒性输入卷", a))

    # 8. 计算题精度边界：目标值 ± 容差
    a = blank()
    for it in bank.get("calc", []):
        vals = []
        for s in it["subs"]:
            label, target, tol = s[0], s[1], s[2]
            if label == "合格性判定":
                vals.append(target)
            else:
                try:
                    vals.append(str(float(target) + float(tol)))   # 刚好卡在容差边界
                except Exception:
                    vals.append(target)
        a["calc"][it["id"]] = vals
    cases.append(("计算题容差边界卷", a))

    # 9~13. 随机卷
    rnd = random.Random(20260804)
    for n in range(5):
        a = blank()
        for it in bank.get("choice", []): a["choice"][it["id"]] = rnd.randint(0, 3)
        for it in bank.get("judge", []): a["judge"][it["id"]] = rnd.choice([True, False, "对", "错", "x", ""])
        for it in bank.get("fill", []):
            a["fill"][it["id"]] = [rnd.choice([ans, "__X__", "", str(ans) + " "])
                                   for ans in it["answers"]]
        for it in bank.get("calc", []):
            a["calc"][it["id"]] = [rnd.choice([s[1], "0", "__X__", ""]) for s in it["subs"]]
        cases.append((f"随机卷{n+1}", a))

    return cases


def main():
    rule = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "rules", "gbt_2951_kb_mvp.json")
    bank = json.load(open(rule, encoding="utf-8"))
    cases = build_cases(bank)

    py_results = [grade_all(bank, a) for _, a in cases]

    tmp_in = os.path.join(HERE, "_parity_cases.json")
    tmp_out = os.path.join(HERE, "_parity_js.json")
    json.dump({"bank": bank, "cases": [{"name": n, "answers": a} for n, a in cases]},
              open(tmp_in, "w", encoding="utf-8"), ensure_ascii=False)

    r = subprocess.run([NODE, os.path.join(HERE, "_parity_runner.js"), tmp_in, tmp_out],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("[FAIL] node 执行失败:\n" + (r.stderr or ""))
        sys.exit(1)

    js_results = json.load(open(tmp_out, encoding="utf-8"))

    total = compute_score(bank)["total"]
    print(f"试卷: {os.path.basename(rule)}  总分 {total}")
    print("-" * 72)
    print(f"{'用例':<20}{'Python':>10}{'JS':>10}{'明细一致':>12}{'结果':>8}")
    print("-" * 72)

    ok = True
    for (name, _), pr, jr in zip(cases, py_results, js_results):
        same_total = pr["got"]["total"] == jr["got"]["total"]
        same_detail = pr["detail"] == jr["detail"]
        good = same_total and same_detail
        ok = ok and good
        print(f"{name:<20}{pr['got']['total']:>10}{jr['got']['total']:>10}"
              f"{('是' if same_detail else '否'):>12}{('PASS' if good else 'FAIL'):>8}")
        if not good:
            for t in ("choice", "judge", "fill", "calc"):
                for qid in pr["detail"][t]:
                    if pr["detail"][t][qid] != jr["detail"].get(t, {}).get(qid):
                        print(f"    ✗ {t}/{qid}: py={pr['detail'][t][qid]} js={jr['detail'].get(t,{}).get(qid)}")

    print("-" * 72)
    # 关键断言
    assert py_results[0]["got"]["total"] == total, "满分卷未得满分"
    assert py_results[1]["got"]["total"] == 0, "全错卷不为 0"
    assert py_results[2]["got"]["total"] == 0, "全空卷不为 0"
    assert py_results[3]["got"]["total"] == total, "近义词卷未得满分（syn 规则失效）"
    jt = py_results[4]["got"]["judge"]
    assert jt == sum(it.get("points", 1) for it in bank.get("judge", [])), "判断题多写法未全对"
    assert py_results[5]["got"]["judge"] == 0, "判断题乱填不为 0"
    print("关键断言：满分/全错/全空/近义词/判断多写法/乱填 —— 全部符合预期")
    print(f"\n{'✅ PARITY PASS：Python 与 JS 判分完全一致' if ok else '❌ PARITY FAIL：两边判分不一致'}")

    for f in (tmp_in, tmp_out):
        try: os.remove(f)
        except OSError: pass
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
