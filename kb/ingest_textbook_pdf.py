# -*- coding: utf-8 -*-
"""
ingest_textbook_pdf.py — 用 doc2kb(OCR/文本层) 把两本教材 PDF 解析为 pages_*.json，
再增量写入 kb.db，补齐「书籍教材」资料层。
（.docx 原稿为 WPS 私有封装无法直接解，故走 PDF 文本层抽取。）
用法：python kb/ingest_textbook_pdf.py
"""
import os, glob, subprocess, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC2KB = r"C:/Users/ZT-052382/.workbuddy/skills/doc2kb/scripts/parse_document.py"
PY = r"C:/Users/ZT-052382/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SRC = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准"
OUT = os.path.join(ROOT, "kb", "raw")
BUILD = os.path.join(ROOT, "_build_kb.py")
DB = os.path.join(ROOT, "kb", "kb.db")


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = [
        ("电性能检验", "电缆产品检验-电性能检验"),
        ("非电性能检验", "电缆产品检验-非电性能检验"),
    ]
    for key, label in targets:
        hits = glob.glob(os.path.join(SRC, f"*{label}*.pdf"))
        if not hits:
            print("NOT FOUND:", label, flush=True)
            continue
        src = hits[0]
        out = os.path.join(OUT, f"pages_textbook_{key}.json")
        print(f"[1/2] OCR/解析 {os.path.basename(src)}", flush=True)
        r = subprocess.run([PY, DOC2KB, src, "--ocr", "auto", "--formula", "degrade", "--out", out],
                           capture_output=True, text=True, timeout=2400)
        print((r.stdout or "")[-300:], file=sys.stderr)
        print((r.stderr or "")[-300:], file=sys.stderr)
        if not os.path.exists(out):
            print("解析失败，跳过", label, flush=True)
            continue
        print(f"     out_size={os.path.getsize(out)}", flush=True)
        print(f"[2/2] 写入 kb.db", flush=True)
        r2 = subprocess.run([PY, BUILD, out, "--db", DB, "--ku-mode", "exam",
                             "--normative", "strict", "--chunk", "clause"],
                            capture_output=True, text=True, timeout=600)
        print((r2.stdout or "")[-300:], file=sys.stderr)
        print((r2.stderr or "")[-300:], file=sys.stderr)
        c = sqlite3.connect(DB)
        for t in c.execute("SELECT id,title FROM documents WHERE title LIKE ? ORDER BY id DESC LIMIT 1", (f"%{label}%",)):
            print("   +新增文档:", t, flush=True)
    print("[done] 教材入库完成，请运行 python kb/build_links.py 接入大纲链接。")


if __name__ == "__main__":
    main()
