# -*- coding: utf-8 -*-
"""
渲染「可作答 + 自动判分」的离线试卷 HTML
==========================================
特点：
  - 单文件自包含，无 CDN、无网络依赖，双击即用，可直接发给同事。
  - 判分内核内联自 engine/grade.js（与 Python 判分逐条镜像，由 test_parity.py 保证一致）。
  - 只判客观题：选择 / 判断 / 填空 / 计算，规则化判分，不调用任何大模型。
  - 交卷后逐题给出对错、正确答案、解析、标准条款溯源。

注意：本文件为「离线自测卷」，答案内联在页面中（查看源码可见）。
      正式闭卷考试须走服务端判分（调用 generate.py 的 grade_all），不要用本文件。

用法：
  python render_exam.py ../rules/gbt_2951_kb_mvp.json
输出：
  ../out/<name>_exam.html
"""
import json, os, sys, html

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate import compute_score, self_check, zero_check

CSS = """
*{box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;max-width:920px;
     margin:0 auto;padding:24px 18px 80px;color:#1f2329;line-height:1.7;background:#f7f8fa}
h1{font-size:22px;margin:0 0 4px;border-left:5px solid #2f6fed;padding-left:12px}
.sub{color:#6b7280;font-size:13px;margin:0 0 16px;padding-left:17px}
.card{background:#fff;border:1px solid #e6e8eb;border-radius:10px;padding:16px 18px;margin:14px 0}
.info{background:#f0f5ff;border-color:#d6e2ff;font-size:13px;color:#334}
.info b{color:#2f6fed}
h2{font-size:17px;color:#2f6fed;margin:28px 0 10px;padding-bottom:6px;border-bottom:2px solid #e6ecfb}
.q{background:#fff;border:1px solid #e6e8eb;border-radius:10px;padding:14px 16px;margin:10px 0;
   transition:border-color .15s}
.q .stem{font-weight:600;color:#1f2329;margin-bottom:8px}
.q .pts{float:right;font-weight:400;font-size:12px;color:#9aa0a6}
.opt{display:block;margin:5px 0 5px 4px;cursor:pointer;padding:4px 8px;border-radius:6px}
.opt:hover{background:#f3f6ff}
.opt input{margin-right:8px}
.tf{display:inline-block;margin-right:10px;cursor:pointer;padding:5px 18px;border:1px solid #d9dde3;
    border-radius:20px;font-size:14px;background:#fff}
.tf:hover{border-color:#2f6fed;color:#2f6fed}
.tf input{display:none}
.tf.sel{background:#2f6fed;color:#fff;border-color:#2f6fed}
input[type=text]{border:none;border-bottom:1.5px solid #b9c0c9;background:transparent;
   padding:2px 6px;min-width:96px;font-size:14px;font-family:inherit;color:#0b57d0;text-align:center}
input[type=text]:focus{outline:none;border-bottom-color:#2f6fed;background:#f5f8ff}
.calcsub{margin:6px 0 6px 6px;font-size:14px}
.calcsub .lb{display:inline-block;min-width:230px;color:#444}
.res{margin-top:10px;font-size:13px;padding:8px 12px;border-radius:6px;display:none}
.res.ok{background:#e9f7ef;color:#12703a;border-left:3px solid #16894a}
.res.bad{background:#fdecec;color:#a5281b;border-left:3px solid #d93025}
.res .src{color:#6b7280;font-size:12px;margin-top:4px}
.bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #e0e3e8;
     padding:12px 18px;display:flex;gap:12px;align-items:center;justify-content:center;
     box-shadow:0 -2px 12px rgba(0,0,0,.06);z-index:20}
button{font-family:inherit;font-size:15px;padding:9px 30px;border-radius:8px;cursor:pointer;border:1px solid transparent}
.btn-main{background:#2f6fed;color:#fff}
.btn-main:hover{background:#1a5bd6}
.btn-sec{background:#fff;color:#444;border-color:#d9dde3}
.btn-sec:hover{border-color:#2f6fed;color:#2f6fed}
#score{font-size:15px;font-weight:600;color:#1f2329}
#score .n{font-size:24px;color:#2f6fed;margin:0 3px}
.sheet{display:none;background:#fff;border:1px solid #e6e8eb;border-radius:10px;padding:14px 18px;margin:14px 0}
.sheet h3{margin:0 0 8px;font-size:15px}
.sheet .row{font-size:13px;color:#444;margin:3px 0}
"""

JS_MAIN = """
var BANK = __BANK__;

function collect(){
  var a = {choice:{}, judge:{}, fill:{}, calc:{}};
  (BANK.choice||[]).forEach(function(it){
    var el = document.querySelector('input[name="c_'+it.id+'"]:checked');
    a.choice[it.id] = el ? el.value : "";
  });
  (BANK.judge||[]).forEach(function(it){
    var el = document.querySelector('input[name="j_'+it.id+'"]:checked');
    a.judge[it.id] = el ? el.value : "";
  });
  (BANK.fill||[]).forEach(function(it){
    a.fill[it.id] = it.answers.map(function(_,i){
      var el = document.getElementById('f_'+it.id+'_'+i); return el ? el.value : "";
    });
  });
  (BANK.calc||[]).forEach(function(it){
    a.calc[it.id] = it.subs.map(function(_,i){
      var el = document.getElementById('k_'+it.id+'_'+i); return el ? el.value : "";
    });
  });
  return a;
}

function fmtAns(t, it){
  if(t==='choice') return String.fromCharCode(65+parseInt(it.answer,10)) + '. ' + it.options[it.answer];
  if(t==='judge')  return it.answer ? '对 √' : '错 ×';
  if(t==='fill')   return it.answers.join('  /  ');
  if(t==='calc')   return it.subs.map(function(s){return s[0]+'='+s[1];}).join('；');
  return '';
}

function submit(){
  var ans = collect();
  var r = Grade.gradeAll(BANK, ans);
  var full = 0, rows = [];
  ['choice','judge','fill','calc'].forEach(function(t){
    (BANK[t]||[]).forEach(function(it){
      var max = (t==='calc') ? it.subs.reduce(function(x,s){return x+s[3];},0)
                             : (it.points===undefined ? (t==='judge'?1:2) : it.points);
      full += max;
      var got = r.detail[t][it.id];
      var box = document.getElementById('res_'+it.id);
      var okAll = got === max;
      box.className = 'res ' + (okAll ? 'ok' : (got>0 ? 'ok' : 'bad'));
      box.style.display = 'block';
      box.innerHTML = '<b>' + (okAll?'✓ 正确':(got>0?'△ 部分正确':'✗ 错误')) + '　得分 '+got+'/'+max+'</b>'
        + '<div>正确答案：' + fmtAns(t,it).replace(/</g,'&lt;') + '</div>'
        + (it.explain ? '<div>解析：'+it.explain.replace(/</g,'&lt;')+'</div>' : '')
        + (it.src ? '<div class="src">来源：'+it.src.replace(/</g,'&lt;')+'</div>' : '');
      document.getElementById('q_'+it.id).style.borderColor = okAll ? '#9bd8b4' : (got>0 ? '#f3d19e' : '#f0b3ae');
      rows.push({t:t,id:it.id,got:got,max:max});
    });
  });
  var pct = full ? Math.round(r.got.total/full*1000)/10 : 0;
  document.getElementById('score').innerHTML =
    '得分 <span class="n">'+r.got.total+'</span>/ '+full+'　（'+pct+'%）'+
    '　选择'+r.got.choice+' 判断'+r.got.judge+' 填空'+r.got.fill+' 计算'+r.got.calc;
  var wrong = rows.filter(function(x){return x.got < x.max;});
  var sh = document.getElementById('sheet');
  sh.style.display='block';
  sh.innerHTML = '<h3>错题清单（'+wrong.length+' 题）</h3>' +
    (wrong.length ? wrong.map(function(x){
        return '<div class="row">· '+x.id+'　得 '+x.got+'/'+x.max+'　<a href="#q_'+x.id+'">定位</a></div>';
      }).join('') : '<div class="row">全部正确，满分通过。</div>');
  window.scrollTo({top:0, behavior:'smooth'});
}

function reset(){
  document.querySelectorAll('input[type=radio]').forEach(function(e){e.checked=false;});
  document.querySelectorAll('input[type=text]').forEach(function(e){e.value='';});
  document.querySelectorAll('.res').forEach(function(e){e.style.display='none';});
  document.querySelectorAll('.q').forEach(function(e){e.style.borderColor='#e6e8eb';});
  document.querySelectorAll('.tf').forEach(function(e){e.classList.remove('sel');});
  document.getElementById('score').innerHTML='未交卷';
  document.getElementById('sheet').style.display='none';
  window.scrollTo({top:0,behavior:'smooth'});
}

document.addEventListener('change', function(e){
  if(e.target.type==='radio' && e.target.name.indexOf('j_')===0){
    document.querySelectorAll('input[name="'+e.target.name+'"]').forEach(function(r){
      r.parentNode.classList.remove('sel');
    });
    e.target.parentNode.classList.add('sel');
  }
});

var t0 = Date.now();
setInterval(function(){
  var s = Math.floor((Date.now()-t0)/1000);
  document.getElementById('timer').textContent =
    '用时 ' + String(Math.floor(s/60)).padStart(2,'0') + ':' + String(s%60).padStart(2,'0');
}, 1000);
"""


def esc(s):
    return html.escape(str(s), quote=False)


def render(bank, name):
    score = compute_score(bank)
    chk = self_check(bank)
    zero = zero_check(bank)
    std = "　·　".join(bank.get("meta", {}).get("standard", ["未命名"]))
    grade_js = open(os.path.join(HERE, "grade.js"), encoding="utf-8").read()
    bank_js = json.dumps(bank, ensure_ascii=False).replace("</", "<\\/")

    p = []
    p.append(f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>在线自测卷 · {esc(name)}</title><style>{CSS}</style></head><body>
<h1>国缆检测杯 · 标准条款自测卷</h1>
<p class="sub">{esc(std)}</p>
<div class="card info">
  <b>总分 {score['total']} 分</b>｜选择 {len(bank.get('choice',[]))} 题 {score['choice']} 分
  ｜判断 {len(bank.get('judge',[]))} 题 {score['judge']} 分
  ｜填空 {len(bank.get('fill',[]))} 题 {score['fill']} 分
  ｜计算 {len(bank.get('calc',[]))} 题 {score['calc']} 分<br>
  题目来源：{esc(bank.get('meta',{}).get('source',''))}<br>
  判分方式：<b>纯脚本规则判分</b>（不调用大模型）；满分自检 {'PASS' if chk[2] else 'FAIL'}、
  零分自检 {'PASS' if zero==0 else 'FAIL'}；Python/JS 判分一致性已由 test_parity.py 验证。<br>
  填空题需<b>整题全部空都答对</b>才得分；数值题按容差判定；答案支持常见近义写法与空格/全角容错。
</div>
<div id="sheet" class="sheet"></div>""")

    if bank.get("choice"):
        p.append("<h2>一、单项选择题</h2>")
        for n, it in enumerate(bank["choice"], 1):
            opts = "".join(
                f'<label class="opt"><input type="radio" name="c_{it["id"]}" value="{i}">'
                f'{chr(65+i)}. {esc(o)}</label>' for i, o in enumerate(it["options"]))
            p.append(f'<div class="q" id="q_{it["id"]}"><div class="stem">'
                     f'<span class="pts">{it.get("points",2)}分</span>{n}. {esc(it["q"])}</div>'
                     f'{opts}<div class="res" id="res_{it["id"]}"></div></div>')

    if bank.get("judge"):
        p.append("<h2>二、判断题（正确画 √ ，错误画 ×）</h2>")
        for n, it in enumerate(bank["judge"], 1):
            p.append(f'<div class="q" id="q_{it["id"]}"><div class="stem">'
                     f'<span class="pts">{it.get("points",1)}分</span>{n}. {esc(it["q"])}</div>'
                     f'<label class="tf"><input type="radio" name="j_{it["id"]}" value="true">√ 对</label>'
                     f'<label class="tf"><input type="radio" name="j_{it["id"]}" value="false">× 错</label>'
                     f'<div class="res" id="res_{it["id"]}"></div></div>')

    if bank.get("fill"):
        p.append("<h2>三、填空题</h2>")
        for n, it in enumerate(bank["fill"], 1):
            parts_q, idx = [], 0
            for seg in esc(it["q"]).split("____"):
                parts_q.append(seg)
                if idx < len(it["answers"]):
                    parts_q.append(f'<input type="text" id="f_{it["id"]}_{idx}">')
                    idx += 1
            stem = "".join(parts_q)
            # 题干里 ____ 数量不足时，补齐输入框
            while idx < len(it["answers"]):
                stem += f' 　填空{idx+1}：<input type="text" id="f_{it["id"]}_{idx}">'
                idx += 1
            p.append(f'<div class="q" id="q_{it["id"]}"><div class="stem">'
                     f'<span class="pts">{it.get("points",2)}分</span>{n}. {stem}</div>'
                     f'<div class="res" id="res_{it["id"]}"></div></div>')

    if bank.get("calc"):
        p.append("<h2>四、计算与判定题</h2>")
        for n, it in enumerate(bank["calc"], 1):
            tot = sum(s[3] for s in it["subs"])
            subs = "".join(
                f'<div class="calcsub"><span class="lb">（{i+1}）{esc(s[0])}</span>'
                f'<input type="text" id="k_{it["id"]}_{i}">　<span style="color:#9aa0a6;font-size:12px">'
                f'{s[3]}分{("，容差±"+str(s[2])) if s[0]!="合格性判定" and s[2] else ""}</span></div>'
                for i, s in enumerate(it["subs"]))
            p.append(f'<div class="q" id="q_{it["id"]}"><div class="stem">'
                     f'<span class="pts">{tot}分</span>{n}. {esc(it["title"])}</div>'
                     f'<div style="color:#444;font-size:14px;margin-bottom:8px">{esc(it["stem"])}</div>'
                     f'{subs}<div class="res" id="res_{it["id"]}"></div></div>')

    p.append(f"""
<div class="bar">
  <span id="timer" style="color:#6b7280;font-size:13px">用时 00:00</span>
  <button class="btn-main" onclick="submit()">交卷判分</button>
  <button class="btn-sec" onclick="reset()">重做</button>
  <span id="score">未交卷</span>
</div>
<script>{grade_js}</script>
<script>{JS_MAIN.replace("__BANK__", bank_js)}</script>
</body></html>""")
    return "\n".join(p)


def main():
    rule = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "rules", "gbt_2951_kb_mvp.json")
    bank = json.load(open(rule, encoding="utf-8"))
    name = os.path.splitext(os.path.basename(rule))[0]
    out_dir = os.path.join(os.path.dirname(HERE), "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}_exam.html")
    open(path, "w", encoding="utf-8").write(render(bank, name))
    print(f"[OK] 可作答试卷 -> {path}")
    print(f"     大小 {os.path.getsize(path)/1024:.1f} KB（自包含，离线可用）")


if __name__ == "__main__":
    main()
