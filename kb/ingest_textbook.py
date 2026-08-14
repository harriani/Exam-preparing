# -*- coding: utf-8 -*-
"""
ingest_textbook.py — 把两本教材（电缆产品检验-电性能检验 / 非电性能检验）的 Word 原稿
用 zipfile 抽取正文（无需 OCR，数字文档），生成与 _build_kb.py 兼容的 pages_*.json，
再增量写入 kb.db，补齐「书籍教材」这一资料层。

用法：python kb/ingest_textbook.py
"""
import os, re, json, glob, subprocess, sqlite3
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "_build_kb.py")
OUT = os.path.join(ROOT, "kb", "raw")
DB = os.path.join(ROOT, "kb", "kb.db")
BASE = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯"


def find_docx(key):
    hits = glob.glob(os.path.join(BASE, "**", f"*{key}*.docx"), recursive=True)
    # 优先 3_标准word版 的原稿
    for h in hits:
        if "3_标准word版" in h:
            return h
    return hits[0] if hits else None


def extract_docx_text(path):
    """返回按段落切分的纯文本列表（保留换行，供 clause 切块）。"""
    paras = []
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    # 段落：<w:p ...> ... </w:p>
    for pm in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.S):
        seg = pm.group(0)
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", seg, re.S)
        line = "".join(texts)
        line = re.sub(r"<[^>]+>", "", line)          # 去残余标签
        line = line.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        paras.append(line)
    return [p.strip() for p in paras]


def to_pages(paras, lines_per_page=90):
    pages, buf, pn = [], [], 1
    for p in paras:
        buf.append(p)
        if len(buf) >= lines_per_page:
            pages.append({"page_no": pn, "text": "\n".join(buf)})
            buf, pn = [], pn + 1
    if buf:
        pages.append({"page_no": pn, "text": "\n".join(buf)})
    return pages


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = [
        ("电性能检验", "电缆产品检验-电性能检验"),
        ("非电性能检验", "电缆产品检验-非电性能检验"),
    ]
    for key, label in targets:
        src = find_docx(label)
        if not src:
            print("未找到教材:", label)
            continue
        print(f"[1/3] 抽取 {os.path.basename(src)}", flush=True)
        paras = extract_docx_text(src)
        pages = to_pages(paras)
        out = os.path.join(OUT, f"pages_textbook_{key}.json")
        json.dump({"source": src, "method": "docx-text", "pages": pages},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"     段落={len(paras)} 生成页={len(pages)} -> {os.path.basename(out)}", flush=True)

        print(f"[2/3] 写入 kb.db", flush=True)
        r = subprocess.run(["python", BUILD, out, "--db", DB, "--ku-mode", "exam",
                            "--normative", "strict", "--chunk", "clause"],
                           capture_output=True, text=True)
        print((r.stdout or "").strip()[-300:], file=__import__("sys").stderr)
        print((r.stderr or "").strip()[-300:], file=__import__("sys").stderr)

        c = sqlite3.connect(DB)
        for t in c.execute("SELECT id,title FROM documents WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
                           (f"%{label}%",)):
            print("   +新增文档:", t, flush=True)

    print("[3/3] 完成。随后请运行 python kb/build_links.py 接入大纲链接。")


if __name__ == "__main__":
    main()
