# ResearchOps 项目结构

> 更新日期：2026-08-09  
> 当前阶段：Gate 1 已完成，结论为 **CONDITIONAL PASS（有条件通过）**；项目获准进入 Sprint 2，但继续以“复现前准备度评估”为唯一 P0 主路径。

## 核心目录

| 目录 | 用途 | 当前状态 |
|---|---|---|
| `00_Project_Admin/` | 项目计划、研究问题、证据索引与每日记录 | 持续维护；Day 6 日志已归档 |
| `01_FGI_Founder_Case/` | FGI 创始用户真实复现过程证据 | 原始过程材料保留 |
| `02_Questionnaire/` | 问卷基线、预测试、正式收集与样本处理 | 原始数据与工作副本隔离 |
| `03_Public_Cases/` | 20 条公开失败案例、案例卡与来源留档 | 已冻结（C-001—C-020） |
| `04_Async_Tests/` | 后续异步任务与行为验证材料 | 预留；Sprint 2 待启用 |
| `05_Analysis_and_Decisions/` | 统计、编码、证据矩阵、研究简报、痛点池与 Gate 决策 | Day 5 证据包和 Day 6 Gate 1 决策包已归档 |
| `06_Product_Versions/` | 产品版本与原型材料 | 预留 |

## 当前目录树

以下仅列正式研究目录和关键交付物；`.codex-*`、`.qa/`、`outputs/`、检查缓存及 Office 临时文件不属于正式证据结构。

```text
ResearchOps/
├─ PROJECT_STRUCTURE.md
├─ 20260805_Public_Cases_V0.1.md
├─ 00_Project_Admin/
│  ├─ 20260801_Evidence_Index_V1.xlsx
│  ├─ 20260801_ResearchQuestions_V1.xlsx
│  ├─ 20260801_DayLog_V1.md … 20260806_DayLog_V1.md
│  └─ 20260805_Questionnaire_Closure_Record_V1.md
├─ 01_FGI_Founder_Case/
│  ├─ 20260801_FGI_Timeline_V1.xlsx
│  └─ 02_Data_and_Weights/
├─ 02_Questionnaire/
│  ├─ 20260803_Pilot_and_Revision/
│  │  ├─ 01_Baseline/
│  │  ├─ 02_Virtual_Precheck/
│  │  ├─ 03_Real_Pilot/
│  │  ├─ 04_Issue_Log/
│  │  └─ 05_V0.2_Release/
│  ├─ 20260804_Formal_Collection/
│  │  ├─ 01_Release_Snapshot/
│  │  ├─ 02_Raw_Backups/
│  │  ├─ 03_Collection_Evidence/
│  │  └─ 04_Final_Processing/
│  │     ├─ 01_Original_ReadOnly/
│  │     ├─ 02_Working_Copy/
│  │     └─ 03_Sample_Screening/
│  └─ Questionnaire_Evidence/
├─ 03_Public_Cases/
│  ├─ Public_Cases_Master.xlsx
│  ├─ FREEZE.md
│  ├─ Case_Cards/             # C-001—C-020 的案例卡
│  └─ Source_Archive/         # C-001—C-020 的公开来源留档
├─ 04_Async_Tests/
├─ 05_Analysis_and_Decisions/
│  ├─ 20260805_Day5_Evidence_Pack/
│  │  ├─ 01_Sample_Statistics/
│  │  ├─ 02_Open_Text_Coding/
│  │  ├─ 03_Public_Case_Analysis/
│  │  ├─ 04_Hypothesis_Evidence/
│  │  ├─ 05_Research_Brief/
│  │  └─ 06_Pain_Point_Pool/
│  └─ 20260806_Day6_Gate1_Decision_Pack/
│     ├─ 01_Input_Audit/
│     ├─ 02_Hypothesis_Decisions/
│     ├─ 03_Pain_Point_Priority/
│     ├─ 04_Problem_Definition/
│     └─ 05_Gate1_Decision/
└─ 06_Product_Versions/
```

## 原始证据冻结边界

| 证据类型 | 原始材料位置 | 隔离方式 | 当前状态 |
|---|---|---|---|
| 正式问卷原始数据 | `02_Questionnaire/20260804_Formal_Collection/04_Final_Processing/01_Original_ReadOnly/20260805_Formal_Samples_Final_Raw.xlsx` | 分析仅使用 `02_Working_Copy/` 中的工作副本 | 已保留，原始文件不覆盖 |
| 真实预测试数据 | `02_Questionnaire/20260803_Pilot_and_Revision/03_Real_Pilot/` | 与虚拟预检查、正式问卷物理分开 | 已保留 |
| 虚拟用户数据 | `02_Questionnaire/20260803_Pilot_and_Revision/02_Virtual_Precheck/` | 与真实预测试物理分开，仅用于预检查 | 已保留 |
| 20 条公开案例原始材料 | `03_Public_Cases/Public_Cases_Master.xlsx`、`Case_Cards/`、`Source_Archive/` | 后续审计和分析使用独立副本，不回写原始案例库 | 已冻结；C-001—C-020 均保留来源材料 |
| FGI 创始用户复现材料 | `01_FGI_Founder_Case/20260801_FGI_Timeline_V1.xlsx` 及 `02_Data_and_Weights/` | 仅作过程证据，不纳入问卷或公开案例频率分母 | 已保留 |

> 说明：`03_Public_Cases/FGI_Case_Cards/` 与 `03_Public_Cases/GitHub_Issues/` 是未使用的早期空目录，不属于正式证据结构，故未列入本目录树。FGI 材料以 `01_FGI_Founder_Case/` 为准；公开 GitHub 来源以 `03_Public_Cases/Source_Archive/` 为准。

### 原始文件校验记录

- 正式问卷原始文件 SHA-256：`C3C7B00A8B483090BAB2418648F1AB95C345FF8DA015646DD36676B031F8E095`
- 公开案例主库 SHA-256：`32D6D6170A36C52B2607237B4807F11633BE1D8419BCE73BD96623BD3DB1BF38`
- 2026-08-08 复核：以上两个校验值与既有记录一致。

## 阶段交付物

### Day 5 Evidence Pack

位置：`05_Analysis_and_Decisions/20260805_Day5_Evidence_Pack/`

| 子目录 | 内容 |
|---|---|
| `01_Sample_Statistics/` | 核心指标与样本画像统计工作簿 |
| `02_Open_Text_Coding/` | Q17 开放回答统一编码工作簿 |
| `03_Public_Case_Analysis/` | 公开案例审计、统一编码与 H5 覆盖分析 |
| `04_Hypothesis_Evidence/` | H1 / H4 / H5 / H6 多源证据矩阵 |
| `05_Research_Brief/` | 阶段研究简报 V0.1、V0.2 |
| `06_Pain_Point_Pool/` | 初步痛点池 V0.1 |

### Day 6 Gate 1 Decision Pack

位置：`05_Analysis_and_Decisions/20260806_Day6_Gate1_Decision_Pack/`

| 子目录 | 内容 |
|---|---|
| `01_Input_Audit/` | Gate 1 输入审计 |
| `02_Hypothesis_Decisions/` | H1 / H4 / H6 阶段决策 |
| `03_Pain_Point_Priority/` | 痛点优先级与范围收敛 |
| `04_Problem_Definition/` | 已冻结的问题定义 |
| `05_Gate1_Decision/` | Gate 1 最终决策记录 |

## Gate 1 后的产品边界

- Gate 1 结论：**CONDITIONAL PASS（有条件通过）**，允许进入 Sprint 2。
- 唯一 P0 主路径：复现前准备度评估，统一覆盖 P07（证据链）、P01（数据与权限）、P02（依赖与环境）、P03（权重与配置）。
- H1：支持；H4：部分支持，需保留安全约束；H6：仅在分享意愿层面获得阶段性支持。
- P04 资源需求、P05 运行后诊断为 P1；P06 评测口径为 P2 / 继续观察。
- 自动完整复现、训练调参、GPU 调度、复杂团队协作、多 Agent / MCP 平台化和通用科研项目管理均不进入首版核心范围。
- Sprint 2 必须验证准备度报告的真实决策价值、判断准确性与可解释性，以及相对 README、GitHub Issue、搜索和通用大模型的增量价值。

## 分析口径与解释边界

- 正式问卷有效样本为 `N_user = 20`；公开有效案例为 `N_case_valid = 20`。两者分析单位不同，不得混用。
- 公开案例用于证明问题存在、支持案例编码与覆盖分析，不用于推断用户问题发生率。
- FGI 创始用户案例用于补充可追溯的复现过程证据，不计入频率统计。
- Gate 1 结论是当前探索阶段的产品方向判断，不代表产品效果已经验证。
- H4 的真实授权行为、H6 的真实分享与协同行为仍需后续异步任务验证。

## 目录维护规则

1. 原始数据只追加留档与校验信息，不直接修改内容。
2. 清洗、编码、统计和产品推断均在工作副本或 `05_Analysis_and_Decisions/` 下完成。
3. 每个新阶段使用独立交付包，不覆盖前一阶段的证据或结论文件。
4. 新增正式交付物应归入对应阶段和子目录，并保留日期与版本号。
5. 临时输出、运行缓存、检查文件、Office 锁文件和工具生成文件不属于正式证据目录。
6. 新证据若改变目标用户、P0 问题或产品边界，必须记录“原结论 → 新证据 → 调整内容 → 影响范围”。
