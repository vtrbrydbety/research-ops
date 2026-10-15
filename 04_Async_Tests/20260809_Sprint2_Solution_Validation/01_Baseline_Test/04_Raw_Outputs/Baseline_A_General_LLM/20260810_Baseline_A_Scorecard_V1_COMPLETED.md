# Baseline Scorecard

Template ID: Baseline_Scorecard_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

Baseline:
Baseline A｜通用大模型自由对话

Raw Record:
20260810_Baseline_A_Record_V1_COMPLETED.md

Rubric:
20260810_Baseline_Rubric_V1.md

| 质量维度 | Score | Evidence / Scoring Rationale |
|---|---:|---|
| 决策完整性 | 2 | 明确给出“有条件继续”，并把该决策与 3 天时间预算、367 GB 可用磁盘、环境未知、数据权限未知等约束联系起来；同时明确“不立即投入全量训练”，决策条件清晰。 |
| 关键缺失 / 阻塞识别 | 2 | 识别了 Driver、DFDC 权限、Python/Conda/PyTorch/CUDA、实际峰值显存、预处理磁盘占用、预处理与训练时间等高影响未知和阻塞。 |
| 证据可追溯性 | 2 | 关键判断给出了可定位来源，包括 BMVC 2024 正式论文、FGI 固定 Commit、README、package-list.txt、my_train.py、dataset_3d.py、write_csv.py、pre-process.py、数据划分列表及 Kaggle 官方页面；并区分“已确认 / 未知 / 冲突”。 |
| 未知项处理 | 2 | 明确列出 14 项未知，没有把未知直接写成事实；并在前三步行动中给出环境核对、数据/磁盘测量、最小闭环验证等补齐路径。 |
| 风险完整性 | 2 | 覆盖数据/磁盘、环境、算力、代码路径一致性、论文与代码超参数冲突、三天时间预算等主要风险，并将数据与磁盘明确标为当前最主要现实风险。 |
| 行动可执行性 | 2 | 三步行动按依赖顺序组织为环境 Gate → 数据与磁盘 Gate → 最小 baseline 闭环，并给出了可立即执行的核查对象和具体操作方向。 |

## Dimension-level Observations

Strongest Dimension:
未知项处理（并列：证据可追溯性）。输出对“已确认 / 未知 / 冲突”的区分较清楚，并给出了对应验证路径。

Weakest Dimension:
在 Baseline Rubric V1 的 0/1/2 锚点下，没有出现明显低于 2 分的质量维度。相对而言，证据虽然可定位到具体论文、页面和源码文件，但并非所有结论都提供到行级/代码位置级引用，因此后续若做更严格的“判断准确性审计”，仍应独立核验。

Critical Decision Breakpoint:
None under Baseline Rubric V1.

需要单独保留的过程限制：
A 的内部搜索次数、材料切换次数和具体检索路径不可完全观察；该限制属于时间/交互成本记录问题，不直接降低本 Scorecard 的质量分。

Notes:
- 本 Scorecard 仅依据冻结的 Baseline Rubric V1 对 Baseline A 的实际输出进行评分。
- 本次评分不等同于对 A 输出中每一条技术事实进行独立外部复核。
- 不使用单一总分替代维度级分析。
- Baseline A 本次耗时 5 分钟，User Follow-up Count = 0；这些属于效率/交互成本记录，不计入质量评分。
