#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发分批 OCR 教材（扫描件）-> pages_textbook_elec.json

设计目标（修复 doc2kb 主流程"整本跑完才一次性写 json、中途崩溃零产出"的缺陷）：
  - 调 doc2kb 内部单页模式 --_page N，逐页独立 OCR
  - 每页成功即 flush 到 pages json（断点续跑，崩溃不丢已完成页）
  - 单实例锁：run_in_background 双启动壳时，第二个实例立即退出，避免抢写同一文件
  - 并发 4（docling 单页 ~1GB，留足内存余量），单页超时 200s、失败重试 1 次
产出格式与 doc2kb 主流程一致：{"source","method":"docling_pdf","pages":[{"page_no","text"}]}
ingest 重跑时 stage_ocr 检测到该文件非空 -> SKIP，直接进 build/links。
"""
import os, sys, json, subprocess, time, ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed

DOC2KB = r"C:/Users/ZT-052382/.workbuddy/skills/doc2kb/scripts/parse_document.py"
PDF = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准/电缆产品检验-电性能检验 (李骥 陈志刚 主编).pdf"
OUT = r"F:/WorkBuddy/2026-08-04-11-22-11/learning-system-v2/kb/raw/pages_textbook_elec.json"
LOCK = OUT + ".lock"
PY = sys.executable

# ---------- 单实例锁 ----------
if os.path.exists(LOCK):
    try:
        pid = int(open(LOCK).read() or "0")
        if pid:
            kernel32 = ctypes.windll.kernel32
            h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if h:
                kernel32.CloseHandle(h)
                print(f"[quit] 已有实例 pid={pid} 存活，退出", flush=True)
                sys.exit(0)
    except Exception:
        pass
    try:
        os.remove(LOCK)
    except Exception:
        pass
try:
    lf = open(LOCK, "x")
except FileExistsError:
    print("[quit] 锁文件存在，退出", flush=True)
    sys.exit(0)
lf.write(str(os.getpid()))
lf.flush()

# ---------- 后处理（复用 doc2kb 的归一化） ----------
sys.path.insert(0, os.path.dirname(DOC2KB))
import parse_document as pd
norm = pd.normalize_ocr_text

# ---------- 断点续跑 ----------
pages = {}
if os.path.isfile(OUT):
    try:
        d = json.load(open(OUT, encoding="utf-8"))
        for p in d.get("pages", []):
            pages[p["page_no"]] = p["text"]
    except Exception:
        pass
print(f"[info] 断点已有 {len(pages)} 页", flush=True)

# ---------- 总页数 ----------
import pdfplumber
with pdfplumber.open(PDF) as _p:
    total = len(_p.pages)
print(f"[info] 总页数 {total}", flush=True)

def ocr_one(n):
    last_err = ""
    for _ in range(3):  # 失败重试 2 次（高并发易超时，单页给足机会）
        try:
            r = subprocess.run(
                [PY, DOC2KB, PDF, "--ocr", "docling", "--formula", "degrade", "--_page", str(n)],
                capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            last_err = "TimeoutExpired"
            continue
        if r.returncode != 0 or not r.stdout.strip():
            last_err = f"rc={r.returncode} err={(r.stderr or '')[:160]!r}"
            continue
        try:
            d = json.loads(r.stdout)
        except Exception as e:
            last_err = f"json:{e}"
            continue
        txt = d.get("text")
        if isinstance(txt, list):
            txt = "\n".join(txt)
        txt = norm(txt or "")
        if not txt.strip():
            last_err = f"empty status={d.get('status')}"
            continue
        return n, txt
    print(f"[dbg] 第{n}页 最终失败: {last_err}", flush=True)
    return None

def flush():
    tmp = OUT + ".tmp"
    data = {
        "source": os.path.abspath(PDF),
        "method": "docling_pdf",
        "pages": [{"page_no": k, "text": pages[k]} for k in sorted(pages)],
    }
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, OUT)

failed = set()
todo = [n for n in range(1, total + 1) if n not in pages]
print(f"[info] 待 OCR {len(todo)} 页", flush=True)

try:
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(ocr_one, n): n for n in todo}
        cnt = 0
        for fut in as_completed(futs):
            res = fut.result()
            n = futs[fut]
            if res is None:
                failed.add(n)
                print(f"[fail] 第 {n} 页 OCR 失败", flush=True)
                continue
            _, txt = res
            pages[n] = txt
            cnt += 1
            if cnt % 5 == 0:
                flush()
                print(f"[prog] 成功 {len(pages)}/{total} 失败 {len(failed)}", flush=True)
    flush()
finally:
    try:
        os.remove(LOCK)
    except Exception:
        pass

print(f"[DONE] 成功 {len(pages)}/{total} 失败 {len(failed)} "
      f"失败页={sorted(failed)[:30]}", flush=True)
