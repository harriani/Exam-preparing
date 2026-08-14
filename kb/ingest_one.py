# -*- coding: utf-8 -*-
"""把单个标准 PDF 经 doc2kb OCR 解析后增量写入 kb.db（安全 INSERT，不动已有文档）。
用法: python kb/ingest_one.py <code>   # code 如 18890.1 / 5023.3 / 2951.11
"""
import os, sys, subprocess, glob, sqlite3

DOC2KB = r"C:/Users/ZT-052382/.workbuddy/skills/doc2kb/scripts/parse_document.py"
PY = r"C:/Users/ZT-052382/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "_build_kb.py")
SRC = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准"
OUT = os.path.join(ROOT, "kb", "raw")
DB = os.path.join(ROOT, "kb", "kb.db")
os.makedirs(OUT, exist_ok=True)

code = sys.argv[1]
hits = glob.glob(os.path.join(SRC, f"*{code}*.pdf"))
if not hits:
    print("NOT FOUND:", code); sys.exit(2)
src = hits[0]
out = os.path.join(OUT, f"pages_{code}.json")

print(f"[1/2] OCR 解析 {os.path.basename(src)}", flush=True)
r = subprocess.run([PY, DOC2KB, src, "--ocr", "auto", "--formula", "degrade", "--out", out],
                   capture_output=True, text=True, timeout=1800)
print((r.stdout or "")[-400:], file=sys.stderr)
print((r.stderr or "")[-400:], file=sys.stderr)
print("  parse rc=", r.returncode, "out_size=", os.path.getsize(out) if os.path.exists(out) else 0, flush=True)
if not os.path.exists(out):
    print("解析失败，中止"); sys.exit(1)

print(f"[2/2] 写入 kb.db ({os.path.basename(out)})", flush=True)
r2 = subprocess.run([PY, BUILD, out, "--db", DB, "--ku-mode", "exam", "--normative", "strict", "--chunk", "clause"],
                    capture_output=True, text=True, timeout=600)
print((r2.stdout or "")[-400:], file=sys.stderr)
print((r2.stderr or "")[-400:], file=sys.stderr)
print("  build rc=", r2.returncode, flush=True)

c = sqlite3.connect(DB)
print("  documents 总数:", c.execute("SELECT COUNT(*) FROM documents").fetchone()[0], flush=True)
for t in c.execute("SELECT id,title FROM documents WHERE title LIKE ?", (f"%{code}%",)):
    print("   +新增:", t, flush=True)
