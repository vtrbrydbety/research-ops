# Figma Change Request V1

## Purpose

用于记录 Figma Prototype 审计后需要进行的界面调整。

本文件用于区分：

- 需要修改 Figma 的 UI / 命名 / 信息展示问题
- 不需要修改 Figma 的 Schema 或数据结构问题


---

## Source

- Figma_Field_Map_V1
- Prototype_State_Checklist_V1
- PRD V0.9
- IA V1
- Field Dictionary V1
- Frozen HTML V3.6


---

# 1. Figma Changes Required


## CR-01 Target Type Naming

### Priority

P2

### Location

Task Setup

Target Confirmation

### Current

Target Type

Options:

- Repository
- Paper
- DOI
- arXiv
- Project Page

### Issue

当前 UI 展示内容实际上代表：

用户提供目标的入口方式（Entry Type）

而不是最终解析后的：

Target.target_type

Field Dictionary 中：

Target Type:

- Paper
- Repository
- Project

### Change

Rename:

Target Type

to:

Entry Type

### Expected Result

UI:

Entry Type

↓

Target Resolution

↓

Target.target_type


---

## CR-02 Target Confirmation Variant Naming

### Priority

P2

### Location

03_Variants_Reference

### Current

Skip Target Confirmation Modal

### Issue

当前名称描述的是 UI 形式（Modal），而不是产品状态。

该状态实际表示：

用户选择在目标未完全确认情况下继续。

### Change

Rename:

Skip Target Confirmation Modal

to:

Target Confirmation Bypass


---

## CR-03 Component Naming Separation

### Priority

P2

### Location

02_Components

### Current

Status Chip

### Issue

当前名称容易与其他状态类型混淆：

- Acquisition State
- Verification Status

### Change

Rename:

Status Chip

to:

Readiness Status Chip

保持：

- Acquisition State Tag
- Verification Status Chip


### Expected Result

Component 命名与业务对象保持一致：

Readiness Status

≠

Acquisition State

≠

Verification Status


---

## CR-04 Gate Availability Explanation

### Priority

P1

### Location

03_Variants_Reference

Gate Not Available Yet

### Current

Not Available Yet

### Issue

用户可能误认为：

Not Available Yet = Unknown

或者认为 Gate 增加第四种状态。

### Change

在 Reference / Supporting Explanation 中补充：

Not Available Yet

is not a fourth Gate status.

It indicates insufficient information to calculate Overall Gate.

### Expected Result

明确区分：

Gate Status:

- PROCEED
- CONDITIONAL PROCEED
- PAUSE

Gate Availability:

- Available
- Not Available Yet


---

# 2. No Figma Change Required

以下问题经过审计后确认：

不修改 Figma。

仅记录为 Schema / Data Model Follow-up。


---

## NR-01 Snapshot File Reference

### Issue

Figma 支持 Snapshot 输入。

但当前 Schema 未定义：

- snapshot reference
- uploaded artifact reference

### Decision

保留当前 UI。

后续 Schema 设计阶段处理。


---

## NR-02 Interaction State Expansion

### Issue

Field Dictionary 已定义：

Confirmation:

- candidate_refs
- selected_candidate_ref
- user_decision

Authorization:

- resource_scope
- authorization_status

但 Output Schema 当前未展开具体子字段。

### Decision

不修改 Figma。

后续补充 Schema。


---

## NR-03 Manual Input Raw Text

### Issue

Manual Input 支持自由文本输入。

当前未定义 raw input 保存字段。

### Decision

保持当前 UI。

是否保存原始输入由数据策略决定。


---

# 3. Change Priority Summary

| ID | Change | Priority | Type |
|---|---|---|---|
| CR-01 | Target Type → Entry Type | P2 | UI Naming |
| CR-02 | Target Confirmation Variant Rename | P2 | Variant Naming |
| CR-03 | Component Naming Separation | P2 | Component Naming |
| CR-04 | Gate Availability Explanation | P1 | Information Clarification |


---

# 4. Final Status

Current Status:

Figma Audit Completed


Pending:

- Apply Change Requests
- Recheck Prototype State Checklist
- Freeze Figma Version


After completion:

ResearchOps Figma Prototype V0.1

will enter Freeze Review.
