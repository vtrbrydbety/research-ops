# ResearchOps Field Dictionary V1

**Document ID：** `20260826_Field_Dictionary_V1`  
**Version：** V1  
**Date：** 2026-08-26 
**Status：** COMPLETED FOR SPRINT 2 DAY 4  
**Stage：** Sprint 2 · Day 4 · Product Specification  
**Product：** ResearchOps


## 1. 文档目的与边界

本文件将 PRD、Readiness Definition 与 Information Architecture 已冻结的业务对象落到字段级，供后续 **Output Schema、Figma Handoff 与 Concept Test 原型**使用。

只定义当前 MVP 必需的：
- 字段、类型、必填性；
- 核心枚举与业务约束；
- 对象之间的引用关系。

不承担数据库、API、权限治理、SLA、数据血缘等企业级设计；当前 MVP 仍为**授权范围内只读**，不执行安装、修改、删除、训练或高成本复现。

上游：`20260826_PRD_V0.9`、`20260826_Readiness_Dimension_Definition_V1`、`20260826_Information_Architecture_V1`。

---

## 2. 字段约定

- **Required**：对象形成后必须存在。
- **Conditional**：满足对应业务条件时必须存在。
- **Optional**：当前 MVP 可缺省。
- 常用类型：`String`、`Boolean`、`Integer`、`Enum<T>`、`Reference<T>`、`Array<T>`、`Object`。

核心对象关系：

> **Task → Target / Material / User Context → Readiness Result → Dimension → Finding → Evidence → Overall Gate → Next Action**

Resource / Evaluation 作为 Signal 进入 Readiness Result；Confirmation、Authorization、Feedback / Correction 为条件交互对象。

---

## 3. Context Objects

### 3.1 Task

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `task_id` | `String` | Required | 一次 Readiness Assessment 的唯一标识 |
| `reproduction_goal` | `String` | Required | 本次复现目标 |
| `target_ref` | `Reference<Target>` | Required | 当前评估对象 |
| `material_refs` | `Array<Reference<Material>>` | Conditional | 已发现并纳入分析的材料 |
| `user_context` | `Reference<UserContext>` | Conditional | 用户约束与实际执行环境 |
| `analysis_state` | `Enum<AnalysisState>` | Conditional | 非业务状态；不得替代 Readiness Status |
| `readiness_result_ref` | `Reference<ReadinessResult>` | Conditional | 当前阶段性 Readiness Result |
| `feedback_refs` | `Array<Reference<Feedback>>` | Conditional | 用户核对、质疑或修正记录 |

### 3.2 Target

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `target_id` | `String` | Required | Target 唯一标识 |
| `target_type` | `Enum<TargetType>` | Required | Paper / Repository / Project |
| `target_name` | `String` | Required | 用户可识别名称 |
| `source_entry` | `String` | Required | 用户最初提供的 Title / DOI / arXiv / Repository / Project Page 等入口 |
| `resolution_status` | `Enum<TargetResolutionStatus>` | Required | Target 当前识别状态；与 Readiness Status 分离 |
| `resolved_source` | `String` | Conditional | 最终确认采用的主要 Target / Source |

### 3.3 Material

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `material_id` | `String` | Required | Material 唯一标识 |
| `material_type` | `Enum<MaterialType>` | Required | 材料类型 |
| `source_locator` | `String` | Required | URL、repo path、document locator 等可重新定位入口 |
| `title` | `String` | Optional | 材料标题 / 文件名 |

> Material 是 Evidence 来源，不直接产生 Ready / Warning / Blocked / Unknown。

### 3.4 User Context / Execution Environment

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `execution_target` | `String` | Conditional | 本次复现实际计划执行的环境 |
| `input_mode` | `Enum<EnvironmentInputMode>` | Conditional | Read-only Detection / Snapshot / Manual Input |
| `acquisition_state` | `Enum<EnvironmentAcquisitionState>` | Required | 环境信息获取状态，不是 Readiness Status |
| `os` | `String` | Conditional | 操作系统 |
| `python_version` | `String` | Conditional | Python 版本 |
| `framework` | `String` | Conditional | Framework 及版本 |
| `cuda_version` | `String` | Conditional | CUDA 版本 |
| `driver_version` | `String` | Conditional | GPU Driver 版本 |
| `gpu_vram` | `String` | Conditional | GPU 型号 / 显存事实 |
| `disk_available` | `String` | Conditional | 当前可写磁盘空间 |
| `time_budget` | `String` | Conditional | 用户提供的时间预算 |
| `user_provided_facts` | `Array<String>` | Optional | 用户主动提供、可能影响判断的事实或限制，如数据权限、checkpoint 状态、已知冲突 |

---

## 4. Readiness Judgment Objects

### 4.1 Readiness Result

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `result_id` | `String` | Required | 当前 Readiness Result 标识 |
| `dimension_refs` | `Array<Reference<Dimension>>` | Required | RD-01 / RD-02 / RD-03 |
| `resource_signal_ref` | `Reference<ResourceConstraintSignal>` | Conditional | materially relevant 的 P04-light Signal |
| `evaluation_signal_ref` | `Reference<EvaluationConflictSignal>` | Conditional | 当前 P06-light Signal |
| `overall_gate_ref` | `Reference<OverallGate>` | Required | 当前 Overall Gate 对象 |
| `prioritized_action_refs` | `Array<Reference<NextAction>>` | Conditional | 排序后的 Next Action；PAUSE / CONDITIONAL PROCEED 至少一项 |

### 4.2 Dimension

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `dimension_id` | `Enum<DimensionID>` | Required | RD-01 / RD-02 / RD-03 |
| `dimension_name` | `String` | Required | 与 Dimension ID 固定映射 |
| `analysis_state` | `Enum<AnalysisState>` | Conditional | 尚未形成业务判断时记录 Processing / Acquisition Failure 等状态 |
| `status` | `Enum<DimensionStatus>` | Conditional | 已形成业务判断后填写；不得用 Processing 代替 |
| `status_explanation` | `String` | Conditional | Status 已形成后解释原因 |
| `finding_refs` | `Array<Reference<Finding>>` | Conditional | 已形成判断后关联 Finding / Unknown |
| `gate_impact` | `String` | Conditional | 对 Overall Gate 的实际影响 |

> `Processing ≠ Unknown`。Partial Result 场景下，已完成 Dimension 使用 `status`，未完成 Dimension 使用 `analysis_state`。

### 4.3 Finding

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `finding_id` | `String` | Required | Finding 唯一标识 |
| `condition` | `String` | Required | 当前检查条件 |
| `summary` | `String` | Required | 当前结构化判断 |
| `finding_type` | `Enum<FindingType>` | Required | Fact / Inference / Unknown |
| `primary_dimension` | `Enum<DimensionID>` | Required | 唯一主归属 Dimension |
| `related_dimensions` | `Array<Enum<DimensionID>>` | Optional | 其他真实相关 Dimension |
| `gate_critical` | `Boolean` | Required | 是否可形成关键 Gate Impact |
| `gate_impact` | `String` | Conditional | 对 Dimension / Overall Gate 的影响 |
| `evidence_refs` | `Array<Reference<Evidence>>` | Conditional | 支持、解释或质疑 Finding 的 Evidence |
| `next_action_ref` | `Reference<NextAction>` | Conditional | 直接相关的 Next Action |

### 4.4 Evidence

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `evidence_id` | `String` | Required | Evidence 唯一标识 |
| `source_ref` | `Reference<Material/UserContext>` | Required | Material 或 User Context 来源 |
| `source_type` | `Enum<EvidenceSourceType>` | Required | Material / User Context |
| `location` | `String` | Conditional | Section / file / line / anchor / environment field 等位置 |
| `material_type` | `Enum<MaterialType>` | Conditional | Source 为 Material 时填写 |
| `summary` | `String` | Required | 与当前 Finding 直接相关的证据摘要 |
| `verification_status` | `Enum<EvidenceVerificationStatus>` | Required | Evidence 当前可核验程度 |
| `finding_ref` | `Reference<Finding>` | Required | 当前支持或质疑的 Finding |
| `conflict_note` | `String` | Optional | 多来源冲突摘要 |

V1 不建立数值 `confidence_score`；`verification_status` 已承接当前 Verification / Confidence 语义。

---

## 5. Decision Output Objects

### 5.1 Overall Gate

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `gate_id` | `String` | Required | Overall Gate 标识 |
| `gate_available` | `Boolean` | Required | 是否已具备形成 Gate 的基础 |
| `gate_value` | `Enum<OverallGateValue>` | Conditional | `gate_available = true` 时填写 |
| `gate_reason` | `String` | Conditional | 当前 Gate 的主要原因 |
| `trigger_refs` | `Array<Reference>` | Conditional | 触发 Gate 的 Dimension / Finding / Signal |

### 5.2 Next Action

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `action_id` | `String` | Required | Next Action 标识 |
| `action_type` | `Enum<NextActionType>` | Required | 五级优先级类型 |
| `action_summary` | `String` | Required | 用户下一步应做什么 |
| `priority` | `Integer` | Required | 当前 Action 排序，`1` 为 First Next Action |
| `reason_refs` | `Array<Reference>` | Required | 对应 Finding / Gate Reason |

### 5.3 Resource Constraint Signal

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `signal_id` | `String` | Required | Resource Signal 标识 |
| `status` | `Enum<ResourceSignalStatus>` | Required | Blocked / Warning / Unknown；不输出 Ready |
| `summary` | `String` | Required | 当前资源约束或不确定性 |
| `resource_items` | `Array<ResourceItem>` | Conditional | 按资源类别记录基础比较项 |
| `gate_impact` | `String` | Conditional | confirmed Resource Blocked 可触发 PAUSE |

`ResourceItem`：

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `resource_type` | `Enum<ResourceType>` | Required | GPU / VRAM / Disk / Time Budget |
| `stated_requirement` | `String` | Conditional | 来源明确写出的最低 / 必要要求 |
| `current_resource` | `String` | Conditional | 用户当前资源事实 |
| `requirement_source_ref` | `Reference<Material/Evidence>` | Conditional | 明确要求的来源 |
| `evidence_refs` | `Array<Reference<Evidence>>` | Conditional | 支撑该比较项的 Evidence |

> **P04-light 边界：** 不建立 `estimated_required_resource`，不精确预测完整磁盘需求、训练时长、GPU 成本或资源配置。Resource Blocked 仅在“明确最低要求已存在 + 当前资源已知 + 当前资源明确低于必要条件”时成立。

### 5.4 Evaluation Conflict Signal

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `signal_id` | `String` | Required | Evaluation Signal 标识 |
| `status` | `Enum<EvaluationSignalStatus>` | Required | 仅 Warning / Unknown |
| `conflict_type` | `Enum<EvaluationConflictType>` | Required | 评测冲突类别 |
| `summary` | `String` | Required | 已知冲突或不确定性 |
| `evidence_refs` | `Array<Reference<Evidence>>` | Conditional | 冲突来源 |
| `gate_impact` | `String` | Conditional | 当前不独立产生 P0 Blocked |

---

## 6. Conditional Interaction Objects

### 6.1 Confirmation

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `confirmation_id` | `String` | Required | Target / Source Confirmation 标识 |
| `candidate_refs` | `Array<Reference>` | Required | 待确认候选项 |
| `uncertainty_reason` | `String` | Required | 无法可靠静默选择的原因 |
| `user_decision` | `Enum<ConfirmationDecision>` | Conditional | Confirm / Supplement / Defer |
| `selected_candidate_ref` | `Reference<Target/Material>` | Conditional | 用户确认的 Target / Source |

### 6.2 Authorization

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `authorization_id` | `String` | Required | 读取授权标识 |
| `resource_scope` | `String` | Required | 当前申请读取范围 |
| `access_mode` | `Enum<AccessMode>` | Required | MVP 固定 Read-only |
| `authorization_status` | `Enum<AuthorizationStatus>` | Required | Authorized / Denied / Not Requested |
| `alternative_input` | `Enum<AlternativeInput>` | Conditional | Snapshot / Manual Input / None |

### 6.3 Feedback / Correction

| Field | Type | Required | Definition / Rule |
|---|---|---|---|
| `feedback_id` | `String` | Required | Feedback / Correction 标识 |
| `feedback_type` | `Enum<FeedbackType>` | Required | Confirm / Question / Correct / Add Evidence |
| `target_ref` | `Reference<Finding/Evidence>` | Required | 当前反馈对象 |
| `content` | `String` | Conditional | 用户补充、质疑或纠正内容 |
| `evidence_ref` | `Reference<Evidence>` | Conditional | 用户新增 Evidence |
| `requires_reassessment` | `Boolean` | Required | 是否需要重评受影响 Finding / Dimension / Result |

---

## 7. 核心枚举

| Enum | Allowed Values | Key Rule |
|---|---|---|
| `TargetType` | Paper / Repository / Project | Target 的归一化对象类型 |
| `DimensionID` | RD-01 / RD-02 / RD-03 | 固定三个核心 Dimension |
| `DimensionStatus` | Ready / Warning / Blocked / Unknown | Ready：足够正向 Evidence 支持关键条件基本满足；Warning：已知非阻塞风险；Blocked：明确 Evidence 证明必要条件不满足；Unknown：证据不足、缺失或冲突，无法可靠判断 |
| `OverallGateValue` | PROCEED / CONDITIONAL PROCEED / PAUSE | Gate 尚未形成由 `gate_available=false` 表达 |
| `FindingType` | Fact / Inference / Unknown | 三者必须分离 |
| `NextActionType` | Resolve Blocker / Resolve Gate-critical Unknown / Mitigate Warning / Minimum Validation / Higher-cost Reproduction | 固定五级优先级 |
| `ResourceSignalStatus` | Blocked / Warning / Unknown | Blocked：明确最低要求且当前资源明确不足；Warning：存在资源余量 / 投入风险但未证明无法继续；Unknown：项目要求或当前资源不足以可靠比较；不输出 Ready |
| `EvaluationSignalStatus` | Warning / Unknown | Warning：已知评测口径差异但未证明阻止复现；Unknown：无法确定正确评测口径；当前不独立产生 Blocked |
| `TargetResolutionStatus` | Identified / Pending Confirmation / Unresolved | 与 Readiness Status 分离 |
| `MaterialType` | Paper / Repository / README / Supplementary / Dataset Page / Checkpoint-Release / Config / Issue / Project Page / Other | Evidence 的 Material 来源类型 |
| `EnvironmentInputMode` | Read-only Detection / Snapshot / Manual Input | — |
| `EnvironmentAcquisitionState` | Acquired / Partial / Unauthorized / Auto Fetch Failed / Not Provided / Insufficient Information | Unauthorized / Fetch Failed ≠ Blocked |
| `EvidenceVerificationStatus` | Located Only / Corroborated / Unverifiable | Located Only：来源已定位但事实未独立确认；Corroborated：已有额外 Evidence / 可核事实形成交叉支持；Unverifiable：当前无法可靠核验。Citation 存在 ≠ 独立验证 |
| `EvidenceSourceType` | Material / User Context | — |
| `EvaluationConflictType` | Dataset Split / Metric Definition / Aggregation / Paper-Code Setting / Other | P06-light |
| `ResourceType` | GPU / VRAM / Disk / Time Budget | P04-light |
| `ConfirmationDecision` | Confirm / Supplement / Defer | — |
| `AccessMode` | Read-only | 当前 MVP 固定 |
| `AuthorizationStatus` | Authorized / Denied / Not Requested | Denied ≠ Environment Blocked |
| `AlternativeInput` | Snapshot / Manual Input / None | — |
| `FeedbackType` | Confirm / Question / Correct / Add Evidence | — |
| `AnalysisState` | Empty / Processing / Partial Result / Acquisition Failure / Conflict | 非 Readiness 业务状态 |

> `Not Provided` 表示用户未提供环境信息；`Insufficient Information` 表示已提供部分信息，但仍不足以支持相关判断。两者都不等于 `Blocked`。

---

## 8. 跨对象核心规则

1. **No Finding ≠ Ready**；Ready 必须有足够正向 Evidence。
2. 一个 Finding 只有一个 `primary_dimension`；同一 Root Cause 不重复建立等价 Finding。
3. 只有 `gate_critical = true` 的 Finding 才能单独形成 Blocked、Gate-critical Unknown 或关键 Gate Impact。
4. Paper / README / Repository / Config / User Environment 的关键冲突必须保留，不静默覆盖。
5. Unknown 只按真实依赖关系传播，不跨 Dimension 自动扩散。
6. Overall Gate 不采用平均分、多数投票或加权总分。
7. `CONDITIONAL PROCEED` 只支持低成本、可逆核验；关键 Unknown 解决前不进入高成本复现。
8. Resource / Evaluation 保持 Signal，不升级为核心 Dimension。
9. Confirmation 判断“对象是否正确”；Authorization 判断“系统是否允许读取”。
10. 技术获取失败不直接转成 Warning / Blocked / PAUSE；若因此无法判断业务条件，再进入 Unknown。

---

## 9. 验收清单

- [x] 三个核心 Dimension、四种 Status、三种 Overall Gate 未被改写。
- [x] Gate availability 与 Gate value 分离。
- [x] Finding 保留 Primary Dimension、`gate_critical`、Evidence 与 Gate Impact。
- [x] Evidence 支持 Material / User Context 来源，并保留核验状态。
- [x] Processing / Partial Result 等非业务状态不污染 Readiness Status。
- [x] Resource Signal 保持 P04-light，不包含完整资源需求预测。
- [x] Evaluation Signal 仅 Warning / Unknown，不独立 Blocked。
- [x] Next Action 保持五级优先级。
- [x] Confirmation 与 Authorization 分离。
- [x] 当前 MVP 只读边界未被字段设计突破。
- [x] 字段足以支持 Output Schema 与 Figma，但未进入企业级数据治理。

---

## 10. 当前状态

**当前状态：COMPLETED FOR SPRINT 2 DAY 4 — READY FOR OUTPUT SCHEMA / FIGMA HANDOFF**

本版本已完成字段级一致性审计，可作为 Output Schema 与 Figma Handoff 的正式输入；下游不得静默改变本文件继承的冻结业务规则。
