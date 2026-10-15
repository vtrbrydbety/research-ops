# ResearchOps — D5 Figma Handoff V1

**Document ID:** `20260826_D5_Figma_Handoff_V1`  
**Version:** V1  
**Date:** 2026-08-26  
**Status:** COMPLETED — READY FOR D5 FIGMA PROTOTYPE / CONCEPT TEST  
**Product:** ResearchOps

## 1. Purpose & Frozen Boundary
本文件将 Day 4 已完成的产品定义转化为 D5 Figma Wireframe / Clickable Prototype 可直接使用的页面、交互、状态与 Concept Test 要求。

审计基准：
- `20260826_PRD_V0.9.docx`
- `20260826_Information_Architecture_V1.md`
- `20260826_Field_Dictionary_V1.md`
- `20260826_Output_Schema_V1.json`
- `20260826_Event_Tracking_Plan_V1.md`
- `20260826_Safety_Boundary_V1.md`

Figma 不重新定义以下冻结项：

| 冻结项 | 规则 |
|---|---|
| Core Dimension | RD-01 / RD-02 / RD-03 |
| Dimension Status | Ready / Warning / Blocked / Unknown |
| Overall Gate | PROCEED / CONDITIONAL PROCEED / PAUSE |
| Signal | Resource / Evaluation，不升级为核心 Dimension |
| Next Action | 5 级固定优先级 |
| Confirmation / Authorization | 分离 |
| Safety | 当前 MVP 授权后只读，不写入、不执行 |

`gate_available = false` 表示 Gate 尚未形成，不是第四种 Gate。

## 2. Prototype Scope
### 2.1 Core Screens
1. **Task Setup**
2. **Readiness Overview**
3. **Dimension Detail**

### 2.2 Supporting Views
- Finding
- Evidence Detail
- Target / Source Confirmation
- Environment Access / Input
- Feedback / Correction

Evidence 可使用 Drawer / Side Panel；Confirmation、Authorization、Feedback 可使用 Modal / Inline。支撑 View 不升级为新的 P0 模块。

### 2.3 Current Non-goals
不设计 Resource Planning、Training Time Estimation、Evaluation Alignment、Runtime Diagnosis、Environment Repair、Training Execution、GPU Scheduling、Persistent / Collaboration Workspace、Multi-Agent / MCP Control Center、通用 Project Management。

## 3. Main Flow
```text
Task Setup
→ Target / Material Identification
→ Target Confirmation（仅关键歧义时）
→ Environment Input
→ Read-only Authorization（仅选择 Read-only Detection 时）
→ Readiness Overview
→ Dimension Detail
→ Finding
→ Evidence Detail / Source
→ 返回原判断
→ Next Action / Feedback
```

全局信息层级：
> **Decision → Explanation → Evidence → Correction**

核心决策链：
> **Evidence → Finding → Dimension / Signal → Status → Gate Impact → Overall Gate → Next Action**

## 4. Screen 01 — Task Setup
### 4.1 Goal
回答：“我要评估什么？系统分析哪个对象？本次准备在哪个环境复现？”

### 4.2 Required Content
**Reproduction Goal**
- `reproduction_goal`

**Target**
- Target Entry
- `target_type`
- `target_name`
- `source_entry`
- `resolution_status`
- Discovered Materials Summary

Target Entry 可来自 Paper Title、DOI、arXiv、Repository、Project Page。

### 4.3 Target / Source Confirmation
仅在关键映射歧义时出现，展示：
- Candidate Target / Source
- `uncertainty_reason`
- Confirm / Supplement / Defer

它只回答：
> **“分析对象是否正确？”**

不得使用 Authorization 文案。

### 4.4 Environment Input
可选择：
- Read-only Detection
- Snapshot
- Manual Input
- 暂不提供

前三项属于 `EnvironmentInputMode`；“暂不提供”不是新增 Input Mode。

### 4.5 Read-only Authorization
选择 Read-only Detection 后才进入 Authorization。

```text
ResearchOps can inspect:
✓ OS / Python / Framework
✓ CUDA / Driver
✓ GPU / VRAM
✓ Available Disk

ResearchOps will not:
✗ install packages
✗ modify environment
✗ write / delete / overwrite files
✗ start training or reproduction

Access Mode: Read-only
```

若 `Authorization = Denied`，不得直接显示 `RD-02 = Blocked`；提供 Snapshot / Manual Input / 暂不提供。

## 5. Screen 02 — Readiness Overview
### 5.1 Goal
第一屏应让用户回答：
1. Overall Gate 是什么？
2. 为什么？
3. 三个 Dimension 是什么状态？
4. 当前最大问题是什么？
5. First Next Action 是什么？

### 5.2 Information Priority
```text
Overall Gate + Gate Reason
→ RD-01 / RD-02 / RD-03
→ Key Issue
→ First Next Action
→ materially relevant Signal
```

### 5.3 Overall Gate
`gate_available = true`：展示 `gate_value`、`gate_reason`，必要时通过 `trigger_refs` 下钻。

```text
Overall Gate
CONDITIONAL PROCEED

Why
Dataset access permission is not confirmed.
```

`gate_available = false`：
```text
Overall Gate
Not Available Yet
```
不得显示 `Gate = Unknown`。

### 5.4 Dimension Card
固定只突出：
- RD-01 Data & Access Readiness
- RD-02 Environment & Dependency Readiness
- RD-03 Weights & Configuration Readiness

每张卡至少显示 Dimension Name / ID、Final Status、Short Explanation、Key Finding / Unknown、Gate Impact、View Details。

### 5.5 Key Issue + First Next Action
显式突出当前最重要的 Blocker / Gate-critical Unknown / Warning，并紧邻展示 `priority = 1` 的 Action 与原因。

Next Action 固定继承：
1. Resolve Blocker
2. Resolve Gate-critical Unknown
3. Mitigate Warning
4. Minimum Validation
5. Higher-cost Reproduction

Higher-cost Reproduction 只是建议，不显示 `Start Training` / `Run Reproduction` 等执行 CTA。

### 5.6 Context Signals
Resource / Evaluation 使用弱于三个核心 Dimension 的视觉层级。

```text
Additional Signals
Resource Constraint  UNKNOWN
Evaluation Conflict WARNING
```

边界：
- Resource：Blocked / Warning / Unknown，不输出 Ready
- Evaluation：Warning / Unknown，不独立 Blocked

## 6. Screen 03 — Dimension Detail
### 6.1 Goal
回答：“为什么这个 Dimension 是当前状态？”

### 6.2 Required Content
- `dimension_id`
- `dimension_name`
- `status` 或 `analysis_state`
- `status_explanation`
- `gate_impact`
- Key Findings
- Related Next Action

### 6.3 Finding
Finding Card 优先显示：
- `condition`
- `summary`
- `finding_type`：Fact / Inference / Unknown
- `gate_critical`
- `gate_impact`
- Evidence Availability

Finding 的 Unknown 是 **Finding Type**；Dimension 的 Unknown 是 **Dimension Status**。

### 6.4 Cross-dimension
一个 Finding 只有一个 `primary_dimension`。若影响其他 Dimension，使用 `related_dimensions`，只提供关联入口，不复制同一 Root Cause。

## 7. Evidence & Feedback
### 7.1 Evidence Detail
建议使用 Drawer / Side Panel，至少显示：
- Evidence Summary
- Source / Location
- Material Type（适用时）
- Verification Status
- Conflict Note（适用时）
- Open Source
- Feedback Entry

Verification Status：
- Located Only
- Corroborated
- Unverifiable

`Located Only` 不使用容易被理解为“已验证正确”的强成功视觉。

必须支持：
> **Finding → Evidence → Source / Location → 返回 Finding / Dimension**

Conflicting Evidence 必须并列保留，不静默选择。

### 7.2 Feedback / Correction
可选择：
- Confirm
- Question
- Correct
- Add Evidence

用户纠正 Finding / Evidence，不直接改写 Dimension Status 或 Overall Gate。

若 `requires_reassessment = true`：
> **Feedback → affected Finding → related Dimension → 必要时更新 Readiness Result / Gate**

`Confirm` 可记录，但不单独视为 Correction Behavior。

当前 Feedback 不提供 Fix Environment、Install Dependency、Modify Config、Apply Patch、Start Training。

## 8. Required States
### 8.1 Business Status
Ready / Warning / Blocked / Unknown

### 8.2 Processing / Acquisition State
Empty / Processing / Partial Result / Acquisition Failure / Conflict

必须保持：
> **Empty ≠ Unknown**  
> **Processing ≠ Unknown**  
> **Acquisition Failure ≠ Blocked**  
> **Unauthorized ≠ Environment Blocked**

关键 UI 规则：
- Ready：仍可下钻正向 Evidence。
- Warning：说明已知风险及非阻塞原因。
- Blocked：必须有明确负向 Evidence，并给解除路径。
- Unknown：说明缺什么、为什么无法判断、是否 gate-critical。
- Unknown 不是终止页。
- Acquisition Failure 提供 Retry / Snapshot / Manual Input。
- 技术错误不直接转成 Warning / Blocked / PAUSE。
- Gate Not Available Yet 不是第四种 Gate。

## 9. Concept Test Handoff
### 9.1 Product Events
Prototype 需支持或模拟：
1. `task_started`
2. `readiness_result_viewed`
3. `evidence_expanded`
4. `evidence_source_opened`
5. `judgment_returned`
6. `feedback_submitted`
7. `next_action_viewed`
8. `decision_recorded`

`decision_recorded` 仅为测试记录事件，不要求新增“确认决策”按钮。

### 9.2 Test Observations
重点观察：
- `key_issue_identified`
- `status_understood`
- `first_action_understood`
- `resource_boundary_understood`
- `input_mechanism_understood`

最低任务完成条件：
1. 能说出 Overall Gate；
2. 能说明主要 Gate Reason；
3. 能说出 First Next Action。

Sprint 2 只记录探索性信号，不直接宣称 H2 / H3 已成立。

### 9.3 Open Questions

本节不新增问题，仅承接 PRD §10.1 已定义的 Figma / Concept Test 待验证问题：

- **OQ-01**：用户能否快速理解三维 Readiness Card 的总体状态、关键缺失、风险 与 Unknown？
- **OQ-02**：用户是否能够区分 Ready / Warning / Blocked / Unknown，尤其 Warning 与 Unknown 的区别？
- **OQ-03**：Evidence-linked Findings 是否被注意、理解和实际查看，而不是增加信息负担？
- **OQ-04**：用户能否通过 Evidence 核对并指出至少一个判断问题 / 修正点？
- **OQ-05**：用户能否明确说出当前第一步 Next Action 以及为什么先做它？
- **OQ-06**：三核心 Dimension 是否足够支撑“是否值得开始复现”的判断？
- **OQ-07**：Resource Constraint Signal 的轻量表达是否清晰，是否会被误解为完整资源预测？
- **OQ-08**：Overall Gate 的 PROCEED / CONDITIONAL PROCEED / PAUSE 是否清晰且不引发错误心理模型？
- **OQ-09**：自动关联的 Paper / Repository 是否易于核验，存在歧义时用户能否正确确认目标对象？
- **OQ-10**：用户能否正确选择实际执行环境，并理解只读检测的授权范围？

## 10. First Prototype Coverage
### 10.1 Main Clickable Flow
```text
Task Setup
→ Target Identified
→ Read-only Authorization
→ Readiness Overview
→ CONDITIONAL PROCEED
→ RD-01 Gate-critical Unknown
→ Evidence Detail
→ Open Source
→ Return to Finding
→ Feedback / Correction
```

### 10.2 Required Variants
额外用 Variant / 独立 Frame 表达：
- Target Pending Confirmation
- Authorization Denied
- Processing
- Partial Result
- Acquisition Failure
- Conflict
- Gate Not Available Yet
- Blocked / PAUSE
- Ready / PROCEED

无需为所有状态组合制作完整 Clickable Flow。

## 11. Acceptance & Alignment
### 11.1 D5 Acceptance
- [x] 仅 3 个核心页面，不新增 P0 页面。
- [x] Target Confirmation 与 Authorization 分离。
- [x] Authorization 明确 Read-only Scope。
- [x] Overview 覆盖 Gate、三维、Key Issue、First Next Action。
- [x] Resource / Evaluation 与核心 Dimension 视觉分层。
- [x] Processing / Acquisition 与业务 Status 分层。
- [x] Finding / Evidence 可追溯且同一 Root Cause 不重复。
- [x] Feedback 不直接人工改写最终 Status / Gate。
- [x] 五级 Next Action 与 Safety Boundary 一致。
- [x] Prototype 可支撑 Event Tracking 与 Concept Test。

## 12. Current Status

**COMPLETED — READY FOR D5 FIGMA PROTOTYPE / CONCEPT TEST**

后续 Figma 不得静默改变：

- 三个核心 Dimension；
- 四种业务 Status；
- 三种 Overall Gate；
- Resource / Evaluation Signal 边界；
- 五级 Next Action；
- Confirmation / Authorization 分离；
- 当前 MVP 授权后只读、不执行的安全边界。
