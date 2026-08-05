#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge_ku.py — KB 管线的「LLM 判断层」

职责（单一职责，不碰提取）：
  读取 doc2kb 产出的原始文本块（pages_*.json，纯提取、无判断），
  把每个文本块交给大模型判断，产出结构化知识单元(KU)。

判断层决定：
  - 这条内容是不是「考点」(is_exam_point)
  - 类型 / 优先级 P0·P1·P2
  - 关键要求(参数/步骤)原样提取，绝不编造
  - 解读

大模型接口：OpenAI 兼容。凭据走环境变量（用户自行配置，脚本不碰明文）：
  KB_LLM_BASE_URL  (默认 https://api.openai.com/v1)
  KB_LLM_API_KEY
  KB_LLM_MODEL     (默认 gpt-4o)

无 key 时 --self 模式：把原始文本块导出成 judge_input_*.json，
由人工/本机大模型在对话里判断后回填 judged_*.json。
"""
import json, os, sys, argparse, glob

RAW_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(os.path.dirname(RAW_DIR), "kb", "kb.db")

SYSTEM_PROMPT = """你是电缆/电线检验领域的标准出题专家，负责知识库管线的「判断层」。
输入是一份国家标准 PDF 经 OCR/提取得到的原始文本块（OCR 可能有噪点、公式区标 [公式区域需 VLM]）。
你要判断每个文本块能否成为「考试知识点(KU)」，并结构化输出。

判断规则（严格遵循，不要自创）：
1. 以下属于「非考点」，is_exam_point=false：
   - 封面/扉页/发布日期/实施日期/标准号本身
   - 目次/目录
   - 前言/引言/编制说明
   - "范围"章里只说"本标准规定了…适用于…"的框架性描述（除非含具体可测参数）
   - 规范性引用文件列表
   - 术语和定义、符号（除非该术语本身在考试里要考，且含可测定义）
   - 单纯的原则性空话（如"试验应按规定进行"）
2. 以下属于「考点」：
   - 具体试验方法/步骤（如密度测定悬浮法操作）
   - 具体参数/限值/允许偏差（如试棒直径 4±0.1mm、试验温度、电压值、时间）
   - 合格判据/通过标准
   - 试样制备要求（尺寸、数量、状态调节）
   - 计算公式及变量含义
   - 不同材料的分类与对应要求

优先级：
   P0 = 高频核心考点（试验方法、关键参数、合格判据、试样制备）
   P1 = 应知考点（试验条件、调节要求、结果处理、解读）
   P2 = 低频/参考（少见参数、边缘条款）

key_requirements：用列表逐条提取**原文事实**，数字/参数必须**原样照抄**文本，绝不编造或推测。
interpretation：1-2 句人话解读，帮助理解为什么考、怎么考。
若 OCR 明显残缺导致无法判断，设 needs_review=true。

只输出 JSON 数组，每个元素：
{
  "is_exam_point": true|false,
  "standard_no": "GB/T 2951.21-2008",
  "clause": "章节号或空",
  "type": "test_method|parameter|pass_criteria|sample_prep|formula|classification|non_exam",
  "priority": "P0|P1|P2|",
  "title": "简短知识点标题",
  "key_requirements": ["原文事实1","原文事实2"],
  "interpretation": "解读",
  "needs_review": false
}
"""


def load_blocks(pages_files):
    blocks = []
    for pf in pages_files:
        dat = json.load(open(pf, encoding="utf-8"))
        # 用文件名推断 standard_no
        bn = os.path.basename(pf)
        std = bn.replace("pages_", "").replace(".json", "").strip()
        for pg in dat.get("pages", []):
            txt = pg.get("text", "").strip()
            if txt:
                blocks.append({"std": std, "page": pg.get("page_no"), "text": txt})
    return blocks


def call_llm(blocks, model, base_url, api_key):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    results = []
    BATCH = 6
    for i in range(0, len(blocks), BATCH):
        chunk = blocks[i:i + BATCH]
        user_msg = "以下是一批标准文本块，请逐块判断并输出 JSON 数组：\n\n"
        for b in chunk:
            user_msg += f"【块 std={b['std']} page={b['page']}】\n{b['text']}\n\n"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user_msg}],
            temperature=0.0,
            response_format={"type": "json_object"} if False else None,
        )
        content = resp.choices[0].message.content
        try:
            arr = json.loads(content)
            if isinstance(arr, dict) and "items" in arr:
                arr = arr["items"]
            results.extend(arr)
        except Exception as e:
            print(f"[warn] LLM 返回解析失败: {e}\n{content[:500]}", file=sys.stderr)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="*", default=["2951.13", "2951.21", "2951.31", "2951.32"],
                    help="要处理的 standard 前缀")
    ap.add_argument("--self", action="store_true",
                    help="不调 LLM，只导出 judge_input_*.json 供人工/对话判断")
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    pats = []
    for d in args.docs:
        pats += glob.glob(os.path.join(RAW_DIR, f"pages_{d}*.json"))
    blocks = load_blocks(pats)
    print(f"载入 {len(blocks)} 个文本块（来自 {len(pats)} 个 pages 文件）")

    if args.self or not os.environ.get("KB_LLM_API_KEY"):
        # 导出供人工/对话判断
        out = os.path.join(RAW_DIR, "judge_input.json")
        json.dump(blocks, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[self] 已导出待判断文本块 -> {out}")
        print("       配置 KB_LLM_API_KEY / KB_LLM_BASE_URL / KB_LLM_MODEL 后可自动跑 LLM 判断。")
        return

    res = call_llm(blocks,
                   model=os.environ.get("KB_LLM_MODEL", "gpt-4o"),
                   base_url=os.environ.get("KB_LLM_BASE_URL", "https://api.openai.com/v1"),
                   api_key=os.environ["KB_LLM_API_KEY"])
    out = os.path.join(RAW_DIR, "judged.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_point = sum(1 for r in res if r.get("is_exam_point"))
    print(f"[llm] 判断完成：{len(res)} 块 -> {n_point} 个考点，已存 {out}")
    # TODO: 写入 kb.db 的 knowledge_units 表（清洗后）


if __name__ == "__main__":
    main()
