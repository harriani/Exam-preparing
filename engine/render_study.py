#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_study.py — 学习材料(LLM 产出的 materials/*.json)的【纯展示】渲染壳。
仅做 HTML 呈现，不含任何"生成/理解/出题"逻辑。生成侧=LLM，本文件=浏览器。
用法: python engine/render_study.py materials/<name>.json out/<name>_study.html
"""
import json, sys, html

def esc(s):
    return html.escape(str(s), quote=True)

def render_card(c):
    fid = abs(hash(c.get("ku_id", "") + c.get("front", ""))) % 100000
    return f'''
    <div class="card">
      <div class="card-h">闪卡 · <span class="src">{esc(c.get('src',''))}</span></div>
      <div class="flash" onclick="this.classList.toggle('flipped')">
        <div class="face front">{esc(c.get('front',''))}</div>
        <div class="face back">{esc(c.get('back',''))}</div>
      </div>
    </div>'''

def render_table(t):
    rows = "".join(
        "<tr>" + "".join(f"<td>{esc(x)}</td>" for x in r) + "</tr>"
        for r in t.get("rows", [])
    )
    head = "".join(f"<th>{esc(x)}</th>" for x in t.get("columns", []))
    note = f'<div class="note">注：{esc(t["note"])}</div>' if t.get("note") else ""
    return f'''
    <div class="card">
      <div class="card-h">参数表 · {esc(t.get("title",""))} · <span class="src">{esc(t.get("src",""))}</span></div>
      <table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>
      {note}
    </div>'''

def render_quiz(q):
    return f'''
    <div class="card">
      <div class="card-h">自测 · <span class="src">{esc(q.get('src',''))}</span></div>
      <div class="q">{esc(q.get('q',''))}</div>
      <button onclick="reveal(this)">显示答案</button>
      <div class="ans" style="display:none">{esc(q.get('a',''))}
        <div class="explain">{esc(q.get('explain',''))}</div>
      </div>
    </div>'''

def render_pitfall(p):
    return f'''
    <div class="card pit">
      <div class="card-h">易错点 · <span class="src">{esc(p.get('src',''))}</span></div>
      <div class="bad">✗ {esc(p.get('desc',''))}</div>
      <div class="good">✓ {esc(p.get('correct',''))}</div>
    </div>'''

def render_summary(s):
    return f'<div class="summary"><b>{esc(s.get("title",""))}</b><p>{esc(s.get("body",""))}</p></div>'

def main():
    if len(sys.argv) < 3:
        print("usage: render_study.py <materials.json> <out.html>")
        sys.exit(1)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    body = render_summary({"title": data.get("standard_family",""), "body": data.get("generated_from","") + " ｜ " + data.get("src_rule","")})
    for sec in data.get("sections", []):
        t = sec.get("type")
        if t == "summary":
            body += render_summary(sec)
        elif t == "flashcard":
            body += render_card(sec)
        elif t == "key_table":
            body += render_table(sec)
        elif t == "quiz":
            body += render_quiz(sec)
        elif t == "pitfall":
            body += render_pitfall(sec)
    html_doc = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get("standard_family",""))} · 学习材料</title>
<style>
*{{box-sizing:border-box}} body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f5f6f8;color:#1f2329}}
.wrap{{max-width:860px;margin:0 auto;padding:24px}}
h1{{font-size:20px;margin:0 0 16px}}
.summary{{background:#fff;border-left:4px solid #2f6fed;padding:14px 16px;border-radius:8px;margin-bottom:18px}}
.card{{background:#fff;border-radius:10px;padding:16px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card-h{{font-size:13px;color:#6b7280;margin-bottom:10px}}
.src{{color:#2f6fed}}
.flash{{cursor:pointer;min-height:64px}}
.face{{padding:14px;border-radius:8px;border:1px solid #e5e7eb}}
.front{{background:#fafbff}}
.back{{display:none;background:#eef6ee;border-color:#bfe3bf;margin-top:8px}}
.flash.flipped .front{{display:none}}
.flash.flipped .back{{display:block}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #e5e7eb;padding:8px 10px;text-align:center}}
th{{background:#f0f3ff}}
.note{{font-size:12px;color:#6b7280;margin-top:8px}}
.q{{font-size:15px;margin-bottom:10px}}
button{{background:#2f6fed;color:#fff;border:0;border-radius:6px;padding:7px 14px;cursor:pointer;font-size:13px}}
.ans{{margin-top:10px;background:#eef6ee;border-radius:8px;padding:12px}}
.explain{{font-size:12px;color:#555;margin-top:8px}}
.pit .bad{{background:#fdecec;color:#b42318;border-radius:6px;padding:8px}}
.pit .good{{background:#eafaf0;color:#067647;border-radius:6px;padding:8px;margin-top:8px}}
</style></head><body><div class="wrap"><h1>{esc(data.get("standard_family",""))} · 学习材料</h1>{body}
<script>
function reveal(b){{var a=b.nextElementSibling;a.style.display='block';b.style.display='none';}}
</script></div></body></html>'''
    open(sys.argv[2], "w", encoding="utf-8").write(html_doc)
    print("written:", sys.argv[2])

if __name__ == "__main__":
    main()
