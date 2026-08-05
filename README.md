# learning-system-v2 · 国缆杯学习/考试系统（重构地基 · MVP）

> 定位：备赛"国缆检测杯"绝缘线缆检验职业技能竞赛（理论+实操）。
> 目标：直接能用的成品系统，不是攻略/大纲文档。

## 一、为什么重做（旧项目的问题）
旧项目 `国缆杯/` 已长成"补丁叠补丁"：
- `app/data/` 下有 **25+ 个 `_gen_gb*.py`**，每个标准一个手写生成脚本 —— 规则没收敛成一处，反而散成脚本堆。
- 这与旧地基文档鼓吹的"单一真源 EXAM_RULES"直接矛盾。
- 做法 = **复用其思路（五闸/去重/质量闸/数据驱动），重写引擎**，而非整搬 54KB/90KB 旧大文件。

## 二、核心设计哲学（继承 + 升级）
1. **资料整合可检索 > 零散文档** —— PDF/Word 标准进库切成知识单元，而非堆文件。
2. **单一真源（Single Source of Truth）** —— 出题规则固化在 `rules/<标准>.json`（数据），引擎框架不变；换标准只改数据。
3. **答案零幻觉** —— 所有题目来自 rules 数据（专家技能 schema + 用户真实资料抽取），引擎只校验/判分/渲染，不编造。
4. **专家库 + 你的东西组合** —— 题型/分值/判分规范来自"出题专家"技能 `standards-exam-generator`；真实内容取自你 `3_标准word版` 的 Word 标准。

## 三、MVP 架构（本目录）
```
learning-system-v2/
├─ engine/generate.py      # 数据驱动出题引擎（纯标准库，离线可跑）
├─ rules/                  # 规则数据（单一真源）：一份标准 = 一个 json
│  ├─ gbt_2951_11_12.json  # 专家技能已验证题库（专家库内容）
│  └─ gbt_3956.json        # 从用户 GB/T 3956-2008 Word 真实抽取（你的资料）
├─ materials/              # 原始资料抽取文本（可溯源）
├─ out/                    # 生成产物：*_bank.json + *_preview.html
└─ scripts/extract_*.py    # 从 Word/PDF 抽文本的脚本
```

### 引擎能力（generate.py）
- 读 `rules/<标准>.json`，校验 schema
- 计算题型得分，输出 `out/<标准>_bank.json`
- **满分自检**：`grade(满分作答) == 总分` 必须 PASS（防规则矛盾）
- 实现 `grade()`：选择/填空/连线/计算（数值容差 + 合格性判定）自动判分
- 渲染 **离线 preview.html**（无 CDN 依赖）

## 四、怎么加一个标准（数据驱动，不要写脚本）
1. 把标准 Word/PDF 放进 `materials/`，用 `scripts/extract_*.py` 抽文本；
2. 按 `rules/gbt_3956.json` 的 schema 写一份 `rules/<新标准>.json`
   （choice/fill/match/calc 四段 + meta.scoring）；
3. 跑 `python engine/generate.py` → 自动生成预览 + 自检。

## 五、当前 MVP 状态
- ✅ 引擎跑通、满分自检 PASS
- ✅ 专家库内容（2951）与用户资料（3956）两条链路都验证
- ⏭ 下一步（按需）：接 Flask 服务层 / 闪卡库 / 更多标准 / 真实 Docling 切块入库
