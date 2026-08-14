# -*- coding: utf-8 -*-
"""把 raw/pages_*.json 中「kb.db 尚未收录」的标准批量写入 kb.db（仅 _build_kb，不重新 OCR）。
OCR 产物 pages_*.json 此前已生成，故本步很快。18890.1 交给后台验证任务，这里跳过以免并发重复写。
用法: python kb/ingest_missing_build.py
"""
import os, re, subprocess, sqlite3, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.path.join(ROOT, "kb", "kb.db")
BUILD = os.path.join(ROOT, "_build_kb.py")
PY   = r"C:/Users/ZT-052382/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
RAW  = os.path.join(ROOT, "kb", "raw")

def code_of(fn):
    m = re.search(r"pages_(.+)\.json$", fn)
    return m.group(1) if m else None

c = sqlite3.connect(DB)
def has(code):
    return c.execute("SELECT COUNT(*) FROM documents WHERE title LIKE ?", ('%'+code+'%',)).fetchone()[0] > 0

files = sorted(glob.glob(os.path.join(RAW, "pages_*.json")))
done = skip = fail = 0
for f in files:
    code = code_of(os.path.basename(f))
    if not code:
        continue
    if code == "18890.1":          # 留给后台验证任务，避免并发重复写
        print("SKIP (后台处理中):", code, flush=True); skip += 1; continue
    if has(code):
        print("SKIP (已有):", code, flush=True); skip += 1; continue
    size = os.path.getsize(f)
    if size < 2000:                # OCR 疑似失败产物，跳过，事后单独重抽
        print("SKIP (OCR可能失败, %dB):" % size, code, flush=True); skip += 1; continue
    print("BUILD:", code, flush=True)
    r = subprocess.run([PY, BUILD, f, "--db", DB, "--ku-mode", "exam",
                        "--normative", "strict", "--chunk", "clause"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        done += 1
        print("  OK", code, flush=True)
    else:
        fail += 1
        print("  FAIL", code, (r.stderr or "")[-300:], flush=True)

print(f"\n=== 完成: 新增 {done}, 跳过 {skip}, 失败 {fail} ===", flush=True)
