# -*- coding: utf-8 -*-
"""
ingest_textbooks_doc2kb.py (加固版) — 扫描版教材入库（三块资料之"书籍教材"）。

职责切分（遵循用户要求）：
  * OCR 能力     -> doc2kb 的 parse_document.py（本地 Docling/RapidOCR 离线管线）
  * 落库业务     -> 本项目 _build_kb.py（切块 clause + 生成考试考点 KU 落 kb.db）
  * 补 KU        -> 本项目 rebuild_missing_ku.py（修 10 个产品标准缺失 KU）
  * 结构化链接   -> 本项目 build_links.py（大纲→实验→标准→产品特殊规定 写进 kb.db）

加固点（满足"持续监控 / 不中断"）：
  1. 断点续跑：每阶段开始先查"产物是否已在"，在则跳过（OCR 半途崩溃重跑不浪费）。
  2. 阶段独立容错：单阶段失败仅记录并继续后续阶段，最后汇总，绝不整条链 SystemExit。
  3. 状态文件 kb/ingest_textbook_status.json：记录每阶段 done/skip/fail + 时间，便于 watchdog 与人工查看。
"""
import subprocess
import sys
import os
import time
import json
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "kb", "kb.db")
RAW = os.path.join(ROOT, "kb", "raw")
DOC2KB = r"C:/Users/ZT-052382/.workbuddy/skills/doc2kb/scripts/parse_document.py"
BUILD_KB = os.path.join(ROOT, "_build_kb.py")
REBUILD_KU = os.path.join(ROOT, "kb", "rebuild_missing_ku.py")
BUILD_LINKS = os.path.join(ROOT, "kb", "build_links.py")
STATUS = os.path.join(ROOT, "kb", "ingest_textbook_status.json")
PY = sys.executable

BASE = r"F:/各项工作/4_日常工作/4_高压车间质量控制/14_competition_paper_research/国缆杯/2_reference/全部标准"
TEXTBOOKS = [
    (os.path.join(BASE, "电缆产品检验-电性能检验 (李骥 陈志刚 主编).pdf"), "elec",
     "电缆产品检验-电性能检验"),
    (os.path.join(BASE, "电缆产品检验-非电性能检验 (肖继东 主编).pdf"), "nonelec",
     "电缆产品检验-非电性能检验"),
]


def load_status():
    if os.path.isfile(STATUS):
        try:
            return json.load(open(STATUS, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_status(s):
    tmp = STATUS + ".tmp"
    json.dump(s, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATUS)


def textbook_in_db(conn, name_sub):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM documents WHERE title LIKE ?", (f"%{name_sub}%",))
    return cur.fetchone()[0] > 0


def run_capture(cmd, step, errfile):
    """运行命令，返回 True/False；stderr 落独立文件便于诊断，不吞输出。"""
    t0 = time.time()
    print(f"\n[{time.strftime('%H:%M:%S')}] >>> {step}", flush=True)
    print("    " + " ".join(cmd), flush=True)
    with open(errfile, "a", encoding="utf-8") as ef:
        ef.write(f"\n[{time.strftime('%H:%M:%S')}] {step}\n")
        r = subprocess.run(cmd, stderr=ef)
    rc = r.returncode
    print(f"    rc={rc} 耗时 {time.time()-t0:.0f}s", flush=True)
    return rc == 0


def stage_ocr(pdf, key, st):
    """doc2kb OCR 整本 -> pages_textbook_{key}.json。已存在且非空则跳过。"""
    out = os.path.join(RAW, f"pages_textbook_{key}.json")
    if os.path.isfile(out) and os.path.getsize(out) > 1024:
        print(f"[SKIP] OCR 教材[{key}] 已存在产物: {out}", flush=True)
        st[f"ocr_{key}"] = {"state": "skip", "time": time.strftime("%H:%M:%S")}
        return True
    errfile = os.path.join(RAW, f"err_textbook_{key}.log")
    ok = run_capture([PY, DOC2KB, pdf, "--ocr", "docling", "--formula", "degrade",
                      "--out", out], f"doc2kb OCR 教材[{key}]", errfile)
    st[f"ocr_{key}"] = {"state": "done" if ok else "fail",
                        "time": time.strftime("%H:%M:%S"),
                        "err": errfile if not ok else None}
    return ok


def stage_build(pdf, key, name_sub, st):
    """本项目 _build_kb 落库。教材文档已入库则跳过。"""
    conn = sqlite3.connect(DB)
    already = textbook_in_db(conn, name_sub)
    conn.close()
    if already:
        print(f"[SKIP] _build_kb 落库 教材[{key}] 文档已在库", flush=True)
        st[f"build_{key}"] = {"state": "skip", "time": time.strftime("%H:%M:%S")}
        return True
    out = os.path.join(RAW, f"pages_textbook_{key}.json")
    if not (os.path.isfile(out) and os.path.getsize(out) > 1024):
        print(f"[FAIL] 教材[{key}] pages 产物缺失，跳过落库", flush=True)
        st[f"build_{key}"] = {"state": "fail", "time": time.strftime("%H:%M:%S")}
        return False
    errfile = os.path.join(RAW, f"err_build_{key}.log")
    ok = run_capture([PY, BUILD_KB, out, "--normative", "strict", "--chunk", "clause",
                      "--ku-mode", "exam", "--db", DB],
                     f"本项目 _build_kb 落库 教材[{key}]", errfile)
    st[f"build_{key}"] = {"state": "done" if ok else "fail",
                          "time": time.strftime("%H:%M:%S"),
                          "err": errfile if not ok else None}
    return ok


def stage_rebuild_ku(st):
    errfile = os.path.join(RAW, "err_rebuild_ku.log")
    ok = run_capture([PY, REBUILD_KU], "rebuild_missing_ku 补产品标准 KU", errfile)
    st["rebuild_ku"] = {"state": "done" if ok else "fail",
                        "time": time.strftime("%H:%M:%S"),
                        "err": errfile if not ok else None}
    return ok


def stage_build_links(st):
    errfile = os.path.join(RAW, "err_build_links.log")
    ok = run_capture([PY, BUILD_LINKS], "build_links 全量重链", errfile)
    st["build_links"] = {"state": "done" if ok else "fail",
                         "time": time.strftime("%H:%M:%S"),
                         "err": errfile if not ok else None}
    return ok


def main():
    os.makedirs(RAW, exist_ok=True)
    st = load_status()
    fails = []
    for pdf, key, name_sub in TEXTBOOKS:
        if not os.path.isfile(pdf):
            print("[WARN] 找不到教材:", pdf, flush=True)
            st[f"ocr_{key}"] = {"state": "missing", "time": time.strftime("%H:%M:%S")}
            fails.append(f"ocr_{key}:missing")
            continue
        if not stage_ocr(pdf, key, st):
            fails.append(f"ocr_{key}")
        save_status(st)
        if not stage_build(pdf, key, name_sub, st):
            fails.append(f"build_{key}")
        save_status(st)

    if not stage_rebuild_ku(st):
        fails.append("rebuild_ku")
    save_status(st)

    if not stage_build_links(st):
        fails.append("build_links")
    save_status(st)

    if fails:
        print(f"\n[PARTIAL] 完成但有失败阶段: {fails}", flush=True)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 失败阶段将可被 watchdog/重跑续接", flush=True)
    else:
        print(f"\n[ALL DONE] {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
