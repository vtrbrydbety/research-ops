# ResearchOps — Event Tracking Plan V1

**Document ID:** 20260826_Event_Tracking_Plan_V1  
**Version:** V1  
**Date:** 2026-08-26  
**Status:** COMPLETED FOR SPRINT 2 DAY 4

---

## 1. 目的与边界

本文件定义 ResearchOps MVP 在 Concept Test 阶段需要记录的最小行为事件与测试观察项，用于验证用户是否能够理解 Readiness Result、核对 Evidence，并形成明确的 Overall Gate 与 First Next Action。

本文件不建设完整企业级埋点体系，不包含：

- 用户增长、渠道归因或商业化埋点
- DAU / MAU 等运营指标体系
- SDK、数据仓库、采样、保留周期等工程治理字段
- 通过点击行为直接推断用户已经正确理解产品语义
- 以 Sprint 2 小样本行为直接宣称 H2 / H3 已通过

当前 Event Tracking 仅服务于 ResearchOps Concept Test 和后续受控验证。

所有 Product Event 默认自动记录 `timestamp`。

`task_id` 作为一次 Readiness Assessment 的核心关联字段，在各 Event 的 Core Properties 中显式保留。

---

## 2. Product Events

### 2.1 `task_started`

**Trigger**

用户正式开始一次 Readiness Assessment。

**Core Properties**

- `task_id`

**Metric Mapping**

- Decision Time 起点

---

### 2.2 `readiness_result_viewed`

**Trigger**

用户首次进入 Readiness Overview 并查看当前评估结果。

**Core Properties**

- `task_id`
- `gate_available`
- `gate_value`

**Metric Mapping**

- 是否进入核心 Readiness Result
- 核心结果触达

> 进入结果页不等于用户已经理解结果。

---

### 2.3 `evidence_expanded`

**Trigger**

用户主动展开某个 Finding 对应的 Evidence。

**Core Properties**

- `task_id`
- `finding_id`
- `dimension_id`
- `evidence_id`

**Metric Mapping**

- Evidence 展开
- H3 探索性行为信号

---

### 2.4 `evidence_source_opened`

**Trigger**

用户从 Evidence 摘要进一步进入 Paper、README、Repository、Issue 等原始来源。

**Core Properties**

- `task_id`
- `evidence_id`
- `material_id`
- `material_type`

**Metric Mapping**

- Evidence 定位
- Evidence Traceability 行为

---

### 2.5 `judgment_returned`

**Trigger**

用户查看 Evidence 或原始来源后，返回对应 Finding、Dimension 或 Overall Gate 继续核对判断。

**Core Properties**

- `task_id`
- `evidence_id`
- `return_target`

`return_target` 当前允许：

- `Finding`
- `Dimension`
- `Overall Gate`

**Metric Mapping**

- Evidence → Judgment 返回核对行为
- H3 探索性行为信号

---

### 2.6 `feedback_submitted`

**Trigger**

用户基于当前 Finding / Evidence 提交确认、质疑、纠正或新增 Evidence。

**Core Properties**

- `task_id`
- `target_ref`
- `feedback_type`
- `requires_reassessment`

`feedback_type` 继承 Field Dictionary：

- `Confirm`
- `Question`
- `Correct`
- `Add Evidence`

**Metric Mapping**

- 用户修正
- Evidence 纠错行为
- H3 探索性行为信号

---

### 2.7 `next_action_viewed`

**Trigger**

用户查看某条 Next Action。

**Core Properties**

- `task_id`
- `action_id`
- `action_type`
- `priority`

**Metric Mapping**

- First Next Action 触达
- Next Action 使用行为

> 查看 Next Action 不等于用户已经理解该行动为什么应被优先执行。

---

### 2.8 `decision_recorded`

**Trigger**

用户在 Concept Test 中形成并确认当前 Overall Gate 与 First Next Action。

**Core Properties**

- `task_id`
- `gate_value`
- `first_action_id`

**Metric Mapping**

- Decision Time 终点
- 任务完成的产品侧辅助记录

> `decision_recorded` 是 Concept Test 的记录事件，不要求当前 MVP 新增“确认决策”按钮或独立产品流程；可由原型测试流程或测试记录机制生成。  
> `decision_recorded` 不自动代表用户已正确理解判断，任务是否真正完成仍需结合 Concept Test 观察确认。

---

## 3. Test Observations

以下内容无法仅通过 Product Event 可靠判断，因此由 Concept Test 主持人或测试记录进行观察。

| Observation | Definition / Judgment |
|---|---|
| `key_issue_identified` | 用户能否指出当前最重要的 Blocker、Gate-critical Unknown 或 Warning |
| `status_understood` | 用户能否正确理解 Ready / Warning / Blocked / Unknown 的区别 |
| `first_action_understood` | 用户能否说明 First Next Action 是什么，以及为什么应优先执行 |
| `resource_boundary_understood` | 用户是否理解 Resource Constraint Signal 不是精确资源需求预测 |
| `input_mechanism_understood` | 用户是否理解：Target / Source Confirmation 用于确认分析对象是否正确；实际执行环境可通过 Read-only Detection / Snapshot / Manual Input 获得；Read-only Authorization 用于确认系统是否被允许读取指定环境或资源 |

Product Event 与 Test Observation 不互相替代。

例如：

`next_action_viewed = true`

只能说明用户查看过 First Next Action，不能证明：

`first_action_understood = true`

---

## 4. Metric Mapping

### 4.1 Decision Time

```text
Decision Time
=
decision_recorded.timestamp
-
task_started.timestamp
```

用于记录用户从正式开始任务，到形成明确 Overall Gate 与 First Next Action 所需的时间。

当前 Sprint 2 仅记录探索性观察值，不直接宣称优于 Baseline。

---

### 4.2 Evidence Viewed

```text
Evidence Viewed
=
是否发生 evidence_expanded
```

表示用户是否主动查看至少一个关键 Finding 的 Evidence。

---

### 4.3 Evidence Located

```text
Evidence Located
=
是否发生 evidence_source_opened
```

表示用户是否进一步进入可定位的原始材料来源。

---

### 4.4 Returned to Judgment

```text
Returned to Judgment
=
是否发生 judgment_returned
```

表示用户查看 Evidence 后是否返回 Finding / Overall Gate 继续核对判断。

---

### 4.5 Correction Behavior

```text
Correction Behavior
=
feedback_submitted
AND
feedback_type ∈ {
  Question,
  Correct,
  Add Evidence
}
```

用于观察用户是否真正基于 Evidence 发生质疑、纠正或证据补充行为。

单纯 `Confirm` 可记录，但不单独视为纠错行为。

---

### 4.6 Task Completion

Concept Test 中的任务完成不能仅由单一 Event 判定。

最低观察条件为用户能够明确说明：

1. 当前 Overall Gate；
2. 当前 Gate 的主要原因；
3. First Next Action。

`decision_recorded` 仅作为任务完成的产品侧辅助记录。

---

## 5. 验收清单

- [x] Event Tracking 直接服务于当前 Concept Test，不扩展为完整运营埋点体系。
- [x] `task_started` 与 `decision_recorded` 可以支持 Decision Time 计算。
- [x] Evidence 展开、来源定位、返回判断、用户修正均有对应 Product Event。
- [x] Product Event 与 Test Observation 已明确分离。
- [x] 四状态理解不能通过点击事件自动推断。
- [x] First Next Action 的“查看”与“理解”已明确分离。
- [x] `gate_available` / `gate_value` 与 Field Dictionary / Output Schema 保持一致。
- [x] `evidence_source_opened.material_type` 与 MaterialType 语义保持一致。
- [x] Resource Constraint Signal 不被埋点设计包装为精确资源预测。
- [x] Target / Source Confirmation、环境输入方式与 Read-only Authorization 已明确区分。
- [x] `decision_recorded` 不要求新增 MVP 产品功能。
- [x] Sprint 2 Event 数据只作为探索性信号，不直接判定 H2 / H3。
- [x] 当前方案未引入与 MVP 无关的企业级埋点治理字段。

---

## 6. 当前状态

**COMPLETED FOR SPRINT 2 DAY 4 — READY FOR CONCEPT TEST / FIGMA HANDOFF**

本文件已完成字段一致性、Field Dictionary / Output Schema 对齐与 PRD Concept Test 对齐审计。下游原型与测试设计不得静默改变当前 Event、Observation 与验证边界。
