# Baseline A / B / C Decision Breakpoint Comparison

Document ID: 20260810_Baseline_ABC_Decision_Breakpoint_Comparison_V1  
Date: 2026-08-10  
Status: COMPLETED  
Rubric: 20260810_Baseline_Rubric_V1.md

## 1. Comparison Scope

本文件用于比较同一 FGI 复现准备判断任务下的三个 Baseline：

- Baseline A｜通用大模型自由对话
- Baseline B｜人工现有流程
- Baseline C｜Codex App

比较重点不是单一总分，而是：
1. 各质量维度是否出现决策断点；
2. 时间 / 交互成本；
3. 信息发现后是否能转化为结构化判断；
4. 对 ResearchOps 产品设计的直接启示。

不修改或重打已冻结的 Baseline Rubric V1 分数。

## 2. Quality Comparison

| 质量维度 | Baseline A | Baseline B | Baseline C |
|---|---:|---:|---:|
| 决策完整性 | 2 | 2 | 2 |
| 关键缺失 / 阻塞识别 | 2 | 1 | 2 |
| 证据可追溯性 | 2 | 1 | 2 |
| 未知项处理 | 2 | 1 | 2 |
| 风险完整性 | 2 | 1 | 2 |
| 行动可执行性 | 2 | 1 | 2 |

说明：
- 不把上述分数汇总成单一“总分排名”作为主要结论。
- A 与 C 在当前 Rubric V1 上均达到六维 2 分，说明当前量表对高质量工具存在明显 ceiling effect。
- B 的主要差距集中在“发现信息之后，没有完整转化为结构化决策”。

## 3. Time / Interaction Cost

| Baseline | Formal Decision Time | Additional Setup Cost | User Follow-up | Timeout |
|---|---:|---:|---:|---|
| A｜通用大模型 | 5 min | None recorded | 0 | No |
| B｜人工现有流程 | 56 min | None recorded | N/A | No |
| C｜Codex App | 7 min | 5 min | 0 | No |

说明：
- C 的 5 min Setup Cost 为 clone repository + checkout frozen commit + open Codex App project。
- 该 Setup Cost 按冻结 Protocol 不计入 Formal Decision Time，但后续效率分析必须单独报告，不能隐去。
- A/C 的内部 Search Count、Material Switch Count、Tool Count 不完全可观察，因此不能与 B 的显式人工计数做伪精确比较。

## 4. Decision Breakpoints

### Baseline A

**Critical Decision Breakpoint:** None under Rubric V1.

表现：
- 首轮即完成六字段；
- 覆盖环境、数据、磁盘、时间、代码/论文冲突等问题；
- 能形成 Gate + 最小闭环式行动路径。

限制：
- 搜索与工具过程不可完全观察；
- 虽有较好的来源定位，但并非所有判断都达到源码行级证据；
- 当前评分只代表结构、覆盖和可追溯性达到 Rubric 锚点，不代表所有技术事实已独立验证。

### Baseline B

**Critical Decision Breakpoint:** 信息发现 → 结构化决策转换不足。

过程记录显示人工流程实际已经接触到：
- package-list.txt；
- DFDC 获取要求；
- README；
- 训练 / 测试脚本；
- 论文与仓库之间的训练参数补充关系；
- 数据分块、磁盘容量与预处理问题。

但最终六字段主要收敛为：
- 训练集具体分块 / 大小未知；
- 367 GB 磁盘不足以容纳记录到的完整数据规模；
- 继续查数据分块、腾磁盘、预处理数据。

因此主要失败不是“完全找不到信息”，而是：
**在有限时间内无法把分散证据系统映射为完整的缺失项、风险、未知项和优先行动。**

### Baseline C

**Critical Decision Breakpoint:** None under Rubric V1.

表现：
- 本地 repository workspace 带来较强代码级定位能力；
- 能识别环境、权限、磁盘、显存、权重、时间、指标口径和论文—代码配置差异；
- 行动方案能映射为 Gate → 冒烟测试 → 短训练标定。

限制：
- 需要额外 5 min repository setup；
- Codex App 内部具体搜索 / 命令 / 文件切换次数不完全可观察；
- 与 A 一样，技术事实准确性尚未做独立 post-hoc audit。

### 4.1 Breakpoint Evidence Mapping

本表用于把本节的核心断点 / 能力判断映射回可复核的原始记录；它不新增评分维度，也不替代 A / B / C 的完整 Record、Time / Interaction Log 与 Scorecard。

| 决策阶段 | A 表现 | B 表现 | C 表现 | 用户影响 | 证据 ID / 文件 |
|---|---|---|---|---|---|
| ① 信息发现 | 5 min 内搜索或核对约 20 个网页 / 源码来源，覆盖环境、数据、训练与预处理信息。 | 56 min 内查阅论文、仓库、README、依赖、Kaggle 数据页及训练 / 测试脚本，能够找到大量相关材料。 | 依托本地冻结仓库和公开检索快速定位代码、配置、论文及外部数据页面，但另有 5 min Setup Cost。 | A/C 可显著缩短发现信息所需时间；B 的问题不是完全找不到信息，而是人工查找和切换成本高。 | D-002、D-004、D-007；`20260810_Baseline_A_Time_Interaction_Log_V1_COMPLETED.md` § Event Log；`20260810_Baseline_B_Time_Interaction_Log_V1_COMPLETED.md` § Event Log；`20260810_Baseline_C_Time_Interaction_Log_V1_COMPLETED.md` § Event Log、§ Pre-test Setup Cost。 |
| ② 跨材料合并 | 能把论文、README、源码与用户硬件约束合并，并识别论文—代码学习率等差异。 | 已发现论文补充仓库训练参数，但没有把所有分散材料稳定汇总到统一准备度结果。 | 能结合本地源码、README、论文与用户环境形成代码级综合判断。 | B 的分散证据未完整进入最终判断，增加遗漏 blocker 和重复核对的风险。 | D-002；`20260810_Baseline_A_Record_V1_COMPLETED.md` § 6.2–6.5；`20260810_Baseline_B_Time_Interaction_Log_V1_COMPLETED.md` 18:19、`20260810_Baseline_B_Record_V1_COMPLETED.md` § 5–6；`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.2–6.5。 |
| ③ 条件判断 | 对数据权限、依赖、磁盘、GPU、权重与配置给出较完整判断。 | 最终主要判断训练集分块 / 大小和磁盘问题，其他已发现条件未被完整转化。 | 对环境、权限、磁盘、显存、权重、时间与配置差异给出较完整判断。 | B 用户可能在条件覆盖不足时过早继续，或无法看清全部前置约束。 | D-002；`20260810_Baseline_A_Record_V1_COMPLETED.md`、`20260810_Baseline_B_Record_V1_COMPLETED.md`、`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.1–6.3；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_B_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` 的“关键缺失 / 阻塞识别”“风险完整性”。 |
| ④ 未知与冲突 | 显式列出数据、耗时、参数口径等 Unknown，并保留论文—代码冲突。 | 记录了数据分块、训练集大小和预处理空间等 Unknown，但覆盖范围较窄。 | 显式保留数据可得性、完整训练耗时、三卡效率及论文—代码配置差异等 Unknown。 | 未知未被充分暴露时，用户容易把“未核验”误当成“已满足”。 | D-001、D-002；`20260810_Baseline_A_Record_V1_COMPLETED.md`、`20260810_Baseline_B_Record_V1_COMPLETED.md`、`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.3、§ 6.5；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_B_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` 的“未知项处理”。 |
| ⑤ 证据核对 | 提供较好的来源定位，但内部检索路径与部分判断的源码粒度不可完全观察。 | 最终证据出处较概括，难以把每个判断快速核对回具体材料。 | 提供较细的本地文件 / 行级定位，但内部完整检索过程仍不可完全观察。 | 用户仍需要统一方式核对关键判断与最终证据的对应关系；citation 本身不是 ResearchOps 独有能力。 | D-005；`20260810_Baseline_A_Record_V1_COMPLETED.md`、`20260810_Baseline_B_Record_V1_COMPLETED.md`、`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.4；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_B_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` 的“证据可追溯性”；`20260810_Baseline_A_Time_Interaction_Log_V1_COMPLETED.md`、`20260810_Baseline_C_Time_Interaction_Log_V1_COMPLETED.md` 的 observability 记录。 |
| ⑥ Gate 形成 | 形成“有条件继续”及环境 Gate、数据 / 磁盘 Gate。 | 虽形成“有条件继续”，但 Gate 主要建立在有限的数据与磁盘判断上。 | 形成“有条件继续”，并组织为 Gate → 冒烟测试 → 短训练标定。 | 结构化 Gate 能减少用户面对信息摘要后仍不知道是否该继续的情况。 | D-002、D-003；`20260810_Baseline_A_Record_V1_COMPLETED.md`、`20260810_Baseline_B_Record_V1_COMPLETED.md`、`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.1、§ 6.6；本文件 § 4 的 Baseline A/B/C 断点说明。 |
| ⑦ Next Action | 给出三步、带前置条件的最小闭环行动路径。 | 行动集中于继续查数据分块、腾出磁盘和预处理数据，未覆盖全部已发现风险。 | 给出 Gate、少量样本冒烟测试和短训练标定等优先行动。 | B 的行动路径受前置信息遗漏影响；A/C 表明高质量工具已能生成行动，因此 ResearchOps 需验证固定结构带来的增量价值。 | D-002、D-003；`20260810_Baseline_A_Record_V1_COMPLETED.md`、`20260810_Baseline_B_Record_V1_COMPLETED.md`、`20260810_Baseline_C_Record_V1_COMPLETED.md` § 6.6；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_B_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` 的“行动可执行性”。 |

## 5. Cross-Baseline Findings

### Finding 1｜人工流程的核心问题不是“完全没有信息”，而是信息整合成本高

B 在 56 分钟内能找到多种材料，但最终结构化输出覆盖明显不足。  
这支持 ResearchOps 需要重点解决：

**Evidence Discovery → Evidence Organization → Readiness Decision → Next Actions**

而不仅仅是“帮用户搜索论文和仓库”。

### Finding 2｜通用大模型已经是非常强的 Baseline

A 在 5 分钟、0 次追问条件下，已经达到当前 Rubric V1 的六维 2 分。

因此 ResearchOps 后续不能只证明：
“它能生成一份完整的复现准备判断。”

这个能力已经被通用大模型较好覆盖。

更有价值的差异化方向应转向：
- Structured Readiness Card：把论文、Repo 和用户环境整理为缺失项、风险、Unknown 与 Readiness；
- Evidence-linked Findings：将关键判断与论文、README 或源码依据以统一的产品结构呈现，减少用户在长对话中定位和核对证据的成本；
- Next Action / Gate：明确当前优先行动，以及 Ready / Warning / Blocked / Unknown 状态。

这些方向用于验证 ResearchOps 相对于单次自由对话的结构化、证据定位与行动引导价值，不要求当前 MVP 承担完整的持续工作流管理。

### Finding 3｜Codex 的优势主要体现在代码仓库级理解，而不是零成本使用

C 的正式判断只用了 7 分钟，但还存在 5 分钟本地仓库准备成本。

因此后续产品比较必须区分：
- Decision Time；
- Tool-specific Setup Cost；
- Evidence Granularity；
- Process Observability。

不能只比较“最终回答生成用了几分钟”。

### Finding 4｜Rubric V1 对 A/C 出现 ceiling effect

A 和 C 六个质量维度全部得到 2 分，说明 V1 足以区分较弱人工流程与高质量工具，但不足以细分 A 与 C。

不能因为 A/C 满分就事后修改 Rubric 或重打本轮分数。

建议：
- 保留 Rubric V1 和所有原分数；
- 将“ceiling effect”作为本轮实验发现；
- 后续若需要区分高质量方案，在新版本分析框架中增加描述性维度，例如：
  evidence precision、fact verification、process observability、setup burden。
- 新维度不得回填或重算当前冻结 Baseline 分数。

## 6. Current Product Implication

当前证据最支持的产品机会不是：

> “做一个比 ChatGPT 更会回答复现问题的聊天机器人。”

而是：

> “把论文、Repo 和用户环境整理成结构化、证据可定位、行动明确的复现前准备度结果。”

Baseline B 暴露的是人工流程的结构化决策缺口；  
Baseline A 证明单次高质量回答已经容易获得；  
Baseline C 证明代码级自动分析很强，但仍存在 setup 成本和过程透明度限制。

因此，当前 MVP 的产品机会收敛为三项：

这里的三个 MVP 模块描述产品结构。其中，Structured Readiness Card 统一承载复现前准备度的核心检查维度与状态；具体维度数量、正式名称、定义及 Gate 权重将在 D4 PRD 中依据 Sprint 1 问题证据与 Baseline 决策断点完成冻结，不预设必须为六维。

### 1. Structured Readiness Card

把论文、Repo 和用户环境整理为：

- 缺失项；
- 风险；
- Unknown；
- Readiness。

### 2. Evidence-linked Findings

将关键判断与论文、README 或源码依据以统一的产品结构呈现，减少用户在长对话中定位和核对证据的成本。

### 3. Next Action / Gate

明确告诉用户当前应优先做什么，并呈现：

- Ready；
- Warning；
- Blocked；
- Unknown。

Persistent state、自动决策更新、多人协作与历史审计作为 Future Roadmap，不作为当前 MVP 必须验证的能力。

## 7. Boundary

本文件不做以下声明：

- 不声明 ResearchOps 已优于 A / B / C；
- 不声明 H2 已成立；
- 不声明 A 或 C 的所有技术事实均已验证正确；
- 不修改已冻结 Rubric；
- 不用单一总分替代维度级 Decision Breakpoint 分析。
