# ResearchOps 项目结构

> 更新日期：2026-09-09
> 当前阶段：**Sprint 2 已完成；Gate 2 = CONDITIONAL；真实 Concept Test 延后至 Sprint 3 MVP Alpha 后执行；Sprint 3 Handoff 已完成（HANDOFF READY）。** PRD V0.9、Figma Prototype V3.6 与现有产品定义继续冻结；Sprint 3 将以“复现前准备度评估”为唯一 P0 主路径，优先实现最小可运行 MVP。

## 核心目录

| 目录 | 用途 | 当前状态 |
|---|---|---|
| `00_Project_Admin/` | 项目计划、研究问题、证据索引与每日记录 | 持续维护；Day 6 日志已归档 |
| `01_FGI_Founder_Case/` | FGI 创始用户真实复现过程证据 | 原始过程材料保留 |
| `02_Questionnaire/` | 问卷基线、预测试、正式收集与样本处理 | 原始数据与工作副本隔离 |
| `03_Public_Cases/` | 20 条公开失败案例、案例卡与来源留档 | 已冻结（C-001—C-020） |
| `04_Async_Tests/` | 后续异步任务与行为验证材料 | Sprint 2 Baseline A / B / C 已完成；真实 Concept Test 延后至 Sprint 3 MVP Alpha 后执行 |
| `05_Analysis_and_Decisions/` | 统计、编码、证据矩阵、研究简报、痛点池与 Gate 决策 | Sprint 2 分析、Prototype Review、Dry-run 与 Prototype Freeze 已完成；Gate 2 = CONDITIONAL；Sprint 3 Handoff 已完成 |
| `06_Product_Versions/` | 产品版本与原型材料 | Sprint 2 产品定义与 Figma Prototype V3.6 已完成并冻结；保留当前 HTML 快照和插件包 |

## 当前目录树

以下仅列正式研究目录和关键交付物；`.codex-*`、`.qa/`、`outputs/`、检查缓存及 Office 临时文件不属于正式证据结构。

```text
ResearchOps/
├─ PROJECT_STRUCTURE.md
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
│  └─ 20260809_Sprint2_Solution_Validation/
│     ├─ 01_Baseline_Test/
│     │  ├─ 01_Protocol/
│     │  │  ├─ 20260809_Sprint2_Start_Brief_V1_FREEZE.docx
│     │  │  ├─ 20260809_Baseline_Test_Protocol_V1.docx
│     │  │  ├─ 20260810_Baseline_Rubric_V1.md
│     │  │  ├─ 20260810_H2_H3_Preregistration_V1.md
│     │  │  └─ Archive/
│     │  ├─ 02_Input_Pack/
│     │  │  └─ 20260809_FGI_Baseline_Input_Pack_V1/
│     │  │     ├─ 00_Manifest/
│     │  │     │  └─ 20260810_FGI_Baseline_Input_Pack_Manifest_V1.md
│     │  │     └─ 01_User_Constraints/
│     │  │        └─ 20260810_User_Constraints_V1.md
│     │  ├─ 03_Record_Templates/
│     │  │  ├─ 20260810_Baseline_Scorecard_V1.md
│     │  │  └─ 20260810_Decision_Log_V1.md
│     │  └─ 04_Raw_Outputs/
│     │     ├─ Baseline_A_General_LLM/
│     │     ├─ Baseline_B_Manual_Workflow/
│     │     └─ Baseline_C_Codex/
│     └─ 02_Concept_Test/
│        ├─ 01_Protocol/
│        └─ 02_Raw_Records/
├─ 05_Analysis_and_Decisions/
│  ├─ 20260805_Day5_Evidence_Pack/
│  │  ├─ 01_Sample_Statistics/
│  │  ├─ 02_Open_Text_Coding/
│  │  ├─ 03_Public_Case_Analysis/
│  │  ├─ 04_Hypothesis_Evidence/
│  │  ├─ 05_Research_Brief/
│  │  └─ 06_Pain_Point_Pool/
│  ├─ 20260806_Day6_Gate1_Decision_Pack/
│  │  ├─ 01_Input_Audit/
│  │  ├─ 02_Hypothesis_Decisions/
│  │  ├─ 03_Pain_Point_Priority/
│  │  ├─ 04_Problem_Definition/
│  │  └─ 05_Gate1_Decision/
│  └─ 20260809_Sprint2_Solution_Validation_Pack/
│     ├─ 01_Baseline_Analysis/
│     │  ├─ 20260810_Baseline_ABC_Decision_Breakpoint_Comparison_V1.md
│     │  └─ 20260810_Baseline_Decision_Log_V1_COMPLETED.md
│     ├─ 02_Opportunity_and_Readiness/
│     │  └─ 20260810_Opportunity_Readiness_Analysis_V1_COMPLETED.md
│     └─ 03_Gate2_and_Handoff/
│        ├─ Gate2_Decision_V1.md
│        ├─ Sprint3_Handoff_V1.md
│        ├─ 01_Prototype_Review/
│        │  ├─ Dry_run_Record_V1.md
│        │  └─ Prototype_Review_Notes_V1.md
│        ├─ 02_Concept_Test/
│        │  ├─ Concept_Test_Plan_V1.md
│        │  └─ Raw_Records/
│        │     ├─ Participant_P01.md
│        │     ├─ Participant_P02.md
│        │     └─ Participant_P03.md
│        └─ 03_Prototype_Freeze/
│           └─ Prototype_Freeze_Record_V1.md
└─ 06_Product_Versions/
   └─ 20260809_Sprint2/
      ├─ 01_PRD/
      │  ├─ 20260826_PRD_V0.8.docx
      │  ├─ 20260826_PRD_V0.9.docx
      │  └─ ResearchOps_PRD_V0.8_to_V0.9_Change_List_Audit_V1.0.docx
      ├─ 02_Product_Spec/
      │  ├─ 20260826_Readiness_Dimension_Definition_V1.md
      │  ├─ 20260826_Information_Architecture_V1.md
      │  ├─ 20260826_Field_Dictionary_V1.md
      │  ├─ 20260826_Output_Schema_V1.json
      │  ├─ 20260826_Event_Tracking_Plan_V1.md
      │  ├─ 20260826_Safety_Boundary_V1.md
      │  └─ 20260826_D5_Figma_Handoff_V1.md
      └─ 03_Figma/
         ├─ 01_Prototype/
         │  └─ Prototype_State_Checklist_V1.md
         ├─ 02_Field_Mapping/
         │  └─ Figma_Field_Map_V1.md
         ├─ 03_Handoff/
         │  ├─ Figma_Change_Request_V1.md
         │  └─ Figma_Freeze_Record_V1.md
         ├─ ResearchOps_FROZEN_HTML_V3.6.html
         ├─ ResearchOps_FROZEN_HTML_V3.6_REVISION.html
         ├─ RO_V36_FINAL/
         ├─ RO_V36_FINAL_CLEANUP_V4/
         └─ RO_V36_FINAL_CLEANUP_V4.zip
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

### Sprint 2 Baseline Test 与分析

测试位置：`04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/`
分析位置：`05_Analysis_and_Decisions/20260809_Sprint2_Solution_Validation_Pack/`

| 交付物 | 当前状态 |
|---|---|
| Start Brief、Baseline Test Protocol、Rubric V1 | 已形成；Start Brief 已冻结 |
| FGI Baseline Input Pack V1 | 已冻结统一输入材料包及 Manifest |
| H2 / H3 Preregistration V1 | 已冻结正式实验条件；当前不记录实验结果，也不代表 H2 / H3 已通过 |
| Baseline A｜通用大模型自由对话 | 已完成 Raw Conversation、Record、Time Log 与 Scorecard |
| Baseline B｜人工现有流程 | 已完成 Record、Time Log 与 Scorecard |
| Baseline C｜Codex | 已完成 Raw Conversation、Record、Time Log 与 Scorecard |
| A / B / C Decision Breakpoint Comparison | 已完成；保留 Rubric V1 原分数及 ceiling effect 结论，并完成七个决策阶段的 A / B / C 表现、用户影响与证据文件映射 |
| Baseline Decision Log | 已完成；D-001—D-007 已补齐完整证据文件与章节定位，保留 B 的“信息发现 → 结构化决策转换不足”断点 |
| Opportunity / Readiness Analysis | 已完成；Opportunity 双证据 ID、三级冻结、Non-goals 与 Safety Boundary 已形成 D4 Handoff 输入与交接口径；相关内容分布于 § 7.2–§ 7.6，并继承 § 5.5 的 Non-goals |
| 独立 D4 Handoff 交付物 | 尚未建立；当前 Handoff 输入内嵌于 Opportunity / Readiness Analysis § 7.2–§ 7.6，并继承 § 5.5 的 Non-goals |
| Prototype Review 与 Prototype Freeze | Internal Dry-run、Prototype Review 与 Prototype Freeze 已完成；Figma Prototype V3.6 当前继续冻结 |
| 真实 Concept Test | 本轮不执行；现有 Concept Test Plan 与 P01—P03 Participant Record 保留，延后至 Sprint 3 MVP Alpha 能处理真实 Paper / Repository 后执行 |
| Gate 2 | **CONDITIONAL — Product Definition & Prototype Ready, Real-user Validation Deferred**；不代表 H2 / H3 已通过，也不代表产品已完成真实用户验证 |
| Sprint 3 Handoff | 已完成；`Sprint3_Handoff_V1.md` 状态为 **HANDOFF READY**，进入最小可运行 Reproduction Readiness Assessment MVP 实现阶段 |

### Sprint 2 产品定义、Figma Prototype 与 D5 Handoff

位置：`06_Product_Versions/20260809_Sprint2/`

| 交付物 | 当前状态 |
|---|---|
| PRD V0.8 | 已保留为上一版产品需求文档 |
| PRD V0.9 | 当前产品需求版本；已完成 Day 4 收敛 |
| PRD V0.8 → V0.9 Change List Audit V1.0 | 已形成版本变化与审计记录 |
| Readiness Dimension Definition V1 | 已冻结 MVP Concept Design：RD-01、RD-02、RD-03 三个核心 Dimension |
| Information Architecture V1 | 已完成 Day 4 产品信息架构 |
| Field Dictionary V1 | 已完成 Day 4 字段定义 |
| Output Schema V1 | 已形成与字段字典对应的机器可读输出结构 |
| Event Tracking Plan V1 | 已完成 Concept Test 最小事件与观察项定义 |
| Safety Boundary V1 | 已冻结当前 MVP 授权后只读、不写入、不执行的安全边界 |
| D5 Figma Handoff V1 | 已完成，并已用于 Figma Prototype V3.6 的设计与冻结；真实 Concept Test 按 Gate 2 决策延后至 Sprint 3 MVP Alpha 后执行 |
| Day 4 产品链路一致性复核 | PRD → IA → Field Dictionary → Output Schema → Event Tracking → Safety Boundary → D5 Figma Handoff 的本轮 P1 问题已全部关闭；未发现新增 P0 冲突 |
| Figma Prototype V3.6 | 已形成 Prototype State Checklist、Field Map、Change Request 与 Freeze Record；冻结记录标记为 `Ready for Freeze`，并记录冻结 V3.6 的决定 |
| HTML 与插件交付快照 | 已保留 V3.6 HTML 与 Revision 快照，以及 `RO_V36_FINAL/`、`RO_V36_FINAL_CLEANUP_V4/` 和对应 ZIP 包 |

## Gate 2 与 Sprint 3 Handoff

- Sprint 2 已完成，当前 Gate 2 决策为 **CONDITIONAL**。
- 产品定义与高保真原型已具备进入实现阶段的条件，但尚未完成真实用户 Concept Test，也尚未用可运行 MVP 验证真实 Readiness 判断能力。
- 真实 Concept Test 延后至 Sprint 3 MVP Alpha 后执行；届时使用真实 Paper / Repository 输入验证 Overall Gate、Main Risk、Evidence 与 First Next Action。
- Sprint 3 Handoff 已完成，状态为 **HANDOFF READY**；默认继承 PRD V0.9、Figma Prototype V3.6、三核心 Dimension、四种 Status、三种 Overall Gate 与 Authorized Read-only Safety Boundary。
- Gate 2 升级为 PASS 的条件将在 MVP Alpha 与真实用户验证完成后重新评估。

## Gate 1 后的产品边界

- Gate 1 结论：**CONDITIONAL PASS（有条件通过）**，允许进入 Sprint 2。
- Sprint 2 已完成；Gate 2 结论为 **CONDITIONAL**，允许进入 Sprint 3 MVP Alpha 实现，但不等同于真实用户验证通过。
- 唯一 P0 主路径：复现前准备度评估，统一覆盖 P07（证据链）、P01（数据与权限）、P02（依赖与环境）、P03（权重与配置）。
- H1：支持；H4：部分支持，需保留安全约束；H6：仅在分享意愿层面获得阶段性支持。
- P04 资源需求、P05 运行后诊断为 P1；P06 评测口径为 P2 / 继续观察。
- 自动完整复现、训练调参、GPU 调度、复杂团队协作、多 Agent / MCP 平台化和通用科研项目管理均不进入首版核心范围。
- 当前 MVP 产品机会收敛为 `Structured Readiness Card`、`Evidence-linked Findings`、`Next Action / Gate`。
- 三个 MVP 模块描述产品结构；`Structured Readiness Card` 统一承载复现前准备度的核心检查维度与状态。Day 4 已通过 Sprint 1 Evidence × Baseline Breakpoint 双证据映射，将核心 Dimension 冻结为 RD-01 `Data & Access Readiness`、RD-02 `Environment & Dependency Readiness`、RD-03 `Weights & Configuration Readiness`，并继续使用 `Ready / Warning / Blocked / Unknown` 四种状态语义。
- Resource Constraint 与 Evaluation Conflict 保持为辅助 Signal，不升级为新的核心 Dimension；Overall Gate 固定为 `PROCEED / CONDITIONAL PROCEED / PAUSE`，不采用平均分、多数投票或加权总分。
- `Evidence-linked Findings` 的定位是将关键判断与论文、README 或源码依据以统一产品结构呈现，降低定位和核对成本；不把 citation 本身宣称为独有能力。
- Safety Boundary 继续继承 Start Brief 与 Baseline Protocol：高风险执行、删除、覆盖及授权类操作必须经过人工确认；当前 MVP 只输出准备度判断、证据与行动建议，不自动执行复现或实施高风险操作。
- `Persistent State`、`Decision Update`、`Collaboration / Handoff` 与完整历史审计属于 Future Roadmap，不作为当前 MVP 必须验证的能力。
- Sprint 3 优先跑通真实输入到结构化 Readiness 判断的最小闭环；真实 Concept Test 在 MVP Alpha 后恢复执行，在此之前不宣称 H2 / H3 已通过。

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


## 2026-10-16 工程发布补充

- `04_Async_Tests/`：异步验证和基线实验资料。
- `06_Product_Versions/`：产品与原型基线；保持现有目录命名。
- `07_ResearchOps_Agent/`：由独立应用仓库导入的实际源码，不是 Git submodule。包含 apps、researchops、tests、docs、openspec 与部署模板。
- 根目录 `README.md` 为项目导航；应用安装、配置和运行步骤见 `07_ResearchOps_Agent/README.md`。
- `.env.example` 为无秘密的配置示例；实际 `.env`、邀请码、评估数据、隧道凭证和临时目录不随源码发布。

本次发布以应用提交 `6f1ee33` 为来源快照，不导入应用独立仓库的 Git 历史。本地运行目录保持原路径，发布目录命名不影响正在运行的 macOS 服务。
