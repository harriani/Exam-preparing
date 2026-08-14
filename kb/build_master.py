# -*- coding: utf-8 -*-
"""合并所有 _ku_doc*.json → 规范化 → 去重 → master_judged.json

用法: python kb/build_master.py
"""
import glob
import io
import json
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ku_schema import normalize, validate, SCHEMA_VERSION  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUDGED = os.path.join(ROOT, "kb", "judged")
OUT = os.path.join(ROOT, "kb", "master_judged.json")


def load_all():
    items, bad = [], []
    for f in sorted(glob.glob(os.path.join(JUDGED, "_ku_doc*.json"))):
        doc = int(re.search(r"_ku_doc(\d+)", f).group(1))
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception as e:
            bad.append((os.path.basename(f), str(e)[:60]))
            continue
        if isinstance(d, dict):
            d = d.get("kus") or d.get("units") or []
        for k in d:
            k = normalize(k)
            k["doc_id"] = doc
            items.append(k)
    return items, bad


def dedup(items):
    """同一 (standard_no, title) 只保留 key_requirements 更丰富的一条。"""
    best = {}
    for k in items:
        key = (k["standard_no"], k["title"])
        old = best.get(key)
        if old is None or len(k["key_requirements"]) > len(old["key_requirements"]):
            best[key] = k
    return list(best.values())


def main():
    items, bad = load_all()
    n_raw = len(items)
    items = dedup(items)

    errs = []
    for k in items:
        e = validate(k)
        if e:
            errs.append((k.get("standard_no"), k.get("title", "")[:24], e))

    items.sort(key=lambda k: (k["standard_no"], k["clause"]))
    payload = {
        "schema": SCHEMA_VERSION,
        "count": len(items),
        "standards": sorted(set(k["standard_no"] for k in items)),
        "kus": items,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=1))

    c = collections.Counter(k["standard_no"] for k in items)
    p = collections.Counter(k["priority"] for k in items)
    t = collections.Counter(k["type"] for k in items)
    print("原始 %d 条 -> 去重后 %d 条 / %d 份标准" % (n_raw, len(items), len(c)))
    print("优先级", dict(p))
    print("类型", dict(t))
    print("考点", sum(1 for k in items if k["is_exam_point"]),
          "非考点", sum(1 for k in items if not k["is_exam_point"]))
    if bad:
        print("!! 坏 JSON 文件:", bad)
    if errs:
        print("!! 契约校验失败 %d 条:" % len(errs))
        for s, t_, e in errs[:15]:
            print("   ", s, t_, e)
    else:
        print("契约校验: 全部通过")
    print("写出:", OUT)
    return 1 if (bad or errs) else 0


if __name__ == "__main__":
    sys.exit(main())
