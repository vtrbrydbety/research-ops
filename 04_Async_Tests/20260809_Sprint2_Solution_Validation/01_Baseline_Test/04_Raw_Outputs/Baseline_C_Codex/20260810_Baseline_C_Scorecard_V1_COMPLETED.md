# Baseline Scorecard

Template ID: Baseline_Scorecard_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

Baseline:
Baseline C｜Codex App

Raw Record:
20260810_Baseline_C_Record_V1_COMPLETED.md

Rubric:
20260810_Baseline_Rubric_V1.md

| 质量维度 | Score | Evidence / Scoring Rationale |
|---|---:|---|
| 决策完整性 | 2 | 明确给出“有条件继续”，并把继续条件限定为前 6–12 小时内确认数据授权、环境可用性并完成少量视频端到端冒烟测试；同时结合 3 天预算说明暂不直接投入完整 100 epoch 训练。 |
| 关键缺失 / 阻塞识别 | 2 | 系统识别了 DFDC/FakeAVCeleb 权限、数据下载与实际大小、Driver/CUDA/PyTorch、显存、官方权重、预处理与训练耗时、目标表格/容差等高影响缺失项。 |
| 证据可追溯性 | 2 | 对关键结论给出了 BMVC 正式论文、固定 Commit、README、package-list.txt、my_train.py、model.py、预处理脚本、数据名单及 FakeAVCeleb 官方说明等可定位来源；原始输出还包含仓库文件行级定位，并明确区分事实、推断和未知。 |
| 未知项处理 | 2 | 明确列出作者训练硬件/时长、3×2080 Ti 实测性能、367 GB 峰值空间、DFDC/FakeAVCeleb 权限、权重完整性、学习率口径、随机性、预处理失败规则与可接受复现误差等未知，并为多数关键未知提供门禁检查、冒烟测试和短训练标定等低成本验证路径。 |
| 风险完整性 | 2 | 风险覆盖数据/磁盘、时间、论文—代码参数差异、旧环境重建、显存和指标口径，并明确区分高风险/中高风险/中风险，满足基本优先级排序要求。 |
| 行动可执行性 | 2 | 三步行动按照依赖顺序组织为资源与授权 Gate → 官方权重+极小数据端到端冒烟测试 → 1–3 epoch 短训练标定，并给出具体检查对象、测量项与进入全量训练的条件。 |

## Dimension-level Observations

Strongest Dimension:
关键缺失 / 阻塞识别与行动可执行性（并列）。Codex 不仅覆盖了环境、数据、磁盘、显存、权重、时间和评测口径，还把这些未知映射为明确的 Gate、冒烟测试和短训练标定。

Weakest Dimension:
在 Baseline Rubric V1 的 0/1/2 锚点下，没有明显低于 2 分的质量维度。相对需要后续审计的是“证据准确性”本身：本 Scorecard 评价的是可追溯性和结构化程度，并未独立复核 Codex 输出中的每一条技术事实或行号是否完全正确。

Critical Decision Breakpoint:
None under Baseline Rubric V1.

需要单独保留的过程限制：
- Codex App 的精确内部 Search Count、Material Switch Count、Repository Lookup Count 和 Tool Count 不完全可观察。
- C 需要 5 分钟 Pre-test Setup Cost（clone + checkout + open project）；该成本不计入 Formal Decision Time，但后续效率比较必须单独报告。

Notes:
- 本 Scorecard 仅依据冻结的 Baseline Rubric V1 对 Baseline C 的实际输出与过程记录评分。
- 不因 Codex 属于代码工具而放宽或提高评分标准。
- 不使用单一总分替代维度级分析。
- Formal Decision Time = 7 minutes，User Follow-up Count = 0。
- Additional Codex Setup Cost = 5 minutes。
