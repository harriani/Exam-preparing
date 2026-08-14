import os, sys, subprocess

DOC2KB = r"C:/Users/ZT-052382/.workbuddy/skills/doc2kb/scripts/parse_document.py"
PY = r"C:/Users/ZT-052382/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SRC = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准"
OUT = r"F:/WorkBuddy/2026-08-04-11-22-11/learning-system-v2/kb/raw"

# 文本型（pdfplumber 直接抽）
TEXT = ["3048.1","3048.3","3048.7","3048.8","3048.9","3048.10","3048.11","3048.13"]
# 扫描件新增（Docling OCR）：2951 新增3 + 3048 扫描4 + 3956
OCR  = ["2951.41","2951.42","2951.51","3048.2","3048.12","3048.14","3048.16","3956"]

def find_file(code):
    t = code + '-'
    for f in os.listdir(SRC):
        if f.lower().endswith('.pdf') and t in f:
            return os.path.join(SRC, f)
    return None

mode = sys.argv[1]
codes = TEXT if mode == 'text' else OCR
for code in codes:
    src = find_file(code)
    if not src:
        print("SKIP not found:", code, flush=True); continue
    out = os.path.join(OUT, f"pages_{code}.json")
    ocr_flag = 'off' if mode == 'text' else 'auto'
    cmd = [PY, DOC2KB, src, '--ocr', ocr_flag, '--formula', 'degrade', '--out', out]
    print(f"=== {code} ({ocr_flag}) <- {os.path.basename(src)[:36]} ===", flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        tail = (r.stdout or '')[-200:] + '\n' + (r.stderr or '')[-200:]
        print(tail, flush=True)
        print(f"rc={r.returncode} out_size={os.path.getsize(out) if os.path.exists(out) else 0}", flush=True)
    except subprocess.TimeoutExpired:
        print("TIMEOUT", code, flush=True)
print("DONE mode=", mode, flush=True)
