# Baseline Decision Log

Template ID: Baseline_Decision_Log_V1  
Date: 2026-08-10  
Status: COMPLETED

| ID | Baseline / Scope | Observation | Evidence | Interpretation | Signal | Product Implication | Next Step |
|---|---|---|---|---|---|---|---|
| D-001 | A/B/C | A 与 C 在 Rubric V1 六个质量维度均达到 2；B 仅决策完整性为 2，其余五维为 1。 | `20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_B_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` § Dimension-level Observations | Rubric V1 能区分人工现有流程与高质量 AI 工具，但无法进一步区分 A 与 C。 | Uncertain | 当前量表存在 ceiling effect，不应事后改分。 | 保留 V1；后续增加不回填本轮分数的描述性分析维度。 |
| D-002 | B | B 在过程里读取了依赖、数据获取、训练/测试脚本和论文参数，但最终输出主要集中在数据分块/磁盘问题。 | `20260810_Baseline_B_Time_Interaction_Log_V1_COMPLETED.md` § Event Log（17:43–18:19）；`20260810_Baseline_B_Record_V1_COMPLETED.md` § 5 Raw Process Record、§ 6 Final Output；`20260810_Baseline_B_Scorecard_V1_COMPLETED.md` § Dimension-level Observations | 核心断点是“信息发现 → 结构化决策”转换不足，而不是单纯搜索能力不足。 | Support | ResearchOps 应帮助用户把分散证据转成统一的准备度判断。 | MVP 用统一 Readiness Card 自动归类关键缺失、风险、Unknown 与下一步行动。 |
| D-003 | A | A 5 分钟、0 follow-up 即完成六字段，并达到 Rubric V1 六维 2。 | `20260810_Baseline_A_Record_V1_COMPLETED.md` § 6.1–6.6；`20260810_Baseline_A_Time_Interaction_Log_V1_COMPLETED.md` § Timing、§ Event Log（23:04–23:09）；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md` § Dimension-level Observations | 单轮通用大模型已经可以生成高质量复现准备判断。 | Contradict | “仅生成一份完整判断”不足以构成 ResearchOps 差异化。 | 当前 MVP 聚焦结构化准备度、证据呈现和下一步行动；持续状态、协作和完整审计留作 Roadmap。 |
| D-004 | C | C 7 分钟完成正式判断，但有额外 5 分钟 repository setup。 | `20260810_Baseline_C_Record_V1_COMPLETED.md` § 2 Test Environment、§ 3 Timing、§ 5 Raw Process Record；`20260810_Baseline_C_Time_Interaction_Log_V1_COMPLETED.md` § Timing、§ Event Log、§ Pre-test Setup Cost | Codex 的代码级分析能力强，但工具形态有前置准备成本。 | Support | 产品设计应尽量减少 repo setup，并显式记录工具特有成本。 | 后续比较同时报告 Formal Decision Time 与 Setup Cost。 |
| D-005 | A/C | A/C 内部搜索次数、材料切换次数和部分工具路径不可完全观察。 | `20260810_Baseline_A_Time_Interaction_Log_V1_COMPLETED.md` § Interaction、§ Cost Notes；`20260810_Baseline_C_Time_Interaction_Log_V1_COMPLETED.md` § Interaction、§ Cost Notes；`20260810_Baseline_A_Record_V1_COMPLETED.md` § 4 Interaction Record；`20260810_Baseline_C_Record_V1_COMPLETED.md` § 4 Interaction Record | A/C 虽能提供较好的证据引用，但完整检索过程不可完全观察；用户仍需要一种更稳定、统一的方式核对关键判断与最终证据之间的对应关系。 | Support | ResearchOps 在 Readiness Card 中标准化呈现 Evidence-linked Findings，而不是把“提供 citation”本身作为差异化能力。 | Concept Test 验证用户是否能更快理解、定位和核对 Readiness Card 中的关键证据。 |
| D-006 | A/C | 当前 Scorecard 评价的是结构、覆盖与可追溯性，未独立核验每条技术事实。 | `20260810_Baseline_Rubric_V1.md` § 1–6、§ Scoring Rules；`20260810_Baseline_A_Scorecard_V1_COMPLETED.md`、`20260810_Baseline_C_Scorecard_V1_COMPLETED.md` § Dimension-level Observations | Baseline 的高分代表输出结构和可追溯性优秀，不等于每条事实都已独立验证。 | Uncertain | 将事实准确性未被独立验证明确记录为本轮研究限制。 | 不新增 Sprint 2 Fact Accuracy Audit；后续引用结果时保留该限制，且不改 V1 分数。 |
| D-007 | A/B/C | B Formal Decision Time 56 min；A 5 min；C 7 min，C 另有 5 min Setup Cost。 | `20260810_Baseline_A_Time_Interaction_Log_V1_COMPLETED.md` § Timing、§ Event Log；`20260810_Baseline_B_Time_Interaction_Log_V1_COMPLETED.md` § Timing、§ Event Log；`20260810_Baseline_C_Time_Interaction_Log_V1_COMPLETED.md` § Timing、§ Event Log、§ Pre-test Setup Cost | 自动化方案明显降低单次判断所需人工等待/阅读成本，但当前比较对象不是 ResearchOps treatment。 | Support | 有效率机会，但不能据此宣称 H2 成立。 | 后续 Concept / H2 测试用 ResearchOps treatment 与对照正式验证。 |

## Decision Summary

### Keep

- 保留 Baseline A / B / C 原始记录、Time Log、Scorecard 和冻结 Rubric V1。
- 保留 C 的 Setup Cost 与 Formal Decision Time 分离记录。
- 保留 B 的“信息发现 → 结构化决策”断点作为核心问题证据。

### Do Not Claim

- 不宣称 ResearchOps 已优于通用大模型或 Codex。
- 不宣称 H2 / H3 已成立。
- 不因 A/C 满分而修改 Rubric V1 或回溯重打分。
- 不把“证据可追溯性 2 分”等同于“所有事实已经独立验证”。

### Carry Forward

后续 Product Spec / Concept Test 不再继续证明“能否生成一份长而完整的回答”，而按以下范围推进：

以下三个 MVP 模块是产品结构。其中，Readiness Card 统一承载复现前准备度的核心检查维度与状态；Day 3 冻结决策结构和 Ready / Warning / Blocked / Unknown 状态语义，具体维度数量、正式名称、定义及 Gate 权重由 D4 PRD 依据 Sprint 1 Evidence × Baseline Breakpoint 双证据映射冻结，不预设必须为六维。

**当前 MVP：**

- Readiness Card
- Evidence-linked Findings
- Next Action / Gate

**Future Roadmap：**

- Persistent State
- Decision Update
- Collaboration / Handoff
