# Figma Field Map V1


## Purpose

用于建立 Figma Prototype 与产品数据结构之间的映射关系。

确保 Prototype 中的关键 UI 元素能够对应：

UI Element
↓
Business Field
↓
Schema


该文档用于：

- 检查 Figma 是否覆盖核心产品字段
- 验证 UI 与 Schema 是否保持一致
- 记录设计过程中发现的数据结构问题


---

## Source

- PRD V0.9
- IA V1
- Field Dictionary V1
- Output Schema V1
- D5 Figma Handoff V1
- Frozen HTML V3.6


---

# 1. Main Mapping


## Task Setup


| UI | Field | Status |
|-|-|-|
| Reproduction Goal | Task.reproduction_goal | Direct |
| Target Entry | Target.source_entry | Direct |
| Context / Constraints | UserContext.user_provided_facts | Derived |
| Time Budget | UserContext.time_budget | Direct |
| Environment Input | UserContext.* | Parsed |


Notes:

- Context / Constraints 可能包含多个结构化信息，例如时间预算、资源限制等。
- Environment Input 通过用户输入或系统读取后解析为结构化环境字段。



---

## Target Identification / Confirmation


| UI | Field | Status |
|-|-|-|
| Target Name | Target.target_name | Direct |
| Target Entry | Target.source_entry | Direct |
| Target Resolution Status | Target.resolution_status | Direct |
| Candidate Target | Target candidates | Direct |
| Confirm Target Action | Target resolution decision | Direct |


Notes:

Target Confirmation 主要用于确认：

- 当前目标是否正确
- 候选目标是否需要补充
- 用户是否接受当前解析结果



---

## Environment Authorization


| UI | Field | Status |
|-|-|-|
| Read-only Access | Authorization.access_mode | Direct |
| Resource Scope | Authorization.resource_scope | Direct |
| Authorization Result | Authorization.authorization_status | Direct |
| Snapshot Input | UserContext.input_mode | Direct |
| Manual Input | UserContext.input_mode | Direct |


Notes:

Authorization 状态属于交互状态。

Authorization Denied 不等同于 Environment Blocked。



---

## Readiness Overview


| UI | Field | Status |
|-|-|-|
| Overall Gate | ReadinessResult.overall_gate | Direct |
| Gate Reason | OverallGate.reason | Direct |
| Dimension Card | ReadinessResult.dimensions | Direct |
| Dimension Status Badge | Dimension.status | Direct |
| Dimension Summary | Dimension.summary | Direct |
| Gate Impact | Dimension.gate_impact | Direct |
| Key Issue | Finding.title | Derived |
| First Next Action | PrioritizedAction | Direct |
| Resource Signal | ReadinessResult.signals.resource | Direct |
| Evaluation Signal | ReadinessResult.signals.evaluation | Direct |



---

## Dimension Detail


| UI | Field | Status |
|-|-|-|
| Dimension Name | Dimension.dimension_name | Direct |
| Dimension Status | Dimension.status | Direct |
| Dimension Explanation | Dimension.summary | Direct |
| Finding Title | Finding.title | Direct |
| Finding Description | Finding.description | Direct |
| Finding Type | Finding.finding_type | Direct |
| Evidence Reference | Finding.evidence_refs | Direct |
| Gate Critical | Finding.gate_critical | Derived |


Notes:

Dimension 与 Finding 保持层级关系：

Dimension
↓
Finding
↓
Evidence


Finding 不直接展示在 Overview Card 中。



---

## Evidence


| UI | Field | Status |
|-|-|-|
| Evidence Source | Evidence.source | Direct |
| Location | Evidence.location | Direct |
| Material Type | Evidence.material_type | Direct |
| Verification Status | Evidence.verification_status | Direct |
| Evidence Summary | Evidence.summary | Direct |


---

## Feedback


| UI | Field | Status |
|-|-|-|
| Confirm | Feedback.feedback_type | Direct |
| Question | Feedback.feedback_type | Direct |
| Correct | Feedback.feedback_type | Direct |
| Add Evidence | Feedback.feedback_type | Direct |
| Feedback Target | Feedback.target_ref | Direct |


Notes:

Feedback 用于补充或纠正 Evidence / Finding。

不会直接修改：

- Dimension Status
- Overall Gate



---

# 2. Important Notes


## Target Type


问题：

Figma 中：

- Repository
- Paper
- DOI
- arXiv
- Project Page


实际表示用户提供目标的方式，

不是最终 Target Type。


当前逻辑：

UI Entry Type

↓

Target Resolution

↓

Target.target_type


处理：

无需新增字段。

如果后续修改 UI：

建议：

Target Type

↓

Entry Type



---

## Acquisition State


以下状态：

- Processing
- Partial Result
- Acquisition Failure
- Conflict


属于：

Information Acquisition State


不要映射为：

- Warning
- Blocked
- Unknown


原因：

Acquisition 状态描述：

"信息获取过程"


Readiness Status 描述：

"复现准备程度"


二者属于不同层级。



---

## Gate Not Available Yet


Not Available Yet

不是第四种 Gate。


当前 Gate：

- PROCEED
- CONDITIONAL PROCEED
- PAUSE


Availability：

- Available
- Not Available Yet


两者需要保持分离。



---

# 3. Open Questions / Follow-up


| Issue | Status |
|-|-|
| Snapshot 文件是否需要单独字段 | Open |
| Interaction State 子字段是否展开到 Schema | Open |
| Target Entry Type 是否单独命名 | Open |
| Manual Input 是否保存原始文本 | Open |



---

# 4. Final Check


Current Result:

✅ Core UI fields covered

✅ Main user flow mapped

✅ Evidence and Readiness hierarchy aligned

✅ No major Figma-Schema mismatch


Remaining items:

⚠️ Mainly related to Schema clarification

⚠️ No major Prototype structure revision required

