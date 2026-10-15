# Baseline Scorecard

Template ID: Baseline_Scorecard_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

Baseline:
Baseline B｜人工现有流程

Raw Record:
20260810_Baseline_B_Record_V1_COMPLETED.md

Rubric:
20260810_Baseline_Rubric_V1.md

| 质量维度 | Score | Evidence / Scoring Rationale |
|---|---:|---|
| 决策完整性 | 2 | 明确给出“有条件继续”，并通过“训练集具体分块/大小未知”与“367 GB 可用磁盘小于记录到的 DFDC 总体积”解释继续的限制条件；最终决策与本轮实际发现的材料和用户存储约束一致。 |
| 关键缺失 / 阻塞识别 | 1 | 识别了训练集分块/大小和磁盘容量这一组高影响问题，但最终六字段没有纳入测试过程中已接触到的环境依赖、DFDC 权限、训练/测试参数核对等其他重要准备项，因此存在明显遗漏。 |
| 证据可追溯性 | 1 | “官方 Kaggle + User Hardware Constraints: Available Disk Space”能够支持磁盘风险的主要方向，但来源定位较粗；对训练集分块/大小未知等判断没有给出更具体的文件、页面或材料位置，部分关键结论缺乏可定位依据。 |
| 未知项处理 | 1 | 明确将“训练集具体分块信息和大小”标记为未知，没有直接补造事实；但没有给出足够明确、最小化的验证路径，只写“查看是否能知道”，且其他已暴露的未知没有进入最终未知项列表。 |
| 风险完整性 | 1 | 识别了数据/磁盘这一主要风险，但最终结果没有覆盖环境兼容性、数据权限、权重、算力/显存、评测闭环等其他可能影响复现准备判断的重要风险，覆盖明显不完整。 |
| 行动可执行性 | 1 | 三步行动有基本顺序：确认数据分块/大小 → 腾出磁盘 → 提取训练集并预处理；但第 2 步默认“需要下载整个数据集”，该前提在本轮仍未证实，同时没有优先处理数据权限、环境等前置条件，因此只能评为部分可执行。 |

## Dimension-level Observations

Strongest Dimension:
决策完整性。Baseline B 能够在 60 分钟内形成明确的“有条件继续”结论，并把当前最显著的数据/存储问题反映到最终决策中。

Weakest Dimension:
关键缺失 / 阻塞识别、风险完整性、未知项处理与证据可追溯性均存在明显不足。最突出的问题不是完全没有发现信息，而是最终六字段没有把测试过程中已经接触到的多类信息完整转化为决策要素。

Critical Decision Breakpoint:
“信息发现 → 结构化决策”转换不足。

Time / Interaction Log 显示，人工流程在测试过程中已经查看 package-list.txt、DFDC 获取要求、训练脚本、测试脚本，并发现部分训练参数需要论文补充；但最终输出主要收敛到“训练集分块/大小 + 磁盘空间”这一条问题链。也就是说，人工流程能够找到不少信息，却没有在有限时间内把环境、权限、配置/参数、评测路径等信息系统地汇总为完整的缺失项、风险和未知项。

Notes:
- 本 Scorecard 仅依据冻结的 Baseline Rubric V1 和 Baseline B 的实际最终输出/过程记录评分。
- 不把 56 分钟耗时、4 次显式 Search、3 次显式 Material Switch 直接折算为质量分。
- Search Count / Material Switch Count 的统计口径按原 Time / Interaction Log 保留。
- 不使用单一总分替代维度级断点分析。
