# -*- coding: utf-8 -*-
"""
learning-system-v2 · 数据驱动出题引擎（MVP）
================================================
设计原则（来自"出题专家"技能 standards-exam-generator 的题型/分值/判分规范）：
  1. 规则数据化 —— 一份标准 = 一个 rules/<标准>.json 数据文件，引擎框架不动。
     彻底替代旧项目 25+ 个 _gen_gbXX.py 手写脚本（补丁叠补丁）。
  2. 单一真源 —— 题型/分值/判分逻辑固化在本引擎；换标准只改数据，不改代码。
  3. 答案零幻觉 —— 所有题目来自 rules 数据（由专家技能 schema + 用户真实资料抽取），
     引擎不做任何"编造"，只做校验、判分、渲染。
  4. 满分自检 —— 生成后必须 grade(满分作答) == 总分，否则报错。

用法：
  python generate.py                      # 处理 rules/ 下全部 *.json
  python generate.py ../rules/gbt_3956.json   # 处理单个
输出：
  ../out/<name>_bank.json    结构化题库（含计算得分）
  ../out/<name>_preview.html 离线预览（题 + 答案/解析，无 CDN 依赖）
"""
import json, os, sys, glob, re

# ---------- 规范化（来自专家技能第 6 节 normalize）----------
def normalize(s):
    """归一化规则（判分单一真源，engine/grade.js 必须逐条镜像）"""
    if s is None:
        return ""
    s = str(s)
    for ch in (" ", " ", "　", "	"):
        s = s.replace(ch, "")
    s = s.replace("％", "%").replace("×", "x").replace("÷", "/")
    s = s.replace("²", "2").replace("³", "3")
    s = s.replace("（", "(").replace("）", ")").replace("：", ":").replace("，", ",")
    s = s.replace("。", ".").replace("、", ",").replace("～", "~").replace("—", "-")
    return s.lower().strip()

NUM_RE = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')

def to_num(x):
    """严格数值解析：只认纯数字串。float() 会把 '1_0'/'inf'/'nan' 也吃进去，判分里不能容忍。"""
    s = str(x).strip().replace(" ", "").replace("\xa0", "").replace("\u3000", "")
    return float(s) if NUM_RE.match(s) else None

def close_enough(a, b, tol=0):
    na, nb = to_num(a), to_num(b)
    if na is None or nb is None:
        return normalize(a) == normalize(b)
    t = to_num(tol) or 0.0
    return abs(na - nb) <= t + 1e-9

# ---------- 单题判分 ----------
def grade_choice(it, sub):
    pts = it.get("points", 2)
    if sub is None or sub == "":
        return 0
    try:
        return pts if int(sub) == int(it["answer"]) else 0
    except (TypeError, ValueError):
        return 0

def grade_judge(it, sub):
    """判断题：答案 true/false。用户输入接受 True/False/对/错/√/× """
    pts = it.get("points", 1)
    truth = bool(it["answer"])
    if isinstance(sub, bool):
        user = sub
    else:
        s = normalize(sub)
        if s in ("true", "t", "对", "正确", "√", "v", "y", "yes", "1"):
            user = True
        elif s in ("false", "f", "错", "错误", "x", "×", "n", "no", "0"):
            user = False
        else:
            return 0
    return pts if user == truth else 0

def grade_fill(it, subs):
    pts = it.get("points", 2)
    ans = it["answers"]
    syn = it.get("syn", [])
    if len(subs) != len(ans):
        return 0
    for i, user in enumerate(subs):
        ok = normalize(user) == normalize(ans[i])
        if not ok and i < len(syn):
            ok = normalize(user) in [normalize(x) for x in syn[i]]
        if not ok:
            return 0
    return pts

def grade_match(it, user_pairs):
    """user_pairs: list of [left, right] 用户连线结果"""
    pts = it.get("points", 2)
    truth = {normalize(it["left"]): normalize(it["right"])}
    if len(user_pairs) != len(truth):
        return 0
    for l, r in user_pairs:
        if normalize(l) not in truth or truth[normalize(l)] != normalize(r):
            return 0
    return pts

def grade_calc(it, subs):
    total = 0
    for i, sub in enumerate(subs):
        label, target, tol, pts = it["subs"][i][:4]
        if label == "合格性判定":
            # 判定类：答案与标准结论完全一致即给分（合格/不符合/不合格/满足等均支持）
            total += pts if normalize(sub) == normalize(target) else 0
        else:
            total += pts if close_enough(sub, target, tol) else 0
    return total

# ---------- 校验 + 计分 ----------
def validate(bank):
    errs = []
    for i, it in enumerate(bank.get("choice", [])):
        for k in ("id", "q", "options", "answer"):
            if k not in it: errs.append(f"choice[{i}] 缺 {k}")
        if not isinstance(it.get("options"), list) or len(it["options"]) != 4:
            errs.append(f"choice[{i}] options 必须正好 4 项")
    for i, it in enumerate(bank.get("judge", [])):
        for k in ("id", "q", "answer"):
            if k not in it: errs.append(f"judge[{i}] 缺 {k}")
        if not isinstance(it.get("answer"), bool):
            errs.append(f"judge[{i}] answer 必须是 true/false 布尔值")
    # 溯源校验：每题应有 src（标准号+条款），杜绝幻觉
    miss_src = 0
    for t in ("choice", "judge", "fill", "calc"):
        for it in bank.get(t, []):
            if not it.get("src"):
                miss_src += 1
    if miss_src:
        errs.append(f"[warn] 有 {miss_src} 题无 src 溯源标注")
    for i, it in enumerate(bank.get("fill", [])):
        for k in ("id", "q", "answers"):
            if k not in it: errs.append(f"fill[{i}] 缺 {k}")
    for i, it in enumerate(bank.get("match", [])):
        for k in ("left", "right"):
            if k not in it: errs.append(f"match[{i}] 缺 {k}")
    for i, it in enumerate(bank.get("calc", [])):
        for k in ("id", "title", "stem", "subs"):
            if k not in it: errs.append(f"calc[{i}] 缺 {k}")
    return errs

def compute_score(bank):
    sc = bank.get("meta", {}).get("scoring", {})
    c = sum(it.get("points", sc.get("choice", 2)) for it in bank.get("choice", []))
    j = sum(it.get("points", sc.get("judge", 1)) for it in bank.get("judge", []))
    f = sum(it.get("points", sc.get("fill", 2)) for it in bank.get("fill", []))
    m = sum(it.get("points", sc.get("match_pair", 2)) for it in bank.get("match", []))
    cal = sum(sum(sub[3] for sub in it["subs"]) for it in bank.get("calc", []))
    return {"choice": c, "judge": j, "fill": f, "match": m, "calc": cal,
            "total": c + j + f + m + cal}

def self_check(bank):
    """满分作答应等于总分"""
    total = compute_score(bank)["total"]
    got = 0
    for it in bank.get("choice", []):
        got += grade_choice(it, it["answer"])
    for it in bank.get("judge", []):
        got += grade_judge(it, it["answer"])
    for it in bank.get("fill", []):
        got += grade_fill(it, list(it["answers"]))
    for it in bank.get("match", []):
        got += grade_match(it, [[it["left"], it["right"]]])
    for it in bank.get("calc", []):
        got += grade_calc(it, [s[1] for s in it["subs"]])
    return total, got, (total == got)

def grade_all(bank, answers):
    """整卷判分（与 engine/grade.js gradeAll 逐条镜像）
    answers = {"choice":{id:idx}, "judge":{id:bool|str}, "fill":{id:[..]}, "calc":{id:[..]}}
    """
    detail = {"choice": {}, "judge": {}, "fill": {}, "calc": {}}
    got = {"choice": 0, "judge": 0, "fill": 0, "calc": 0}
    for it in bank.get("choice", []):
        s = grade_choice(it, answers.get("choice", {}).get(it["id"], ""))
        detail["choice"][it["id"]] = s; got["choice"] += s
    for it in bank.get("judge", []):
        s = grade_judge(it, answers.get("judge", {}).get(it["id"], ""))
        detail["judge"][it["id"]] = s; got["judge"] += s
    for it in bank.get("fill", []):
        s = grade_fill(it, answers.get("fill", {}).get(it["id"], []))
        detail["fill"][it["id"]] = s; got["fill"] += s
    for it in bank.get("calc", []):
        s = grade_calc(it, answers.get("calc", {}).get(it["id"], []))
        detail["calc"][it["id"]] = s; got["calc"] += s
    got["total"] = got["choice"] + got["judge"] + got["fill"] + got["calc"]
    return {"got": got, "detail": detail}

def zero_check(bank):
    """反向自检：故意全答错，应得 0 分。防止判分逻辑写反。"""
    got = 0
    for it in bank.get("choice", []):
        wrong = (int(it["answer"]) + 1) % 4
        got += grade_choice(it, wrong)
    for it in bank.get("judge", []):
        got += grade_judge(it, not it["answer"])
    for it in bank.get("fill", []):
        got += grade_fill(it, ["__WRONG__"] * len(it["answers"]))
    return got

# ---------- 渲染离线 HTML ----------
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_html(bank, score, check):
    meta = bank.get("meta", {})
    std = " / ".join(meta.get("standard", ["未命名标准"]))
    parts = []
    parts.append(f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>出题预览 · {esc(std)}</title>
<style>
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;max-width:900px;margin:24px auto;padding:0 18px;color:#1f2329;line-height:1.6}}
h1{{font-size:22px;border-left:5px solid #2f6fed;padding-left:10px}}
.summary{{background:#f3f6ff;border:1px solid #d6e2ff;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px}}
.badge{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;margin-right:6px}}
.ok{{background:#e6f7ec;color:#16894a}}.bad{{background:#fdecec;color:#c0392b}}
h2{{font-size:17px;margin-top:26px;color:#2f6fed}}
.q{{border:1px solid #e6e8eb;border-radius:8px;padding:12px 14px;margin:10px 0;background:#fff}}
.q .t{{font-weight:600;color:#334}}
.opt{{margin:3px 0 3px 18px}}
.ans{{margin-top:8px;font-size:13px;color:#16894a;background:#f3fbf6;border-radius:6px;padding:6px 10px}}
.exp{{font-size:13px;color:#666;margin-top:4px}}
.match{{font-size:14px;margin:3px 0}}
.toggle{{cursor:pointer;color:#2f6fed;font-size:13px;user-select:none}}
</style></head><body>
<h1>出题预览 · {esc(std)}</h1>
<div class="summary">
  <span class="badge ok">总分 {score['total']}</span>
  <span class="badge {'ok' if check[2] else 'bad'}">满分自检 {'PASS' if check[2] else 'FAIL'}（满分作答={check[1]}）</span>
  <br>题型得分：选择 {score['choice']} ｜ 判断 {score['judge']} ｜ 填空 {score['fill']} ｜ 连线 {score['match']} ｜ 计算 {score['calc']}
  <br>题量：选择 {len(bank.get('choice',[]))} ｜ 判断 {len(bank.get('judge',[]))} ｜ 填空 {len(bank.get('fill',[]))} ｜ 连线 {len(bank.get('match',[]))} ｜ 计算 {len(bank.get('calc',[]))}
  <br>设计理念：{esc(meta.get('design',''))}
</div>""")

    if bank.get("choice"):
        parts.append("<h2>一、选择题（4 选 1）</h2>")
        for n, it in enumerate(bank["choice"], 1):
            opts = "".join(f'<div class="opt">{chr(65+i)}. {esc(o)}</div>' for i, o in enumerate(it["options"]))
            parts.append(f'<div class="q"><div class="t">C{n}. {esc(it["q"])}</div>{opts}'
                         f'<div class="ans">答案：{chr(65+int(it["answer"]))}</div>'
                         f'<div class="exp">解析：{esc(it.get("explain",""))}</div></div>')
    if bank.get("judge"):
        parts.append("<h2>二、判断题（对 / 错）</h2>")
        for n, it in enumerate(bank["judge"], 1):
            parts.append(f'<div class="q"><div class="t">J{n}. {esc(it["q"])}</div>'
                         f'<div class="ans">答案：{"对 √" if it["answer"] else "错 ×"}</div>'
                         f'<div class="exp">解析：{esc(it.get("explain",""))}｜来源：{esc(it.get("src",""))}</div></div>')
    if bank.get("fill"):
        parts.append("<h2>三、填空题</h2>")
        for n, it in enumerate(bank["fill"], 1):
            parts.append(f'<div class="q"><div class="t">F{n}. {esc(it["q"])}</div>'
                         f'<div class="ans">答案：{" / ".join(esc(a) for a in it["answers"])}'
                         f'{("｜近义："+ " / ".join(esc(x) for x in it["syn"][0])) if it.get("syn") else ""}</div>'
                         f'<div class="exp">解析：{esc(it.get("explain",""))}</div></div>')
    if bank.get("match"):
        parts.append("<h2>四、连线题（方法 → 要素）</h2>")
        for n, it in enumerate(bank["match"], 1):
            parts.append(f'<div class="q"><div class="match">{esc(it["left"])} —— <b>{esc(it["right"])}</b></div>'
                         f'<div class="exp">解析：{esc(it.get("explain",""))}</div></div>')
    if bank.get("calc"):
        parts.append("<h2>五、计算题（阶梯小问，数值+容差判分）</h2>")
        for n, it in enumerate(bank["calc"], 1):
            subs = "".join(f'<div class="match">· {esc(s[0])} → 目标 {esc(s[1])}（容差 {esc(s[2])}，{esc(s[3])}分）</div>' for s in it["subs"])
            parts.append(f'<div class="q"><div class="t">CALC{n}. {esc(it["title"])}</div>'
                         f'<div class="exp">{esc(it["stem"])}</div>{subs}'
                         f'<div class="exp">解析：{esc(it.get("explain",""))}</div></div>')
    parts.append("</body></html>")
    return "\n".join(parts)

# ---------- 主流程 ----------
def process(path):
    bank = json.load(open(path, encoding="utf-8"))
    name = os.path.splitext(os.path.basename(path))[0]
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out_dir, exist_ok=True)

    errs = validate(bank)
    score = compute_score(bank)
    check = self_check(bank)
    zero = zero_check(bank)

    # 写结构化题库（附带计算得分）
    bank_out = dict(bank)
    bank_out["_computed_score"] = score
    bank_out["_self_check"] = {"total": check[0], "perfect_got": check[1], "pass": check[2],
                               "all_wrong_got": zero, "zero_pass": zero == 0}
    json.dump(bank_out, open(os.path.join(out_dir, f"{name}_bank.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 写预览
    html = render_html(bank, score, check)
    html_path = os.path.join(out_dir, f"{name}_preview.html")
    open(html_path, "w", encoding="utf-8").write(html)

    hard_errs = [e for e in errs if not e.startswith("[warn]")]
    print(f"[OK] {name}")
    print(f"     题型得分: 选择{score['choice']} 判断{score['judge']} 填空{score['fill']} "
          f"连线{score['match']} 计算{score['calc']} = 总分 {score['total']}")
    print(f"     满分自检: {'PASS' if check[2] else 'FAIL'} (满分作答={check[1]}/{check[0]})")
    print(f"     零分自检: {'PASS' if zero == 0 else 'FAIL'} (全答错={zero}, 应为0)")
    for e in errs:
        print("     " + e)
    print(f"     -> {html_path}")
    return check[2] and zero == 0 and not hard_errs

def main():
    if len(sys.argv) > 1:
        files = [sys.argv[1]]
    else:
        files = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rules", "*.json")))
    if not files:
        print("没有找到 rules/*.json"); sys.exit(1)
    ok = True
    for f in files:
        ok = process(f) and ok
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
