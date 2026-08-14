# -*- coding: utf-8 -*-
"""
watchdog_textbook.py — 教材入库守护进程（满足"持续监控 / 不中断"）。

职责：
  * 每 ~90s 探测主入库进程（命令行含 ingest_textbooks_doc2kb.py 且非自身）是否存活。
  * 主进程存活 -> 仅记录，继续等。
  * 主进程死亡 ->
      - 其日志已含 [ALL DONE]      -> 视为正常完成，watchdog 退出。
      - 否则（崩溃 / [FAIL] / Traceback / 被杀）-> 自动拉起加固版 ingest_textbooks_doc2kb.py
        续跑（断点续跑会跳过已完成的 OCR/落库阶段），最多重试 2 次。
  * 用 run_in_background 启动时，watchdog 自身退出会触发完成通知，便于人工接管。

注意：本文件绝不含 "ingest_textbooks_doc2kb.py" 字面量之外的歧义匹配；定位主进程时
显式排除自身（命令行含 "watchdog_textbook"）。
"""
import subprocess
import sys
import os
import time
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = r"C:/Users/ZT-052382/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
INGEST = os.path.join(ROOT, "kb", "ingest_textbooks_doc2kb.py")
LEGACY_LOG = os.path.join(ROOT, "kb", "ingest_textbooks_doc2kb.log")
WATCH_LOG = os.path.join(ROOT, "kb", "ingest_textbook_watchdog.log")
INTERVAL = 90
MAX_RETRY = 2


def find_main_pid():
    """探测主入库进程（命令行含 ingest_textbooks_doc2kb.py 且非自身）。

    注意：本机 wmic 被安全策略禁用（返回 SYSTEM TOOL DISABLED），故改用
    PowerShell Get-CimInstance 取 CommandLine 匹配——这是修复"watchdog 永远检测不到
    主进程→反复误拉起→重复进程风暴"的根因。
    """
    ps = ('Get-CimInstance Win32_Process -EA SilentlyContinue | '
          'Where-Object { $_.Name -eq "python.exe" -and '
          '$_.CommandLine -match "ingest_textbooks_doc2kb" -and '
          '$_.CommandLine -notmatch "watchdog_textbook" } | '
          'ForEach-Object { $_.ProcessId }')
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            shell=False, text=True, errors="ignore", timeout=30)
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] [watchdog] ps 查询失败: {e}", flush=True)
        return None
    pids = [int(x) for x in out.split() if x.strip().isdigit()]
    return pids[0] if pids else None


def log_tail_has(path, *markers):
    if not os.path.isfile(path):
        return False
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return False
    return any(m in txt for m in markers)


def launch_hardened():
    print(f"\n[{time.strftime('%H:%M:%S')}] [watchdog] >>> 拉起加固版续跑", flush=True)
    with open(WATCH_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{time.strftime('%H:%M:%S')}] launch hardened ingest\n")
        r = subprocess.run([PY, INGEST], stdout=f, stderr=f)
    return r.returncode


def main():
    print(f"[{time.strftime('%H:%M:%S')}] [watchdog] 启动，监控入库进程", flush=True)
    retries = 0
    while True:
        pid = find_main_pid()
        if pid is not None:
            print(f"[{time.strftime('%H:%M:%S')}] 主进程存活 pid={pid}，等待...", flush=True)
            time.sleep(INTERVAL)
            continue
        # 主进程已死
        print(f"[{time.strftime('%H:%M:%S')}] 主进程不在，判断死因", flush=True)
        if log_tail_has(LEGACY_LOG, "[ALL DONE]") or log_tail_has(WATCH_LOG, "[ALL DONE]"):
            print(f"[{time.strftime('%H:%M:%S')}] 主进程已正常完成([ALL DONE])，watchdog 退出", flush=True)
            break
        # 异常死亡 -> 续跑
        if retries >= MAX_RETRY:
            print(f"[{time.strftime('%H:%M:%S')}] 续跑已达上限 {MAX_RETRY}，需人工介入", flush=True)
            break
        rc = launch_hardened()
        retries += 1
        print(f"[{time.strftime('%H:%M:%S')}] 加固版续跑 rc={rc} (第{retries}次)", flush=True)
        if log_tail_has(WATCH_LOG, "[ALL DONE]"):
            print(f"[{time.strftime('%H:%M:%S')}] 续跑成功完成，watchdog 退出", flush=True)
            break
        # 续跑仍未 [ALL DONE]（可能是 [PARTIAL]），进入下一轮再判断
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] [watchdog] 自身异常: {e}", flush=True)
        raise
