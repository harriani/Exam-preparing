# -*- coding: utf-8 -*-
"""
国缆杯学习系统 v2 · 系统级端到端回归测试
=========================================
一条命令，验证整条链路是否还站得住：

    PDF/OCR → kb/raw → 摘要 → LLM判定(KU) → master_judged.json
            → 题库(rules/*.json) → 判分引擎(generate.py / grade.js) → 前端SPA(public/)
            → 后端服务(server.py: /api/build 出卷 + /api/grade 判卷)

设计原则：**测的是"数据资产"而不是"函数"**。
这套系统的 bug 90% 不在代码里，在数据里 —— 少一个 src、priority 写错枚举、
JS 和 Python 判分差一个字符、public/data 忘了同步。所以每个用例都直接
拿真实资产开刀，不用 mock。

用法：
    python tests/system_test.py                # 全量
    python tests/system_test.py --no-node      # 跳过需要 Node 的用例
    python tests/system_test.py --strict-trace # 溯源缺失从 WARN 升级为 FAIL

退出码：0 = 无 FAIL；1 = 有 FAIL
产物：tests/report.json、tests/report.html
"""
import os, sys, json, glob, re, subprocess, time, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE = os.path.join(ROOT, "engine")
KB = os.path.join(ROOT, "kb")
sys.path.insert(0, ENGINE)
sys.path.insert(0, KB)

NODE = r"C:/Users/ZT-052382/.workbuddy/binaries/node/versions/22.22.2/node.exe"
PY = sys.executable

STD_RE = re.compile(r"^(GB/T|GB|JB/T|JB|IEC)\s?\d+(\.\d+)*(-\d{4})?$")

# ---------------------------------------------------------------- 结果收集
RESULTS = []
_t0 = time.time()


def rec(suite, case, status, msg=""):
    RESULTS.append({"suite": suite, "case": case, "status": status, "msg": msg})
    return status == "PASS"


def ck(suite, case, ok, msg_fail="", msg_pass="", warn_only=False):
    if ok:
        return rec(suite, case, "PASS", msg_pass)
    return rec(suite, case, "WARN" if warn_only else "FAIL", msg_fail)


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ================================================================ T0 环境
def t0_env():
    S = "T0 环境与目录"
    for name, path in [("engine/generate.py", os.path.join(ENGINE, "generate.py")),
                       ("engine/grade.js", os.path.join(ENGINE, "grade.js")),
                       ("kb/ku_schema.py", os.path.join(KB, "ku_schema.py")),
                       ("kb/master_judged.json", os.path.join(KB, "master_judged.json")),
                       ("public/index.html", os.path.join(ROOT, "public", "index.html")),
                       ("public/app.js", os.path.join(ROOT, "public", "app.js"))]:
        ck(S, f"存在 {name}", os.path.exists(path), "文件缺失")

    try:
        import generate, ku_schema  # noqa
        ck(S, "引擎模块可导入", True, msg_pass="generate + ku_schema")
    except Exception as e:
        ck(S, "引擎模块可导入", False, f"{type(e).__name__}: {e}")

    banks = sorted(glob.glob(os.path.join(ROOT, "rules", "*.json")))
    ck(S, "rules/ 存在题库真源", len(banks) > 0, "rules/ 下无题库",
       f"{len(banks)} 个题库")
    # out/ 只应有产出物，不应混入题库真源
    stray = [os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "out", "*.json"))
             if not p.endswith("_bank.json")]
    ck(S, "out/ 无混入的题库真源", not stray,
       f"out/ 混入真源: {stray}（题库真源只放 rules/）")
    return banks


# ================================================================ T1 KU契约
def t1_ku_contract():
    S = "T1 KU数据契约"
    import ku_schema
    p = os.path.join(KB, "master_judged.json")
    if not os.path.exists(p):
        rec(S, "master_judged.json", "FAIL", "不存在，请先跑 kb/build_master.py")
        return None
    m = load_json(p)

    ck(S, "schema 版本号存在", m.get("schema") == ku_schema.SCHEMA_VERSION,
       f"期望 {ku_schema.SCHEMA_VERSION}，实际 {m.get('schema')}", m.get("schema"))

    kus = m.get("kus", [])
    ck(S, "KU 非空", len(kus) > 0, "master 里一条 KU 都没有", f"{len(kus)} 条")
    ck(S, "count 字段与实际一致", m.get("count") == len(kus),
       f"count={m.get('count')} 实际={len(kus)}")

    # 逐条过 schema 校验
    bad = []
    for i, k in enumerate(kus):
        errs = ku_schema.validate(k)
        if errs:
            bad.append(f"[{i}]{k.get('standard_no')}/{k.get('title','')[:16]}: {'; '.join(errs)}")
    ck(S, "全部 KU 通过 schema 校验", not bad,
       f"{len(bad)} 条不合规 -> " + " | ".join(bad[:5]), f"{len(kus)} 条全通过")

    # 必填字段
    miss = [f"{k.get('standard_no')}#{i}" for i, k in enumerate(kus)
            if not k.get("standard_no") or not k.get("title") or not k.get("clause")]
    ck(S, "standard_no/title/clause 必填", not miss,
       f"{len(miss)} 条缺字段: {miss[:5]}")

    # 标准号格式
    badstd = sorted({k["standard_no"] for k in kus
                     if k.get("standard_no") and not STD_RE.match(k["standard_no"].strip())})
    ck(S, "标准号格式合法", not badstd, f"非法标准号: {badstd[:5]}")

    # 年份必须带（版本混淆是这个项目的老坑：3048 有 2007/2025 两版）
    noyear = sorted({k["standard_no"] for k in kus if not re.search(r"-\d{4}$", k.get("standard_no", ""))})
    ck(S, "标准号带年份（防版本混淆）", not noyear, f"缺年份: {noyear[:5]}")

    # 去重
    seen, dup = set(), []
    for k in kus:
        key = (k.get("standard_no"), k.get("title"))
        if key in seen:
            dup.append(key)
        seen.add(key)
    ck(S, "KU 无重复(标准号+标题)", not dup, f"{len(dup)} 条重复: {dup[:3]}")

    # 考点必须有可考的东西
    empty_req = [k["title"] for k in kus
                 if k.get("is_exam_point") and not k.get("key_requirements")]
    ck(S, "考点 KU 都有 key_requirements", not empty_req,
       f"{len(empty_req)} 条考点没有要点: {empty_req[:3]}")

    return m


# ================================================================ T2 题库契约
def t2_bank_contract(banks):
    S = "T2 题库结构契约"
    import generate
    all_ids, dup_ids, loaded = set(), [], {}

    for p in banks:
        name = os.path.basename(p)
        try:
            b = load_json(p)
        except Exception as e:
            ck(S, f"{name} 可解析", False, f"JSON 错误: {e}")
            continue
        loaded[p] = b
        ck(S, f"{name} 可解析", True, msg_pass="ok")

        errs = generate.validate(b)
        hard = [e for e in errs if not e.startswith("[warn]")]
        soft = [e for e in errs if e.startswith("[warn]")]
        ck(S, f"{name} 引擎硬校验", not hard, f"{len(hard)} 个错误: {hard[:3]}")
        if soft:
            rec(S, f"{name} 引擎软告警", "WARN", f"{len(soft)} 条: {soft[:2]}")

        # 题型细粒度结构
        prob = []
        for it in b.get("choice", []):
            if len(it.get("options", [])) != 4:
                prob.append(f"{it['id']} 选项非4个")
            a = it.get("answer")
            if not isinstance(a, int) or not (0 <= a < len(it.get("options", []))):
                prob.append(f"{it['id']} answer 越界/非整数")
        for it in b.get("judge", []):
            if not isinstance(it.get("answer"), bool):
                prob.append(f"{it['id']} judge.answer 非布尔")
        for it in b.get("fill", []):
            if not isinstance(it.get("answers"), list) or not it["answers"]:
                prob.append(f"{it['id']} fill.answers 非非空列表")
        for it in b.get("calc", []):
            for s in it.get("subs", []):
                if len(s) != 4:
                    prob.append(f"{it['id']} calc.sub 非4元组")
        ck(S, f"{name} 四题型结构", not prob, f"{len(prob)} 处: {prob[:3]}")

        # 题号唯一（跨题库也要唯一，组卷时会混在一起）
        noid = []
        for t in ("choice", "judge", "fill", "match", "calc"):
            for idx, it in enumerate(b.get(t, []) or []):
                i = it.get("id")
                if not i:
                    noid.append(f"{t}[{idx}]")
                    continue
                if i in all_ids:
                    dup_ids.append(i)
                all_ids.add(i)
        ck(S, f"{name} 每题都有 id", not noid,
           f"{len(noid)} 题缺 id: {noid[:5]}（无法记录作答/错题）")

    ck(S, "全库题号跨文件唯一", not dup_ids,
       f"{len(dup_ids)} 个重复题号: {sorted(set(map(str, dup_ids)))[:5]}（组卷混题会互相覆盖）",
       f"{len(all_ids)} 个题号")
    return loaded


# ================================================================ T3 判分自检
def t3_scoring(loaded):
    S = "T3 判分自检"
    import generate
    for p, b in loaded.items():
        name = os.path.basename(p)
        sc = generate.compute_score(b)
        ck(S, f"{name} 总分>0", sc["total"] > 0, "总分为0，题库空？", f"{sc['total']} 分")

        total, got, ok = generate.self_check(b)
        ck(S, f"{name} 满分卷=满分", ok, f"标准答案只得 {got}/{total}（判分规则与答案不自洽）",
           f"{got}/{total}")

        zero = generate.zero_check(b)
        ck(S, f"{name} 全错卷=0分", zero == 0, f"全答错却得 {zero} 分（送分bug）")

        blank = generate.grade_all(b, {"choice": {}, "judge": {}, "fill": {},
                                       "match": {}, "calc": {}})
        ck(S, f"{name} 空卷=0分", blank["got"]["total"] == 0,
           f"空卷得 {blank['got']['total']} 分（不作答也给分）")


# ================================================================ T4 判分parity
def t4_parity(banks, use_node):
    S = "T4 判分一致性(PY↔JS)"
    if not use_node:
        rec(S, "全部用例", "SKIP", "--no-node")
        return
    if not os.path.exists(NODE):
        rec(S, "Node 可用", "SKIP", f"未找到 {NODE}")
        return
    script = os.path.join(ENGINE, "test_parity.py")
    for p in banks:
        name = os.path.basename(p)
        try:
            r = subprocess.run([PY, script, p], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=180, cwd=ENGINE)
        except subprocess.TimeoutExpired:
            ck(S, f"{name}", False, "超时 180s")
            continue
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0
        tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
        ck(S, f"{name} 两端逐题一致", ok, f"退出码{r.returncode} | {tail[0][:160]}", tail[0][:80])


# ================================================================ T5 溯源
def t5_traceability(loaded, master, strict):
    S = "T5 溯源零幻觉"
    if master is None:
        rec(S, "全部用例", "SKIP", "master 缺失")
        return
    known_std = set(master.get("standards", []))
    # 标准 -> 已建 KU 的条款集合
    clause_map = {}
    for k in master.get("kus", []):
        clause_map.setdefault(k["standard_no"], set()).add(str(k.get("clause", "")).strip())

    for p, b in loaded.items():
        name = os.path.basename(p)
        items = []
        for t in ("choice", "judge", "fill", "match", "calc"):
            items += [(t, it) for it in (b.get(t) or [])]
        if not items:
            continue

        no_src, bad_std, no_clause, off_kb = [], [], [], []
        for t, it in items:
            src = it.get("src")
            if not src:
                no_src.append(it.get("id"))
                continue
            if isinstance(src, str):
                # 老格式 "GB/T 2951.13-2008 §5 预处理"
                mm = re.match(r"^(GB/T|GB|JB/T|IEC)\s?[\d.]+(-\d{4})?", src.strip())
                if not mm:
                    bad_std.append(it.get("id"))
                    continue
                std = mm.group(0).strip()
                clause = src[len(std):].strip()
            else:
                std = str(src.get("standard_no", "")).strip()
                clause = str(src.get("clause", "")).strip()
            if std not in known_std:
                bad_std.append(f"{it.get('id')}:{std}")
            if not clause:
                no_clause.append(it.get("id"))
            elif std in clause_map:
                # 条款号能否对上已建 KU（前缀匹配：4.1.1.2 命中 KU 的 4.1）
                num = re.match(r"[§\s]*([\d.]+)", clause)
                if num:
                    n = num.group(1).rstrip(".")
                    hit = any(n == c or n.startswith(c + ".") or c.startswith(n + ".")
                              for c in clause_map[std] if c)
                    if not hit:
                        off_kb.append(f"{it.get('id')}:{std} {n}")

        ck(S, f"{name} 每题都有 src", not no_src,
           f"{len(no_src)}/{len(items)} 题无溯源: {no_src[:5]}（答案无法回查=幻觉风险）",
           f"{len(items)} 题全有", warn_only=not strict)
        ck(S, f"{name} src 标准号在库内", not bad_std,
           f"{len(bad_std)} 题引用未入库标准: {bad_std[:3]}")
        ck(S, f"{name} src 有条款号", not no_clause,
           f"{len(no_clause)} 题只有标准号没条款: {no_clause[:5]}", warn_only=not strict)
        if off_kb:
            rec(S, f"{name} 条款可回查 KU", "WARN",
                f"{len(off_kb)}/{len(items)} 题条款未建 KU（题可能对，但无法自动回查）: {off_kb[:3]}")
        else:
            rec(S, f"{name} 条款可回查 KU", "PASS", "全部命中")


# ================================================================ T6 前端冒烟
def t6_frontend(use_node):
    S = "T6 前端SPA冒烟"
    pub = os.path.join(ROOT, "public")
    appjs = os.path.join(pub, "app.js")

    if use_node and os.path.exists(NODE) and os.path.exists(appjs):
        r = subprocess.run([NODE, "--check", appjs], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        ck(S, "app.js 语法通过", r.returncode == 0,
           (r.stderr or "")[:200])
        gjs = os.path.join(pub, "data", "grade.js")
        if os.path.exists(gjs):
            probe = ("const G=require(%s);"
                     "const b={meta:{scoring:{choice:2}},choice:[{id:'x',q:'q',"
                     "options:['a','b','c','d'],answer:1,points:2}]};"
                     "const r=G.gradeAll(b,{choice:{x:1}});"
                     "if(r.got.total!==2)throw new Error('bad '+r.got.total);"
                     "console.log('ok');") % json.dumps(gjs.replace("\\", "/"))
            r2 = subprocess.run([NODE, "-e", probe], capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
            ck(S, "public/data/grade.js 可判分", r2.returncode == 0,
               (r2.stderr or "")[:200])
    else:
        rec(S, "app.js 语法/判分", "SKIP", "无 Node 或文件缺失")

    # app.js 引用的数据文件必须存在且可解析
    if os.path.exists(appjs):
        src = open(appjs, encoding="utf-8").read()
        refs = sorted(set(re.findall(r"['\"](data/[\w.\-]+\.json)['\"]", src)))
        missing, broken = [], []
        for rf in refs:
            fp = os.path.join(pub, rf)
            if not os.path.exists(fp):
                missing.append(rf)
                continue
            try:
                load_json(fp)
            except Exception as e:
                broken.append(f"{rf}:{e}")
        ck(S, "SPA 引用的数据文件齐全", not missing,
           f"缺失: {missing}（页面会白屏）", f"{len(refs)} 个引用全在")
        ck(S, "SPA 数据文件可解析", not broken, f"损坏: {broken[:3]}")

    # public/data 与 rules/out 同名文件是否同步（防"改了没部署"）
    stale = []
    for pd in glob.glob(os.path.join(pub, "data", "*.json")):
        base = os.path.basename(pd)
        for cand in (os.path.join(ROOT, "rules", base),
                     os.path.join(ROOT, "out", base.replace(".json", "_bank.json"))):
            if os.path.exists(cand):
                try:
                    if load_json(cand) != load_json(pd):
                        stale.append(base)
                except Exception:
                    pass
                break
    ck(S, "public/data 与真源同步", not stale,
       f"不一致: {sorted(set(stale))}（改了题库忘了同步到前端）", warn_only=True)


# ================================================================ T7 覆盖度
def t7_coverage(master, loaded):
    S = "T7 资产覆盖度"
    import collections
    if master is None:
        rec(S, "全部用例", "SKIP", "master 缺失")
        return {}
    kus = master.get("kus", [])
    stds = set(master.get("standards", []))
    prio = collections.Counter(k.get("priority") for k in kus)
    exam_kus = [k for k in kus if k.get("is_exam_point")]

    banked_std = set()
    nq = 0
    for b in loaded.values():
        for t in ("choice", "judge", "fill", "match", "calc"):
            for it in (b.get(t) or []):
                nq += 1
                src = it.get("src")
                if isinstance(src, dict) and src.get("standard_no"):
                    banked_std.add(src["standard_no"].strip())
                elif isinstance(src, str):
                    mm = re.match(r"^(GB/T|GB|JB/T|IEC)\s?[\d.]+(-\d{4})?", src.strip())
                    if mm:
                        banked_std.add(mm.group(0).strip())

    raw = len(glob.glob(os.path.join(KB, "raw", "*.json")))
    kuf = len(glob.glob(os.path.join(KB, "judged", "_ku_doc*.json")))
    stats = {"raw文档": raw, "KU文件": kuf, "已判标准": len(stds), "KU总数": len(kus),
             "考点KU": len(exam_kus), "P0": prio.get("P0", 0), "P1": prio.get("P1", 0),
             "P2": prio.get("P2", 0), "非考点NA": prio.get("NA", 0),
             "题库文件": len(loaded), "题目总数": nq,
             "已出题标准": len(banked_std),
             "出题覆盖率": f"{len(banked_std)}/{len(stds)}"}
    rec(S, "资产统计", "PASS", json.dumps(stats, ensure_ascii=False))

    ck(S, "P0 考点数达标(>=30)", prio.get("P0", 0) >= 30,
       f"仅 {prio.get('P0',0)} 条 P0", f"{prio.get('P0',0)} 条", warn_only=True)
    ck(S, "题目总数达标(>=100)", nq >= 100, f"仅 {nq} 题", f"{nq} 题", warn_only=True)

    gap = sorted(stds - banked_std)
    ck(S, "已判标准都已出题", not gap,
       f"{len(gap)}/{len(stds)} 份标准判了但没出题: {gap[:8]}", warn_only=True)
    return stats


# ================================================================ T8 后端服务冒烟
def t8_backend():
    """启动真实 server.py，HTTP 层验证 /api/build 与 /api/grade，
    把"整个系统"的后端路径也纳入回归（不只是资产与前端）。"""
    S = "T8 后端服务冒烟"
    sp = os.path.join(ROOT, "server.py")
    if not os.path.exists(sp):
        rec(S, "全部用例", "SKIP", "无 server.py")
        return
    import socket as _sock
    _s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
    _s.bind(("127.0.0.1", 0))
    PORT_T = _s.getsockname()[1]
    _s.close()
    try:
        proc = subprocess.Popen([PY, "server.py", str(PORT_T)], cwd=ROOT,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        rec(S, "启动后端", "FAIL", f"{type(e).__name__}: {e}")
        return

    base = f"http://127.0.0.1:{PORT_T}"
    _opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕过沙箱代理，避免 localhost 偶发断连
    ready = False
    for _ in range(40):
        try:
            _opener.open(base + "/", timeout=1)
            ready = True
            break
        except Exception:
            time.sleep(0.5)
    if not ready:
        rec(S, "后端启动", "FAIL", "40×0.5s 内未响应 /")
        try:
            proc.terminate()
        except Exception:
            pass
        return
    rec(S, "后端启动", "PASS", f"server.py :{PORT_T} 已响应 /")

    try:
        sys.path.insert(0, ROOT)
        import server as _srv
        import generate as _gen
    except Exception as e:
        rec(S, "导入后端模块", "FAIL", f"{type(e).__name__}: {e}")
        try:
            proc.terminate()
        except Exception:
            pass
        return

    def post(path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with _opener.open(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))

    def build_answers(b, wrong):
        a = {"choice": {}, "judge": {}, "fill": {}, "calc": {}}
        for it in b.get("choice", []):
            ans = int(it["answer"])
            a["choice"][it["id"]] = (ans + 1) % 4 if wrong else ans
        for it in b.get("judge", []):
            ans = bool(it["answer"])
            a["judge"][it["id"]] = (not ans) if wrong else ans
        for it in b.get("fill", []):
            cor = list(it.get("answers", []))
            a["fill"][it["id"]] = ["__WRONG__"] * len(cor) if wrong else cor
        for it in b.get("calc", []):
            subs = it.get("subs", [])
            if wrong:
                vals = [(s[1] + 999 if isinstance(s[1], (int, float)) else str(s[1]) + "x")
                        for s in subs]
            else:
                vals = [s[1] for s in subs]
            a["calc"][it["id"]] = vals
        return a

    bank_name = "gbt_3956"
    bank = _srv.load_bank(bank_name)
    if not bank:
        rec(S, "/api/build 出卷", "SKIP", f"{bank_name} 未找到")
        rec(S, "/api/grade 判卷", "SKIP", f"{bank_name} 未找到")
    else:
        # ---- /api/build 按权重出卷
        groups = {}
        for sec in ("choice", "judge", "fill", "calc"):
            for it in bank.get(sec, []):
                k = _srv.std_prefix(it.get("src"))
                groups[k] = groups.get(k, 0) + 1
        kp = {k: 1 for k in groups}
        try:
            resp = post("/api/build", {"bank": bank_name, "kp_counts": kp})
            out = resp.get("bank", {})
            tot = sum(len(out.get(s, [])) for s in ("choice", "judge", "fill", "calc"))
            ok_struct = all(s in out for s in ("choice", "judge", "fill", "calc"))
            ok_scope = all(
                _srv.std_prefix(it.get("src")) in kp
                for sec in ("choice", "judge", "fill", "calc")
                for it in out.get(sec, []))
            ck(S, "/api/build 按权重出卷", ok_struct and tot > 0 and ok_scope,
               f"结构={ok_struct} 题数={tot} 越界={not ok_scope}")
        except Exception as e:
            ck(S, "/api/build 按权重出卷", False, f"{type(e).__name__}: {e}")

        # ---- /api/grade 判卷（满分 / 零分）
        full = _gen.compute_score(bank)["total"]
        try:
            r_ok = post("/api/grade", {"inline": bank, "answers": build_answers(bank, False)})
            r_bad = post("/api/grade", {"inline": bank, "answers": build_answers(bank, True)})
            got_ok = r_ok.get("got", {}).get("total", -1)
            got_bad = r_bad.get("got", {}).get("total", -1)
            ck(S, "/api/grade 满分卷=满分", got_ok == full,
               f"后端得 {got_ok} 期望 {full}（与权威引擎 compute_score 一致）")
            ck(S, "/api/grade 全错卷=0分", got_bad == 0, f"后端得 {got_bad}（送分bug）")
        except Exception as e:
            ck(S, "/api/grade 判卷", False, f"{type(e).__name__}: {e}")

    try:
        proc.terminate()
    except Exception:
        pass


# ================================================================ 报告
def report(stats):
    n = collections.Counter(r["status"] for r in RESULTS)
    dur = time.time() - _t0
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    w = 96
    print("=" * w)
    print(f"国缆杯学习系统 v2 · 系统级回归测试    {ts}")
    print("=" * w)
    cur = None
    for r in RESULTS:
        if r["suite"] != cur:
            cur = r["suite"]
            print(f"\n--- {cur} " + "-" * (w - len(cur) - 5))
        mark = {"PASS": "  ok  ", "FAIL": " FAIL ", "WARN": " warn ", "SKIP": " skip "}[r["status"]]
        line = f"[{mark}] {r['case']}"
        if r["msg"]:
            line += f"   {r['msg']}"
        print(line[:250])
    print("\n" + "=" * w)
    print(f"PASS {n['PASS']}   FAIL {n['FAIL']}   WARN {n['WARN']}   SKIP {n['SKIP']}"
          f"   共 {len(RESULTS)} 项 / {dur:.1f}s")
    print("结论：" + ("全部通过，可以部署" if n["FAIL"] == 0 else
                    f"存在 {n['FAIL']} 项失败，禁止部署"))
    print("=" * w)

    out = {"time": ts, "duration_s": round(dur, 1), "summary": dict(n),
           "stats": stats, "results": RESULTS}
    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    color = {"PASS": "#16a34a", "FAIL": "#dc2626", "WARN": "#d97706", "SKIP": "#6b7280"}
    rows = []
    cur = None
    for r in RESULTS:
        if r["suite"] != cur:
            cur = r["suite"]
            rows.append(f'<tr class="s"><td colspan="3">{cur}</td></tr>')
        rows.append(
            f'<tr><td><b style="color:{color[r["status"]]}">{r["status"]}</b></td>'
            f'<td>{r["case"]}</td><td class="m">{r["msg"]}</td></tr>')
    stat_html = "".join(f"<span><b>{k}</b>{v}</span>" for k, v in (stats or {}).items())
    html = f"""<!doctype html><html lang="zh"><meta charset="utf-8">
<title>系统回归测试报告 {ts}</title><style>
body{{font:14px/1.6 -apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#64748b;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}}
.card{{flex:1;min-width:110px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px}}
.card b{{display:block;font-size:24px}} .card span{{color:#64748b;font-size:12px}}
.stats{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;margin-bottom:16px;
display:flex;flex-wrap:wrap;gap:8px 18px;font-size:13px}}
.stats span b{{color:#334155;margin-right:6px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden}}
td{{padding:7px 12px;border-top:1px solid #f1f5f9;vertical-align:top}}
tr.s td{{background:#f1f5f9;font-weight:600;border-top:1px solid #e2e8f0}}
td:first-child{{width:64px;font-size:12px}} .m{{color:#64748b;font-size:12px;word-break:break-all}}
.verdict{{margin:18px 0;padding:14px 16px;border-radius:10px;font-weight:600;
background:{'#dcfce7' if n['FAIL']==0 else '#fee2e2'};color:{'#166534' if n['FAIL']==0 else '#991b1b'}}}
</style><div class="wrap">
<h1>国缆杯学习系统 v2 · 系统级回归测试</h1>
<div class="sub">{ts} · 耗时 {dur:.1f}s · 共 {len(RESULTS)} 项</div>
<div class="cards">
<div class="card"><b style="color:#16a34a">{n['PASS']}</b><span>PASS</span></div>
<div class="card"><b style="color:#dc2626">{n['FAIL']}</b><span>FAIL</span></div>
<div class="card"><b style="color:#d97706">{n['WARN']}</b><span>WARN</span></div>
<div class="card"><b style="color:#6b7280">{n['SKIP']}</b><span>SKIP</span></div>
</div>
<div class="stats">{stat_html}</div>
<div class="verdict">{'✅ 全部通过，可以部署' if n['FAIL']==0 else f'❌ 存在 {n["FAIL"]} 项失败，禁止部署'}</div>
<table>{''.join(rows)}</table></div></html>"""
    with open(os.path.join(HERE, "report.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告：{os.path.join(HERE,'report.json')}\n      {os.path.join(HERE,'report.html')}")
    return 1 if n["FAIL"] else 0


import collections  # noqa: E402


def main():
    args = sys.argv[1:]
    use_node = "--no-node" not in args
    strict = "--strict-trace" in args

    banks = t0_env()
    master = t1_ku_contract()
    loaded = t2_bank_contract(banks)
    t3_scoring(loaded)
    t4_parity(banks, use_node)
    t5_traceability(loaded, master, strict)
    t6_frontend(use_node)
    stats = t7_coverage(master, loaded)
    t8_backend()
    sys.exit(report(stats))


if __name__ == "__main__":
    main()
