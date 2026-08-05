#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国缆杯学习/考试系统 v2 —— L5 服务层（薄壳，零依赖）
------------------------------------------------------------------
职责：
  1) 托管网页（仪表盘 / 在线考试 / 自测卷 / 学习页）
  2) 服务端判分（调用 engine/generate.py 的 grade_all，闭卷防作弊）
  3) 学习层消费：出卷器(按权重) / 闪卡库(浏览+学习) / 术语库(搜索筛选)
                 成绩 / 弱项 / 反馈系统(含日志) / 考试大纲(权重真源)

设计红线（用户拍板）：
  - 本文件不写任何"出题/生成"逻辑——那由大模型 + 技能(standards-exam-generator)
    产出数据落盘到 rules/ 与 materials/。
  - 出卷器只是"从题库按权重确定性抽题"的消费者，不生成新题。
  - 判分真源 = engine/generate.py（Python 权威） + engine/grade.js（浏览器镜像）。
  - 闭卷：答案永远只留在服务端，前端页面不出现正确答案。
仅用 Python 标准库，避免 Flask 安装受沙箱拦截。
"""
import os
import sys
import json
import re
import random
from datetime import datetime, date
import urllib.parse
import http.server
import socketserver

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine")
RULES = os.path.join(HERE, "rules")
MATERIALS = os.path.join(HERE, "materials")
OUT = os.path.join(HERE, "out")
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
SCORES = os.path.join(DATA, "scores.json")
FEEDBACK_JSON = os.path.join(DATA, "feedback.json")
FEEDBACK_JSONL = os.path.join(DATA, "feedback.jsonl")
FEEDBACK_LOG = os.path.join(DATA, "feedback.log")
FC_PROGRESS = os.path.join(DATA, "flashcard_progress.json")
SYLLABUS = os.path.join(MATERIALS, "syllabus_2026.json")
sys.path.insert(0, ENGINE)
import generate  # 复用 grade_all / grade_judge 等

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

CSS = """
*{box-sizing:border-box}
body{font-family:-apple-system,"Microsoft YaHei",sans-serif;max-width:960px;margin:0 auto;padding:24px 18px;color:#1f2329;line-height:1.6;background:#f7f8fa}
h1{font-size:24px;border-left:5px solid #2f6fed;padding-left:12px;margin:8px 0 20px}
h2{font-size:18px;margin:26px 0 10px;color:#2f6fed}
.card{background:#fff;border:1px solid #e6e8eb;border-radius:10px;padding:14px 16px;margin:10px 0;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
a.btn{display:inline-block;padding:6px 14px;border-radius:8px;background:#2f6fed;color:#fff;text-decoration:none;font-size:13px;margin:3px 0}
a.btn.alt{background:#eef2ff;color:#2f6fed}
a.btn.ghost{background:#fff;color:#555;border:1px solid #d0d3d9}
.q{border:1px solid #e6e8eb;border-radius:8px;padding:12px 14px;margin:10px 0;background:#fff}
.qt{font-weight:600;color:#333}
.src{font-size:12px;color:#888;margin-top:6px}
input[type=text],input:not([type]){padding:5px 8px;border:1px solid #cfd4da;border-radius:6px;font-size:14px;width:200px}
input[type=number]{padding:5px 8px;border:1px solid #cfd4da;border-radius:6px;font-size:14px;width:70px}
select{padding:5px 8px;border:1px solid #cfd4da;border-radius:6px;font-size:14px}
label{display:block;margin:3px 0 3px 2px;cursor:pointer}
.x{background:#fff;border:1px solid #e6e8eb;border-radius:10px;padding:16px;margin:10px 0}
.score{font-size:30px;font-weight:700;color:#16894a}
.bad{color:#c0392b}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;background:#eef2ff;color:#2f6fed;margin-right:5px}
footer{margin-top:34px;color:#9aa0a6;font-size:12px}
.fc{background:#fff;border:1px solid #e6e8eb;border-radius:12px;padding:22px;margin:14px 0;text-align:center;min-height:130px;display:flex;flex-direction:column;justify-content:center}
.fc .front{font-size:18px;font-weight:600}
.fc .back{font-size:16px;color:#16894a;margin-top:12px}
nav a{margin-right:10px;font-size:13px;color:#2f6fed;text-decoration:none}
.fb-fab{position:fixed;right:18px;bottom:18px;z-index:9999;width:52px;height:52px;border-radius:50%;background:#2f6fed;color:#fff;border:none;font-size:24px;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.25)}
.fb-bubble{position:fixed;z-index:9998;background:#2f6fed;color:#fff;border:none;padding:4px 10px;border-radius:14px;font-size:13px;cursor:pointer}
.sel-bubble{position:fixed;z-index:9997;background:#333;color:#fff;padding:5px 12px;border-radius:14px;font-size:13px;cursor:pointer;display:none}
.fb-modal{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:10000;display:none;align-items:center;justify-content:center}
.fb-box{background:#fff;border-radius:12px;padding:20px;width:min(440px,92vw)}
.fb-box textarea,.fb-box input{width:100%;margin:6px 0;padding:7px 9px;border:1px solid #cfd4da;border-radius:6px;font-size:14px}
.p0{background:#fdecea;color:#c0392b}.p1{background:#fff4e5;color:#b7791f}.p2{background:#eef2ff;color:#2f6fed}
.fb-tbl{width:100%;border-collapse:collapse;font-size:13px}
.fb-tbl th,.fb-tbl td{border:1px solid #e6e8eb;padding:6px 8px;text-align:left;vertical-align:top}
.fb-tbl th{background:#f0f3f8}
.fb-status{padding:2px 8px;border-radius:10px;font-size:12px}
.s-待整改{background:#fdecea;color:#c0392b}.s-整改中{background:#fff4e5;color:#b7791f}.s-已整改{background:#e6f6ec;color:#2f855a}
"""

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

STD_RE = re.compile(r"(GB/T\s?\d+[\.\-]\d+[\.\-]?\d*)", re.I)

def std_prefix(src):
    if not src:
        return "未归类"
    m = STD_RE.search(str(src).replace(" ", ""))
    return m.group(1).upper().replace(" ", "") if m else "未归类"

def list_banks():
    return sorted(f[:-5] for f in os.listdir(RULES) if f.endswith(".json"))

def list_materials():
    return sorted(f[:-5] for f in os.listdir(MATERIALS) if f.endswith(".json"))

def list_flashcard_decks():
    return sorted(f[:-5] for f in os.listdir(MATERIALS) if f.endswith("_flashcards.json"))

def list_terminology():
    return sorted(f[:-5] for f in os.listdir(MATERIALS) if f.endswith("_terminology.json"))

def practice_html_for(name):
    for cand in (f"{name}_exam.html", f"{name}_preview.html"):
        if os.path.isfile(os.path.join(OUT, cand)):
            return cand
    return None

def strip_answers(bank):
    b = json.loads(json.dumps(bank))
    for sec in ("choice", "judge", "fill", "calc"):
        for it in b.get(sec, []):
            if sec == "fill":
                it["blanks"] = len(it.get("answers", []))
            if sec == "calc":
                it["subs"] = [[s[0]] for s in it.get("subs", [])]
            it.pop("answer", None)
            it.pop("answers", None)
    return b

def load_bank(name):
    fp = os.path.join(RULES, name + ".json")
    if not os.path.isfile(fp):
        return None
    return json.load(open(fp, encoding="utf-8"))

def group_by_kp(bank):
    groups = {}
    for sec in ("choice", "judge", "fill", "calc"):
        for it in bank.get(sec, []):
            kp = std_prefix(it.get("src", ""))
            groups.setdefault(kp, 0)
            groups[kp] += 1
    return sorted(groups.items(), key=lambda x: -x[1])

# ----------------------------------------------------------------------------
# 反馈系统：内存/文件读写 + 追加日志
FB_CATS = ["题目错误", "题库质量", "学习材料", "功能缺陷", "其他"]
FB_STATUS = ["待整改", "整改中", "已整改"]

def load_feedback():
    if not os.path.isfile(FEEDBACK_JSON):
        return []
    try:
        return json.load(open(FEEDBACK_JSON, encoding="utf-8"))
    except Exception:
        return []

def save_feedback(recs):
    tmp = FEEDBACK_JSON + ".tmp"
    json.dump(recs, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, FEEDBACK_JSON)

def append_feedback_log(rec):
    # 追加式：jsonl（机器友好）+ log（人读，便于 grep / Agent 整改）
    with open(FEEDBACK_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    line = f"[{rec['created_at']}] id={rec['id']} cat={rec['category']} page={rec.get('page','')} loc={rec.get('location','')} status={rec['status']} :: {rec['detail']}"
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def add_feedback(payload):
    recs = load_feedback()
    nid = (max([r["id"] for r in recs], default=0) + 1)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = {
        "id": nid,
        "created_at": now,
        "page": payload.get("page", ""),
        "category": payload.get("category", "其他"),
        "location": payload.get("location", ""),
        "detail": payload.get("detail", ""),
        "status": "待整改",
        "resolution": "",
        "resolved_at": "",
    }
    recs.append(rec)
    save_feedback(recs)
    append_feedback_log(rec)
    return rec

def resolve_feedback(fid, resolution, status):
    recs = load_feedback()
    for r in recs:
        if r["id"] == fid:
            r["resolution"] = resolution
            r["status"] = status
            r["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_feedback(recs)
            append_feedback_log(r)
            return True
    return False

def load_fc_progress():
    if not os.path.isfile(FC_PROGRESS):
        return {}
    try:
        return json.load(open(FC_PROGRESS, encoding="utf-8"))
    except Exception:
        return {}

def save_fc_progress(data):
    tmp = FC_PROGRESS + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, FC_PROGRESS)

def load_syllabus():
    if not os.path.isfile(SYLLABUS):
        return None
    return json.load(open(SYLLABUS, encoding="utf-8"))

# ----------------------------------------------------------------------------
def dashboard_html():
    banks = list_banks()
    decks = list_flashcard_decks()
    terms = list_terminology()
    cards = []
    for name in banks:
        meta = load_bank(name).get("meta", {})
        title = " / ".join(meta.get("standard", [name]))
        total = meta.get("total", "?")
        bank = load_bank(name)
        q = sum(len(bank.get(s, [])) for s in ("choice", "judge", "fill", "calc"))
        ph = practice_html_for(name)
        cards.append(f"""<div class="card">
  <div><span class="tag">题库</span><b>{esc(title)}</b></div>
  <div style="color:#888;font-size:13px;margin:6px 0">总分 {total} ｜ 共 {q} 题</div>
  <div class="row">
    <a class="btn" href="/take/{name}">在线考试（闭卷·服务端判分）</a>
    <a class="btn alt" href="/builder?bank={name}">按权重出卷</a>
    <a class="btn ghost" href="/bank/{name}">题库 JSON</a>
    {f'<a class="btn ghost" href="/exam/{ph}">自测卷（含答案）</a>' if ph else ''}
  </div>
</div>""")
    deck_cards = "".join(f"""<div class="card"><div><span class="tag">闪卡</span><b>{esc(d)}</b></div>
  <div class="row" style="margin-top:8px">
  <a class="btn alt" href="/flashcards?deck={d}&mode=browse">浏览模式</a>
  <a class="btn" href="/flashcards?deck={d}&mode=study">学习模式(SM-2)</a>
  <a class="btn ghost" href="/material/{d}">JSON</a></div></div>""" for d in decks)
    term_cards = "".join(f"""<div class="card"><div><span class="tag">术语</span><b>{esc(t)}</b></div>
  <div class="row" style="margin-top:8px"><a class="btn alt" href="/terminology?file={t}">术语表</a></div></div>""" for t in terms)
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>国缆杯学习/考试系统 v2</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/builder">出卷器</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/weak">弱项</a><a href="/feedback">反馈日志</a></nav>
<h1>国缆杯学习 / 考试系统 v2</h1>
<div style="color:#666;font-size:14px">大模型出题 · 脚本判分 · 服务端闭卷。已入库题库 {len(banks)} 套、闪卡 {len(decks)} 副、术语 {len(terms)} 份。</div>
<h2>一、在线题库（考试 / 测验）</h2>
{''.join(cards) if cards else '<p>暂无题库，把标准文件丢进来后由大模型产出。</p>'}
<h2>二、学习材料（第 6 层学习层）</h2>
{deck_cards or '<p>暂无闪卡。</p>'}
{term_cards or '<p>暂无术语。</p>'}
<footer>v2 · L1 提取→L2 理解→L3 出题/材料→L4 脚本判分→L5 服务。生成侧（L1-L3）由大模型+技能完成，本服务只托管、判分与按权重出卷。</footer>
</body></html>"""

def take_html(name):
    return TAKE_TPL.replace("__NAME__", name)

def take_embedded_html(bank_obj):
    js = json.dumps(bank_obj, ensure_ascii=False)
    return TAKE_EMBED_TPL.replace("__BANK__", js)

TAKE_TPL = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>在线考试 - __NAME__</title><style>__CSS__</style></head><body>
<h1>在线考试 · __NAME__</h1>
<div id=app>加载中…</div>
<button id=submit style="display:none" onclick="submitExam()">交卷（服务端判分）</button>
<div id=result></div>
<script src="/static/grade.js"></script>
<script>
const NAME="__NAME__";
const EMBEDDED_NAME=NAME;
const EMBEDDED=null;
fetch('/bank/'+NAME+'?safe=1').then(r=>r.json()).then(bank=>render(bank));
__TAKE_JS__
</script>
</body></html>""".replace("__CSS__", CSS)

TAKE_EMBED_TPL = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>组卷考试</title><style>__CSS__</style></head><body>
<h1>组卷考试（按权重抽取）</h1>
<div id=app>加载中…</div>
<button id=submit style="display:none" onclick="submitExam()">交卷（服务端判分）</button>
<div id=result></div>
<script src="/static/grade.js"></script>
<script>
const EMBEDDED=__BANK__;
const EMBEDDED_NAME='(inline)';
render(EMBEDDED);
__TAKE_JS__
</script>
</body></html>""".replace("__CSS__", CSS)

TAKE_JS = r"""
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function render(bank){
  const app=document.getElementById('app');
  let html='<div class=x>本卷为<b>闭卷</b>：正确答案仅在服务端，提交后由服务器判分并返回得分。</div>';
  const secs=[['choice','一、选择题（4 选 1）'],['judge','二、判断题（√/×）'],['fill','三、填空题'],['calc','四、计算题']];
  for(const [sec,title] of secs){
    const items=bank[sec]||[]; if(!items.length) continue;
    html+='<h2>'+title+'</h2>';
    items.forEach((it,i)=>{
      let body='';
      if(sec==='choice'){
        body=it.options.map((o,j)=>`<label><input type=radio name="c_${it.id}" value="${j}"> ${String.fromCharCode(65+j)}. ${esc(o)}</label>`).join('');
      } else if(sec==='judge'){
        body=`<label><input type=radio name="j_${it.id}" value="1"> 正确(√)</label> <label><input type=radio name="j_${it.id}" value="0"> 错误(×)</label>`;
      } else if(sec==='fill'){
        const n=it.blanks||1;
        body=Array.from({length:n}).map((_,k)=>`<input id="f_${it.id}_${k}" placeholder="第${k+1}空"> `).join('');
      } else if(sec==='calc'){
        body=(it.subs||[]).map((s,k)=>`<div style="margin:4px 0">${esc(s[0]||'')}<br><input id="cal_${it.id}_${k}" placeholder="第${k+1}问"></div>`).join('');
      }
      html+=`<div class=q><div class=qt>${i+1}. ${esc(it.question||it.q||'')}</div>${body}<div class=src>来源：${esc(it.src||'')}</div></div>`;
    });
  }
  app.innerHTML=html;
  document.getElementById('submit').style.display='inline-block';
}
function submitExam(){
  const ans={choice:{},judge:{},fill:{},calc:{}};
  document.querySelectorAll('input[type=radio]').forEach(r=>{ if(r.checked){const m=r.name.split('_'); if(m[0]==='c')ans.choice[m[1]]=parseInt(r.value); if(m[0]==='j')ans.judge[m[1]]=r.value;} });
  document.querySelectorAll('input[id^="f_"]').forEach(inp=>{const [_,id,k]=inp.id.split('_'); (ans.fill[id]=ans.fill[id]||[])[k]=inp.value;});
  document.querySelectorAll('input[id^="cal_"]').forEach(inp=>{const [_,id,k]=inp.id.split('_'); (ans.calc[id]=ans.calc[id]||[])[k]=inp.value;});
  document.getElementById('submit').disabled=true;
  document.getElementById('result').innerHTML='判分中…';
  fetch('/api/grade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bank:EMBEDDED_NAME,inline:EMBEDDED,answers:ans})})
    .then(r=>r.json()).then(res=>{
      const g=res.got;
      let h=`<div class=x><div class="score">${g.total} 分</div><div style="color:#888">选择 ${g.choice} ｜ 判断 ${g.judge} ｜ 填空 ${g.fill} ｜ 计算 ${g.calc}</div>
      <div style="margin-top:8px"><a class="btn alt" href="/weak">看我的弱项</a> <a class="btn ghost" href="/scores">成绩记录</a></div></div>`;
      document.getElementById('result').innerHTML=h;
    }).catch(e=>{document.getElementById('result').innerHTML='<span class=bad>提交失败：'+e+'</span>';document.getElementById('submit').disabled=false;});
}
"""
TAKE_TPL = TAKE_TPL.replace("__TAKE_JS__", TAKE_JS)
TAKE_EMBED_TPL = TAKE_EMBED_TPL.replace("__TAKE_JS__", TAKE_JS)

def builder_html(bank_name):
    bank = load_bank(bank_name)
    if not bank:
        return f"<h1>出卷器</h1><p class=bad>题库 {esc(bank_name)} 不存在</p>"
    kps = group_by_kp(bank)
    rows = "".join(
        f'<div class="card"><span class="tag">{esc(kp)}</span> 共 {cnt} 题'
        f' &nbsp; 抽 <input type=number min=0 max={cnt} value=0 id="kp_{i}"> 题</div>'
        for i, (kp, cnt) in enumerate(kps)
    )
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>出卷器 - {esc(bank_name)}</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/weak">弱项</a></nav>
<h1>按权重出卷 · {esc(bank_name)}</h1>
<div style="color:#666;font-size:14px">给每个知识点设「抽题数」（考得重/要求高就多设），系统从题库确定性抽取组卷。零权重项不抽。</div>
<div class="card"><a class="btn alt" href="#" onclick="autoFromSyllabus();return false">📚 按考试大纲自动配权重</a> <span style="color:#888;font-size:12px" id="autoMsg"></span></div>
<div id=kps>{rows}</div>
<button class="btn" style="margin-top:12px" onclick="build()">生成试卷（闭卷）</button>
<div id=out></div>
<script>
const BANK="{esc(bank_name)}";
const KPS={json.dumps([k for k,_ in kps], ensure_ascii=False)};
function autoFromSyllabus(){{
  document.getElementById('autoMsg').textContent='读取大纲中…';
  fetch('/api/syllabus_weights?bank='+encodeURIComponent(BANK)).then(r=>r.json()).then(j=>{{
    if(j.error){{document.getElementById('autoMsg').textContent='该题库无匹配大纲';return;}}
    let hit=0;
    KPS.forEach((kp,i)=>{{ if(j.kp_counts[kp]!==undefined){{document.getElementById('kp_'+i).value=j.kp_counts[kp];hit++;}} }});
    document.getElementById('autoMsg').textContent='已按大纲认知层次配权重（匹配 '+hit+' 个知识点）';
  }});
}}
function build(){{
  const counts={{}};
  KPS.forEach((kp,i)=>{{ counts[kp]=parseInt(document.getElementById('kp_'+i).value)||0; }});
  document.getElementById('out').innerHTML='组卷中…';
  fetch('/api/build',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{bank:BANK,kp_counts:counts}})}})
    .then(r=>r.json()).then(res=>{{
      if(res.error){{document.getElementById('out').innerHTML='<span class=bad>'+res.error+'</span>';return;}}
      const b=res.bank;
      const total=(b.choice||[]).length+(b.judge||[]).length+(b.fill||[]).length+(b.calc||[]).length;
      document.getElementById('out').innerHTML='<div class=x>已组卷 <b>'+total+' 题</b>。'+
        '<a class="btn" href="#" onclick="start()">开始考试</a></div>';
      window.__examBank=b;
    }});
}}
function start(){{
  const b=window.__examBank;
  const w=window.open('','_blank');
  fetch('/api/exam_html',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{bank:b}})}})
    .then(r=>r.text()).then(html=>{{ w.document.open(); w.document.write(html); w.document.close(); }});
  return false;
}}
</script>
</body></html>"""

def flashcards_html(deck, mode):
    fp = os.path.join(MATERIALS, deck + ".json")
    if not os.path.isfile(fp):
        return f"<h1>闪卡</h1><p class=bad>牌组 {esc(deck)} 不存在</p>"
    data = json.load(open(fp, encoding="utf-8"))
    cards = data.get("cards", [])
    stds = sorted({c.get("std", "") for c in cards if c.get("std")})
    methods = sorted({c.get("method", "") for c in cards if c.get("method")})
    prios = ["P0", "P1", "P2"]
    prio_badge = {"P0": "p0", "P1": "p1", "P2": "p2"}
    mname = {"sample_prep": "样品制备", "test_method": "试验方法", "parameter": "参数表", "requirement": "要求/安全"}
    std_tags = "".join(f'<a class="tag" href="#" onclick="filterBy(\'std\',\'{s}\');return false">{s}</a>' for s in stds)
    method_tags = "".join(f'<a class="tag" href="#" onclick="filterBy(\'method\',\'{m}\');return false">{mname.get(m,m)}</a>' for m in methods)
    prio_tags = "".join(f'<a class="tag {prio_badge.get(p,"")}" href="#" onclick="filterBy(\'priority\',\'{p}\');return false">{p}</a>' for p in prios if any(c.get("priority")==p for c in cards))
    is_study = (mode == "study")
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>闪卡 - {esc(deck)}</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">牌组列表</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/weak">弱项</a><a href="/feedback">反馈</a></nav>
<h1>闪卡 · {esc(deck)}</h1>
<div class="row" style="margin-bottom:8px">
  <a class="btn ghost" href="/flashcards?deck={esc(deck)}&mode=browse">浏览模式</a>
  <a class="btn ghost" href="/flashcards?deck={esc(deck)}&mode=study">学习模式(SM-2)</a>
</div>
<div id=filters>
  <div style="margin:6px 0">标准：{std_tags or '—'}</div>
  <div style="margin:6px 0">方法：{method_tags or '—'}</div>
  <div style="margin:6px 0">优先级：{prio_tags or '—'} &nbsp; <a class="tag" href="#" onclick="clearFilter();return false">清除筛选</a></div>
  <div style="margin:6px 0"><label><input type=checkbox id=wshuffle> 加权洗牌（P0 多出现，强化重点）</label></div>
</div>
<div class=fc id=card onclick="flip()"><div class=front id=front></div><div class=back id=back style="display:none"></div></div>
<div class="row" style="margin-top:10px">
<button class="btn ghost" onclick="prev()">上一张</button>
<button class="btn ghost" onclick="next()">下一张</button>
<span id=pos style="margin-left:8px;color:#888"></span>
{'<span id=due style="margin-left:8px;color:#16894a"></span>' if is_study else ''}
</div>
{'''<div class="row" id=rateBtns style="margin-top:10px;display:none">
<button class="btn" style="background:#c0392b" onclick="rate(0)">完全不会</button>
<button class="btn" style="background:#e67e22" onclick="rate(1)">困难</button>
<button class="btn" style="background:#2f6fed" onclick="rate(3)">良好</button>
<button class="btn" style="background:#16894a" onclick="rate(5)">轻松</button>
</div>''' if is_study else '<button class="btn" id=fbCardBtn onclick="openCardFb(CARDS[idx])">👎 反馈此卡</button>'}
<script>
const CARDS={json.dumps(cards, ensure_ascii=False)};
const DECK="{esc(deck)}";
const IS_STUDY={'true' if is_study else 'false'};
let PROG={{}};
let idx=0,shown=false;
let filt={{key:null,val:null}};
function visible(){{
  return CARDS.filter(c=>!filt.key || c[filt.key]===filt.val);
}}
function buildDeck(){{
  let deck=visible().slice();
  if(!IS_STUDY && document.getElementById('wshuffle').checked){{
    const w={{P0:3,P1:2,P2:1}}; deck=[];
    visible().forEach(c=>{{const n=w[c.priority]||1; for(let i=0;i<n;i++) deck.push(c);}});
  }}
  if(IS_STUDY){{
    const today=new Date().toISOString().slice(0,10);
    const due=visible().filter(c=>{{const p=PROG[c.id]; return !p||!p.due||p.due<=today;}});
    deck = due.length? due : visible();
  }}
  return deck;
}}
let DECKARR=buildDeck();
function render(){{
  if(!DECKARR.length){{document.getElementById('front').textContent='（无匹配卡片）';document.getElementById('back').style.display='none';return;}}
  const c=DECKARR[idx];
  document.getElementById('front').textContent=c.front;
  document.getElementById('back').innerHTML='【'+c.kind+'·'+c.priority+'】'+c.back+'<br><span class=src>'+c.src+'</span>';
  document.getElementById('back').style.display='none'; shown=false;
  document.getElementById('pos').textContent=(idx+1)+'/'+DECKARR.length;
  if(IS_STUDY){{
    const p=PROG[c.id];
    document.getElementById('due').textContent = p? ('下次:'+p.due+' 熟练度'+p.ease.toFixed(2)) : '新卡';
    document.getElementById('rateBtns').style.display='block';
  }}
}}
function flip(){{shown=!shown;document.getElementById('back').style.display=shown?'block':'none';}}
function next(){{idx=(idx+1)%DECKARR.length;render();}}
function prev(){{idx=(idx-1+DECKARR.length)%DECKARR.length;render();}}
function filterBy(k,v){{filt={{key:k,val:v}};DECKARR=buildDeck();idx=0;render();}}
function clearFilter(){{filt={{key:null,val:null}};DECKARR=buildDeck();idx=0;render();}}
document.getElementById('wshuffle').addEventListener('change',()=>{{if(!IS_STUDY){{DECKARR=buildDeck();idx=0;render();}}}});
function rate(q){{
  const c=DECKARR[idx];
  let p=PROG[c.id]||{{ease:2.5,interval:0,reps:0,due:null}};
  if(q<3){{p.reps=0;p.interval=0;}}
  else{{ if(p.reps===0)p.interval=1; else if(p.reps===1)p.interval=6; else p.interval=Math.round(p.interval*p.ease); p.reps+=1;
        p.ease=p.ease+0.1-(5-q)*(0.08+(5-q)*0.02); if(p.ease<1.3)p.ease=1.3; }}
  const d=new Date(); d.setDate(d.getDate()+p.interval); p.due=d.toISOString().slice(0,10);
  PROG[c.id]=p; saveProg();
  idx=(idx+1)%DECKARR.length; render();
}}
function saveProg(){{fetch('/api/flashcard_progress',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{deck:DECK,progress:PROG}})}});}}
fetch('/api/flashcard_progress?deck='+encodeURIComponent(DECK)).then(r=>r.json()).then(j=>{{PROG=j.progress||{{}}; DECKARR=buildDeck(); render();}});
document.addEventListener('keydown',e=>{{ if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return; if(e.key==='ArrowLeft')prev(); else if(e.key==='ArrowRight')next(); else if(e.key===' '){{e.preventDefault();flip();}} }});
</script>
</body></html>"""

def terminology_html(fname):
    fp = os.path.join(MATERIALS, fname + ".json")
    if not os.path.isfile(fp):
        return f"<h1>术语</h1><p class=bad>文件 {esc(fname)} 不存在</p>"
    data = json.load(open(fp, encoding="utf-8"))
    terms = data.get("terms", [])
    cats = sorted({t.get("category", "") for t in terms if t.get("category")})
    cat_opts = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats)
    rows = "".join(
        f'''<div class="card term" data-cat="{esc(t.get('category',''))}" data-txt="{esc((t.get('term_cn','')+t.get('definition','')+t.get('term_en','')).lower())}">
  <div><b>{esc(t.get('term_cn',''))}</b> <span class="tag">{esc(t.get('term_en',''))}</span> {('<span class="tag">'+esc(t.get('abbrev',''))+'</span>') if t.get('abbrev') else ''}</div>
  <div style="margin-top:6px">{esc(t.get('definition',''))}</div>
  {('<div style="margin-top:6px;color:#16894a">📌 考点：'+''.join("<div>· "+esc(p)+"</div>" for p in t.get("exam_points",[]))+'</div>') if t.get('exam_points') else ''}
  <div class="row" style="margin-top:6px;color:#888;font-size:12px">
    {('<span class="tag">'+esc(t.get('category',''))+'</span>') if t.get('category') else ''}
    {(''.join('<span class="tag">'+esc(r)+'</span>' for r in t.get("ref_standards",[]))) if t.get('ref_standards') else ''}
    {('<span class="tag">'+esc(t.get('key_values',''))+'</span>') if t.get('key_values') else ''}
  </div>
  {('<div style="margin-top:4px;color:#666;font-size:12px">关联：'+esc(' / '.join(t.get('related_terms',[])))+'</div>') if t.get('related_terms') else ''}
</div>''' for t in terms
    )
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>术语库 - {esc(fname)}</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语列表</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/weak">弱项</a><a href="/feedback">反馈</a></nav>
<h1>术语库 · {esc(fname)}（{len(terms)} 条）</h1>
<div class="card">
  <input type=text id=search placeholder="搜索术语/定义…" oninput="applyFilter()">
  <select id=cat onchange="applyFilter()"><option value="">全部分类</option>{cat_opts}</select>
  <span id=cnt style="color:#888;margin-left:8px"></span>
</div>
{rows}
<script>
function applyFilter(){{
  const q=document.getElementById('search').value.trim().toLowerCase();
  const c=document.getElementById('cat').value;
  let n=0;
  document.querySelectorAll('.term').forEach(el=>{{
    const ok=(!q||el.dataset.txt.includes(q))&&(!c||el.dataset.cat===c);
    el.style.display=ok?'':'none'; if(ok)n++;
  }});
  document.getElementById('cnt').textContent='显示 '+n+' 条';
}}
applyFilter();
</script>
</body></html>"""

def scores_html():
    recs = load_scores()
    if not recs:
        body = "<p>还没有成绩记录。去做一套 <a href='/'>在线考试</a> 吧。</p>"
    else:
        rows = "".join(
            f'<div class="card"><span class="tag">{esc(r.get("name","?"))}</span> 得分 <b>{r.get("got",{}).get("total","?")}</b>'
            f' <span style="color:#888">选择{r.get("got",{}).get("choice","?")} 判断{r.get("got",{}).get("judge","?")} 填空{r.get("got",{}).get("fill","?")} 计算{r.get("got",{}).get("calc","?")}</span>'
            f' <span style="color:#aaa;font-size:12px">{r.get("ts","")}</span></div>'
            for r in reversed(recs[-30:])
        )
        body = rows
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>成绩记录</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/weak">弱项</a><a href="/feedback">反馈</a></nav>
<h1>成绩记录</h1>
{body}
</body></html>"""

def weak_html():
    recs = load_scores()
    if not recs:
        return "<h1>弱项分析</h1><p>还没有成绩数据，先做几套考试。</p>"
    agg = {}
    for r in recs:
        bank = r.get("bank_subset")
        detail = r.get("detail", {})
        if not bank:
            continue
        id2src = {}
        for sec in ("choice", "judge", "fill", "calc"):
            for it in bank.get(sec, []):
                id2src[it["id"]] = it.get("src", "")
        for sec in ("choice", "judge", "fill", "calc"):
            d = detail.get(sec, {})
            for qid, ok in d.items():
                kp = std_prefix(id2src.get(qid, ""))
                a = agg.setdefault(kp, [0, 0])
                if ok:
                    a[0] += 1
                else:
                    a[1] += 1
    if not agg:
        return "<h1>弱项分析</h1><p>成绩中无逐题明细，无法分析弱项。</p>"
    items = sorted(agg.items(), key=lambda x: (x[1][1] / max(1, sum(x[1])), -sum(x[1])), reverse=True)
    rows = "".join(
        f'<div class="card"><span class="tag">{esc(kp)}</span> 答对 {c} / 答错 {w} '
        f'（正确率 {round(100*c/max(1,c+w))}%）'
        f'{" ⚠️ 重点补强" if (w>0 and c/max(1,c+w)<0.7) else ""}</div>'
        for kp, (c, w) in items
    )
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>弱项分析</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/feedback">反馈</a></nav>
<h1>弱项分析</h1>
<div style="color:#666;font-size:14px">基于历史成绩逐题明细，按「答错率」排序，红字为建议重点补强的知识点。</div>
{rows}
</body></html>"""

def syllabus_html():
    sy = load_syllabus()
    if not sy:
        return "<h1>考试大纲</h1><p class=bad>未找到 materials/syllabus_2026.json</p>"
    meta = sy.get("meta", {})
    items = sy.get("items", [])
    # 按 part 分组
    parts = {}
    for it in items:
        parts.setdefault(it.get("part", "other"), []).append(it)
    legend = "<div class=card>认知层次权重（决定出卷抽题权重）：了解=1 · 熟悉=2 · 掌握=3 · 熟练掌握=4</div>"
    blocks = ""
    for part, its in parts.items():
        rows = "".join(
            f'<div class="card"><span class="tag">{esc(it.get("category",""))}</span> {esc(it.get("topic",""))}'
            f'<div style="color:#888;font-size:13px;margin-top:4px">{esc(it.get("requirement",""))}</div>'
            + (f'<div style="margin-top:4px"><span class="tag">认知:{esc(it.get("cognitive_level",""))}</span> {("".join("<span class=tag>"+esc(r)+"</span>" for r in it.get("ref_standards",[])))}</div>' if it.get("cognitive_level") else "")
            for it in its
        )
        blocks += f"<h2>{esc(part)}（{len(its)} 条）</h2>{rows}"
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>考试大纲 - 2026</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/scores">成绩</a><a href="/weak">弱项</a><a href="/feedback">反馈</a></nav>
<h1>考试大纲 · 2026 电器线缆检验职业技能竞赛</h1>
<div style="color:#666;font-size:14px">{esc(meta.get('org',''))} ｜ {esc(meta.get('code',''))} ｜ {esc(meta.get('notes',''))}</div>
{legend}
{blocks}
<footer>大纲为出卷权重真源：在「按权重出卷」页点「按考试大纲自动配权重」即可一键套用认知层次。</footer>
</body></html>"""

def feedback_html():
    recs = load_feedback()
    cats = FB_CATS
    stats = {s: sum(1 for r in recs if r["status"] == s) for s in FB_STATUS}
    stat_cards = " ".join(f'<div class="card" style="flex:1"><div class="score" style="font-size:20px">{stats[s]}</div><div style="color:#888">{s}</div></div>' for s in FB_STATUS)
    rows = "".join(
        f'''<tr data-cat="{esc(r['category'])}" data-status="{esc(r['status'])}">
<td>{r['id']}</td><td style="white-space:nowrap">{esc(r['created_at'])}</td><td>{esc(r.get('page',''))}</td>
<td>{esc(r['category'])}</td><td>{esc(r.get('location',''))}</td><td>{esc(r['detail'])}</td>
<td><span class="fb-status s-{esc(r['status'])}">{esc(r['status'])}</span></td>
<td>{esc(r.get('resolution','') or '—')}{('<br><span style="color:#888;font-size:12px">整改于 '+esc(r.get('resolved_at',''))+'</span>') if r.get('resolved_at') else ''}</td>
<td><button class="btn ghost" onclick="toggleResolve({r['id']})">整改</button>
<div id="res-{r['id']}" style="display:none;margin-top:6px">
<textarea id="resTxt-{r['id']}" rows=2 placeholder="整改说明…" style="width:100%">{esc(r.get('resolution',''))}</textarea>
<select id="resSt-{r['id']}"><option value="整改中">整改中</option><option value="已整改">已整改</option></select>
<button class="btn" onclick="saveResolve({r['id']})">保存</button></div></td></tr>'''
        for r in reversed(recs)
    )
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>反馈日志</title><style>{CSS}</style></head><body>
<nav><a href="/">首页</a><a href="/flashcards">闪卡库</a><a href="/terminology">术语库</a><a href="/syllabus">考试大纲</a><a href="/scores">成绩</a><a href="/weak">弱项</a></nav>
<h1>反馈整改日志</h1>
<div class="row">{stat_cards}</div>
<div class="card" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
  <div><select id=filterCat><option value="">全部类别</option>{''.join(f'<option>{esc(c)}</option>' for c in cats)}</select>
  <select id=filterStatus><option value="">全部状态</option>{''.join(f'<option>{esc(s)}</option>' for s in FB_STATUS)}</select></div>
  <a class="btn alt" href="/feedback/export.csv">⬇ 导出 CSV</a>
</div>
<p style="color:#888;font-size:13px">记录你对题库/题目/学习材料的反馈；整改后由我回填「整改说明」。悬右下角 📝 可随时提交新反馈。所有反馈同时写入 data/feedback.jsonl 与 data/feedback.log 形成日志。</p>
<table class="fb-tbl"><thead><tr><th>#</th><th>时间</th><th>页面</th><th>类别</th><th>对象</th><th>说明</th><th>状态</th><th>整改</th><th>操作</th></tr></thead>
<tbody>{rows or '<tr><td colspan=9 style="text-align:center;color:#999;padding:20px">暂无反馈</td></tr>'}</tbody></table>
<script>
function toggleResolve(id){{var e=document.getElementById('res-'+id);e.style.display=e.style.display==='none'?'block':'none';}}
function saveResolve(id){{
  var res=document.getElementById('resTxt-'+id).value.trim();
  var st=document.getElementById('resSt-'+id).value;
  fetch('/api/feedback/'+id+'/resolve',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{resolution:res,status:st}})}}).then(r=>r.json()).then(j=>{{if(j.ok)location.reload();else alert('保存失败');}});
}}
document.getElementById('filterCat').addEventListener('change',applyF);
document.getElementById('filterStatus').addEventListener('change',applyF);
function applyF(){{var c=document.getElementById('filterCat').value,s=document.getElementById('filterStatus').value;
  document.querySelectorAll('.fb-tbl tbody tr').forEach(tr=>{{tr.style.display=(!c||tr.dataset.cat===c)&&(!s||tr.dataset.status===s)?'':'none';}});}}
</script>
</body></html>"""

# ----------------------------------------------------------------------------
# 全局反馈 widget（注入所有 HTML 页）
FEEDBACK_WIDGET = """
<div class="fb-modal" id="fbModal"><div class="fb-box">
  <h2 style="margin-top:0">提交反馈</h2>
  <div style="font-size:12px;color:#888" id="fbPage"></div>
  <select id="fbCat">__FB_CATS__</select>
  <input id="fbLoc" placeholder="具体对象/位置（可空）">
  <textarea id="fbDetail" rows=4 placeholder="问题描述…"></textarea>
  <div class="row"><button class="btn" onclick="fbSubmit()">提交</button><button class="btn ghost" onclick="document.getElementById('fbModal').style.display='none'">取消</button></div>
</div></div>
<button class="fb-fab" title="提交反馈" onclick="fbOpen('',location.pathname)">📝</button>
<div class="sel-bubble" id="selBubble" onclick="fbSelSubmit()">反馈这段</div>
<script>
function fbOpen(initDetail, initLoc){{
  document.getElementById('fbDetail').value=initDetail||'';
  document.getElementById('fbLoc').value=initLoc||'';
  document.getElementById('fbPage').textContent='页面：'+(location.pathname);
  document.getElementById('fbModal').style.display='flex';
}}
function fbSubmit(){{
  var payload={{page:location.pathname,category:document.getElementById('fbCat').value,location:document.getElementById('fbLoc').value,detail:document.getElementById('fbDetail').value}};
  if(!payload.detail.trim()){{alert('请填写反馈内容');return;}}
  fetch('/api/feedback',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}}).then(r=>r.json()).then(j=>{{
    if(j.ok){{document.getElementById('fbModal').style.display='none';alert('已记录，感谢反馈！');}}else alert('提交失败');
  }});
}}
function fbSelSubmit(){{var b=document.getElementById('selBubble');fbOpen(b.dataset.txt, location.pathname+' 划词');b.style.display='none';}}
function openCardFb(card){{fbOpen('【闪卡反馈】'+JSON.stringify(card), location.pathname);}}
document.addEventListener('mouseup',function(e){{
  var sel=window.getSelection().toString().trim();var b=document.getElementById('selBubble');
  if(sel&&sel.length>1){{var r=window.getSelection().getRangeAt(0).getBoundingClientRect();b.style.display='block';b.style.left=(r.left+r.width/2-30)+'px';b.style.top=(r.top-38)+'px';b.dataset.txt=sel;}}else b.style.display='none';
}});
</script>
"""

def load_scores():
    if not os.path.isfile(SCORES):
        return []
    try:
        return json.load(open(SCORES, encoding="utf-8"))
    except Exception:
        return []

def save_score(rec):
    recs = load_scores()
    recs.append(rec)
    tmp = SCORES + ".tmp"
    json.dump(recs, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, SCORES)

# ----------------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            if "text/html" in ctype and "</body>" in body:
                body = body.replace("</body>", FEEDBACK_WIDGET + "\n</body>", 1)
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        q = urllib.parse.parse_qs(u.query)
        if path in ("/", ""):
            return self._send(200, dashboard_html())
        if path == "/builder":
            bank = q.get("bank", [list_banks()[0] if list_banks() else ""])[0]
            return self._send(200, builder_html(bank))
        if path == "/flashcards":
            deck = q.get("deck", [list_flashcard_decks()[0] if list_flashcard_decks() else ""])[0]
            mode = q.get("mode", ["browse"])[0]
            return self._send(200, flashcards_html(deck, mode))
        if path == "/terminology":
            f = q.get("file", [list_terminology()[0] if list_terminology() else ""])[0]
            return self._send(200, terminology_html(f))
        if path == "/syllabus":
            return self._send(200, syllabus_html())
        if path == "/scores":
            return self._send(200, scores_html())
        if path == "/weak":
            return self._send(200, weak_html())
        if path == "/feedback":
            return self._send(200, feedback_html())
        if path.startswith("/take/"):
            name = path[len("/take/"):]
            if name not in list_banks():
                return self._send(404, "题库不存在")
            return self._send(200, take_html(name))
        if path.startswith("/bank/"):
            name = path[len("/bank/"):]
            safe = "safe" in q
            bank = load_bank(name)
            if not bank:
                return self._send(404, "no bank")
            data = strip_answers(bank) if safe else bank
            return self._send(200, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/material/"):
            name = path[len("/material/"):]
            fp = os.path.join(MATERIALS, name + ".json")
            if not os.path.isfile(fp):
                return self._send(404, "no material")
            return self._send(200, open(fp, "rb").read(), "application/json; charset=utf-8")
        if path == "/feedback/export.csv":
            import csv
            recs = load_feedback()
            out = ["id,created_at,page,category,location,detail,status,resolution"]
            for r in recs:
                out.append(",".join('"' + str(r.get(k, "")).replace('"', '""') + '"' for k in ["id", "created_at", "page", "category", "location", "detail", "status", "resolution"]))
            return self._send(200, "\n".join(out), "text/csv; charset=utf-8")
        if path.startswith("/static/"):
            fn = os.path.basename(path)
            fp = os.path.join(ENGINE, fn)
            if not os.path.isfile(fp):
                return self._send(404, "no")
            return self._send(200, open(fp, "rb").read(), "application/javascript; charset=utf-8")
        if path.startswith("/exam/") or path.startswith("/study/"):
            fn = os.path.basename(path)
            fp = os.path.join(OUT, fn)
            if not os.path.isfile(fp):
                return self._send(404, "no")
            return self._send(200, open(fp, "rb").read())
        return self._send(404, "not found")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            payload = json.loads(raw)
        except Exception as e:
            return self._send(400, json.dumps({"error": str(e)}), "application/json")
        if u.path == "/api/grade":
            answers = payload.get("answers", {})
            inline = payload.get("inline")
            name = payload.get("bank", "")
            if inline:
                bank = inline
            else:
                bank = load_bank(name)
                if not bank:
                    return self._send(404, json.dumps({"error": "no bank"}), "application/json")
            res = generate.grade_all(bank, answers)
            save_score({
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "name": name if name else "(inline)",
                "got": res.get("got", {}),
                "detail": res.get("detail", {}),
                "bank_subset": bank,
            })
            return self._send(200, json.dumps(res, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path == "/api/build":
            name = payload.get("bank", "")
            kp_counts = payload.get("kp_counts", {})
            bank = load_bank(name)
            if not bank:
                return self._send(404, json.dumps({"error": "no bank"}), "application/json")
            out = {"meta": bank.get("meta", {}), "choice": [], "judge": [], "fill": [], "calc": []}
            for sec in ("choice", "judge", "fill", "calc"):
                by_kp = {}
                for it in bank.get(sec, []):
                    by_kp.setdefault(std_prefix(it.get("src", "")), []).append(it)
                for kp, want in kp_counts.items():
                    want = int(want or 0)
                    pool = by_kp.get(kp, [])
                    if want <= 0 or not pool:
                        continue
                    take = pool[:want] if want <= len(pool) else pool
                    out[sec].extend(take)
            total = 0
            for sec in ("choice", "judge", "fill", "calc"):
                for it in out[sec]:
                    total += int(it.get("points", it.get("point", 0)))
            out["meta"] = dict(out["meta"]); out["meta"]["total"] = total
            return self._send(200, json.dumps({"bank": out}, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path == "/api/exam_html":
            bank = payload.get("bank", {})
            return self._send(200, take_embedded_html(bank))
        if u.path == "/api/feedback":
            rec = add_feedback(payload)
            return self._send(200, json.dumps({"ok": True, "id": rec["id"]}, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path.startswith("/api/feedback/") and u.path.endswith("/resolve"):
            fid = int(u.path.split("/")[3])
            ok = resolve_feedback(fid, payload.get("resolution", ""), payload.get("status", "已整改"))
            return self._send(200, json.dumps({"ok": ok}, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path == "/api/flashcard_progress":
            deck = payload.get("deck", "")
            prog = payload.get("progress", {})
            data = load_fc_progress()
            data[deck] = prog
            save_fc_progress(data)
            return self._send(200, json.dumps({"ok": True}, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path == "/api/syllabus_weights":
            name = payload.get("bank", "")
            bank = load_bank(name)
            if not bank:
                return self._send(404, json.dumps({"error": "no bank"}), "application/json")
            sy = load_syllabus()
            if not sy:
                return self._send(404, json.dumps({"error": "no syllabus"}), "application/json")
            # 认知层次 → 权重
            cw = {"了解": 1, "熟悉": 2, "掌握": 3, "熟练掌握": 4}
            # 标准前缀 → 最大权重
            std_weight = {}
            for it in sy.get("items", []):
                lvl = it.get("cognitive_level")
                if not lvl:
                    continue
                w = cw.get(lvl, 1)
                for rs in it.get("ref_standards", []):
                    key = re.sub(r"[^A-Z0-9]", "", rs.upper())
                    std_weight[key] = max(std_weight.get(key, 0), w)
            kp_counts = {}
            for kp, cnt in group_by_kp(bank):
                kn = re.sub(r"[^A-Z0-9]", "", kp.upper())
                best = 0
                for key, w in std_weight.items():
                    if kn.startswith(key) or key.startswith(kn):
                        best = max(best, w)
                if best:
                    kp_counts[kp] = min(best, cnt)
            return self._send(200, json.dumps({"kp_counts": kp_counts}, ensure_ascii=False), "application/json; charset=utf-8")
        return self._send(404, "not found")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"国缆杯 v2 服务已启动: http://0.0.0.0:{PORT}")
        httpd.serve_forever()
