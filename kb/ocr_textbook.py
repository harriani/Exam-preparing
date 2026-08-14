# -*- coding: utf-8 -*-
"""
ocr_textbook.py — 把两本教材（扫描图片版 PDF，无文本层）用本地 RapidOCR 离线
识别，走 _build_kb 流程写入 kb.db。无需联网，不依赖被代理拦截的云端 OCR。

教材是数字扫描版：fitz 渲染页面为图片 -> RapidOCR 抽取文字 -> 存 pages json ->
build_kb(读文件) 切块 -> write_sqlite 落库。文档标题取自 PDF 文件名（含
「电缆产品检验」「电性能/非电性能」），供 build_links.py 识别为教材层并接入大纲。

断点续跑：每本教材先把 OCR 结果写到 kb/raw/pages_textbook_*.json；若文件已存在
则直接加载，跳过 OCR（崩了重跑不浪费）。落库后再删除该缓存文件。
幂等：documents 已存在同名教材则整本跳过。
用法：python kb/ocr_textbook.py
"""
import os, sys, io, re, json, time
import sqlite3
import fitz
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception as e:
    print("[fatal] rapidocr_onnxruntime 不可用：", e, file=sys.stderr); sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from _build_kb import build_kb, write_sqlite

DB = os.path.join(ROOT, "kb", "kb.db")
RAW = os.path.join(ROOT, "kb", "raw")
SRC_DIR = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准"
BOOKS = [
    ("电缆产品检验-电性能检验 (李骥 陈志刚 主编).pdf", "GB/T 3048 电线电缆电性能试验方法"),
    ("电缆产品检验-非电性能检验 (肖继东 主编).pdf", "GB/T 2951 电缆绝缘和护套材料通用试验方法"),
]
DPI = 200


def _slug(fname):
    return "pages_textbook_" + re.sub(r'[^\w一-鿿]+', '_', os.path.splitext(fname)[0]) + ".json"


def book_already(db, src_basename):
    c = db.cursor()
    c.execute("SELECT id FROM documents WHERE title=?", (src_basename,))
    return c.fetchone()


def ocr_pages(pdf_path, cache_path):
    # 断点续跑：缓存文件已存在则直接加载
    if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 1:
        print(f"  [resume] 加载缓存 {os.path.basename(cache_path)}", file=sys.stderr)
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f).get("pages", [])
    doc = fitz.open(pdf_path)
    n = doc.page_count
    pages = []
    t0 = time.time()
    for i in range(n):
        pg = doc[i]
        pix = pg.get_pixmap(dpi=DPI)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO(); img.save(buf, "PNG"); png = buf.getvalue()
        res, _ = ocr(png)
        text = "\n".join(r[1] for r in res) if res else ""
        pages.append({"page_no": i + 1, "text": text})
        if (i + 1) % 20 == 0:
            el = time.time() - t0
            print(f"  OCR 进度 {i+1}/{n}  已用 {el:.0f}s ({(el/(i+1)):.1f}s/页)", file=sys.stderr)
    doc.close()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"source": fname, "method": method, "pages": pages}, f, ensure_ascii=False)
    print(f"  [cache] 已写 {os.path.basename(cache_path)} ({len(pages)} 页)", file=sys.stderr)
    return pages


def main():
    global ocr
    ocr = RapidOCR()
    db = sqlite3.connect(DB)
    for fname, method in BOOKS:
        pdf = os.path.join(SRC_DIR, fname)
        if not os.path.isfile(pdf):
            print("[skip] 找不到", pdf, file=sys.stderr); continue
        if book_already(db, fname):
            print(f"[skip] 已入库：{fname}", file=sys.stderr); continue
        cache_path = os.path.join(RAW, _slug(fname))
        print(f"\n=== OCR 教材：{fname} ===", file=sys.stderr)
        pages = ocr_pages(pdf, cache_path)
        nonempty = sum(1 for p in pages if p["text"].strip())
        print(f"  渲染+OCR 完成：{len(pages)} 页，非空 {nonempty} 页", file=sys.stderr)
        # build_kb 吃文件路径
        kb = build_kb(cache_path,
                      normative_mode="off", chunk_mode="clause", make_ku=True, ku_mode="generic")
        write_sqlite(kb, DB)
        print(f"  落库完成：sections={len(kb['sections'])} units={len(kb['units'])} doc='{kb['document']['title']}'",
              file=sys.stderr)
        # 落库成功后清理缓存，避免重复占用磁盘
        try:
            os.remove(cache_path)
        except OSError:
            pass
    db.close()
    print("\n[done] 教材 OCR 入库结束", file=sys.stderr)


if __name__ == "__main__":
    main()
