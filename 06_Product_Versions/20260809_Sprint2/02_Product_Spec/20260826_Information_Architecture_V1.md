# ResearchOps Information Architecture V1

**Document ID：** `20260826_Information_Architecture_V1`  
**Version：** V1  
**Date：** 2026-08-26  
**Status：** COMPLETED FOR DAY 4 PRODUCT SPEC 
**Stage：** Sprint 2 · Day 4  
**Product：** ResearchOps

---

## 1. 文档概览

### 1.1 文档目的

本文档将 PRD V0.9 已定义的产品范围、核心用户流程与安全边界转化为 ResearchOps MVP 的信息架构，重点回答：

1. 产品中有哪些核心信息对象；
2. 用户先看到什么、再下钻什么；
3. Task、Dimension、Finding、Evidence、Overall Gate 与 Next Action 如何关联；
4. Target / Source Confirmation、执行环境只读授权与异常状态如何进入主流程。

本 IA 不重新定义产品问题，不重新调整 P0 / P1 / P2，也不重新决定 Readiness Dimension、Status 或 Overall Gate 规则。

### 1.2 上游输入与冻结边界

本 IA 直接继承：

- `20260826_PRD_V0.9`；
- `20260826_Readiness_Dimension_Definition_V1`；
- Sprint 2 Baseline / Decision Breakpoint 已冻结结论；
- Sprint 2 Opportunity / Readiness Analysis 已冻结结论。

必须保持：

- 唯一 P0 主路径：`Reproduction Readiness Assessment`；
- 三个核心 Dimension：RD-01 / RD-02 / RD-03；
- 四种 Dimension Status：Ready / Warning / Blocked / Unknown；
- 三种 Overall Gate：PROCEED / CONDITIONAL PROCEED / PAUSE；
- Evidence-linked Findings 为跨 Dimension 机制；
- Resource Constraint Signal 与 Evaluation Conflict Signal 不升级为核心 Dimension；
- 当前 MVP 仅在用户授权范围内进行只读信息获取，不提供写入 / 修复 / 训练执行能力。

### 1.3 核心产品结构

当前 MVP 继续由三个核心模块构成：

1. **Structured Readiness Card**：组织三个核心 Dimension 及其 Status；
2. **Evidence-linked Findings**：将关键判断与可定位 Evidence 绑定；
3. **Next Action / Gate**：给出阶段性 Overall Gate 与优先行动。

辅助机制：

- Resource Constraint Signal；
- Evaluation Conflict Signal。

单个 Dimension 的信息表达遵循：

> **Condition / Check → Status → Finding / Unknown → Evidence → Gate Impact → Next Action**

整体决策关系遵循：

> **Evidence → Finding → Dimension / Signal → Status → Gate Impact → Overall Gate → Next Action**

### 1.4 IA 主路径

当前主路径为：

> **Task Setup → 关联材料发现与理解 → Readiness Overview → Dimension Detail → Finding → Evidence → Next Action / Feedback**

关键条件路径：

- Target / Source 存在歧义 → 用户确认目标对象；
- RD-02 或 Resource 判断需要实际执行环境 → 用户授权只读获取，或 Snapshot / Manual Input；
- Gate-critical 信息不足 → 保留 Unknown，不通过猜测补齐；
- 用户查看 Evidence 后可确认、质疑或补充修正信息。

---

## 2. 核心信息对象与关系

### 2.1 核心对象总览

| 对象 | 作用 | 关键关系 |
|---|---|---|
| **Task** | 一次完整 Readiness Assessment 的顶层上下文 | 包含 Target、Materials、Context 与 Readiness Result |
| **Target** | 本次评估针对的论文 / 项目 / Repository | 由用户入口识别，可存在待确认状态 |
| **Material** | 判断所依据的材料来源 | 可支持多个 Evidence / Finding |
| **User Context / Execution Environment** | 用户约束与实际执行环境事实 | 为 RD-02 与 Resource Signal 提供上下文 |
| **Readiness Result** | 当前 Task 的阶段性准备度结果 | 汇总三个 Dimension、Signal、Gate 与 Action |
| **Dimension** | 组织三类核心复现前条件 | 固定为 RD-01 / RD-02 / RD-03 |
| **Finding** | 对一个具体条件形成的结构化判断 | 一个 Primary Dimension，可有 Related Dimension |
| **Evidence** | 支持、解释、质疑或核对 Finding 的来源 | 指向 Source / Location |
| **Overall Gate** | 当前是否适合进入下一阶段投入 | 由 Dimension Status 与必要 Signal 聚合 |
| **Next Action** | 将当前判断转化为下一步建议 | 应回溯到 Finding / Dimension / Gate Reason |
| **Signal** | 不属于核心 Dimension、但会影响 Gate 的上下文信息 | Resource / Evaluation |
| **Feedback / Correction** | 用户核对、质疑或补充判断 | 关联 Finding / Evidence |
| **Confirmation / Authorization** | 分别处理“对象是否正确”和“系统是否允许读取” | 两类语义必须分离 |

### 2.2 Task

Task 是一次 Readiness Assessment 的顶层业务对象，不等于一次对话或单个页面。

一个 Task 至少承载：

- Reproduction Goal；
- Target；
- Materials；
- User Context / Execution Environment；
- Readiness Result；
- Feedback / Correction。

### 2.3 Target 与 Material

用户创建 Task 时只需提供至少一个可识别 Target Entry，例如：

- Paper Title；
- DOI；
- arXiv；
- Repository；
- Project Page。

系统可以发现关联 Paper、Repository、README、Supplementary、Dataset Page、Checkpoint / Release、Config、Issue 等 Material。

若 Paper ↔ Repository 或官方 / 第三方实现存在关键歧义：

- 不得静默选择；
- 应进入 Target / Source Confirmation；
- 未确认的关键关联不得作为已验证事实。

Material 是 Evidence 来源，不直接代表 Ready / Warning / Blocked / Unknown。

### 2.4 Readiness Result 与 Dimension

Readiness Result 是当前 Evidence 与用户上下文下的阶段性判断，主要包含：

- RD-01 / RD-02 / RD-03 Final Status；
- Key Findings / Unknown；
- Resource Constraint Signal；
- Evaluation Conflict Signal；
- Overall Gate；
- Prioritized Next Action。

三个核心 Dimension 固定为：

| ID | Dimension | 主要组织内容 |
|---|---|---|
| **RD-01** | Data & Access Readiness | Dataset / Subset、获取入口、权限、申请 / 审批、metadata / split / path / input format |
| **RD-02** | Environment & Dependency Readiness | OS、Python、Framework、CUDA、Driver、Dependency、Environment File、兼容风险 |
| **RD-03** | Weights & Configuration Readiness | Checkpoint、Pretrained Weights、Config、关键参数、加载要求、论文—代码配置差异 |

每个 Dimension：

- 只输出一个最终 Status；
- 可以包含多个 Finding / Unknown / Evidence；
- 可以影响 Overall Gate。

### 2.5 Finding 与 Evidence

Finding 是最小的可解释判断单元，应能够表达：

- Condition / Check；
- 当前判断；
- Primary Dimension；
- 可选 Related Dimension；
- Fact / Inference / Unknown；
- `gate_critical`；
- Gate Impact；
- Evidence；
- Next Action（如需要）。

跨维规则：

1. 一个 Finding 只有一个 Primary Dimension；
2. 可通过 Related Dimension 表达其他影响；
3. 同一 Root Cause 不重复建立等价 Finding 或重复计算 Blocker；
4. Paper / README / Repository / Config / User Environment 的关键冲突必须显式保留；
5. Fact、Inference 与 Unknown 必须分离；
6. 一个 Dimension 的 Unknown 不自动传播到其他 Dimension，除非另一判断真实依赖同一未知事实；
7. Finding 必须区分 `gate_critical = true / false`；只有 Gate-critical Finding 才能单独形成 Dimension-level Blocked、Gate-critical Unknown 或直接触发关键 Gate Impact。

Evidence 应尽可能包含：

- Source；
- Location；
- Material Type；
- Evidence Summary；
- Verification / Confidence；
- 对应 Finding。

原则：

> **Citation 存在 ≠ 事实已经独立验证。**

无法可靠定位 Evidence 时，不伪造精确 Source / Location，应保留验证状态或 Unknown。

### 2.6 Overall Gate、Next Action 与 Signal

Overall Gate 固定为：

- PROCEED；
- CONDITIONAL PROCEED；
- PAUSE。

Overall Gate 继续继承上游聚合规则：

1. 任一核心 Dimension = `Blocked`，或存在 confirmed Resource Blocked Signal → `PAUSE`；
2. 无 confirmed Blocker，但任一核心 Dimension = `Warning / Unknown`，或存在 Resource / Evaluation Warning / Unknown Signal → `CONDITIONAL PROCEED`；
3. RD-01 / RD-02 / RD-03 均为 `Ready`，且不存在重要 Resource Constraint 或优先 Evaluation Conflict → `PROCEED`。

Gate 必须能够回溯到触发它的 Dimension、Finding、Unknown 或 Signal，不采用平均分、多数投票或加权总分。

`CONDITIONAL PROCEED` 仅表示可以继续低成本、可逆的核验或准备；进入高成本复现前，应优先解决 Gate-critical Unknown。

Next Action 优先级继承上游：

> **1. Resolve Blocker → 2. Resolve Gate-critical Unknown → 3. Mitigate Warning → 4. Minimum Validation → 5. Higher-cost Reproduction**

只有关键 Gate 条件满足后，才建议进入 full dataset preparation、long training、large-scale preprocessing 或 high-cost GPU execution。Next Action 是建议，不等于系统自动执行。

Signal 保持独立：

- **Resource Constraint Signal**：基于 GPU / VRAM / Disk / Time Budget 形成 Blocked / Warning / Unknown；不提供完整 Resource Ready 认证或精确资源预测；
- **Evaluation Conflict Signal**：表达明显 Dataset Split / Metric / Aggregation / Paper-Code 评测冲突，仅作为 Warning / Unknown 轻量观察信号。

### 2.7 Confirmation 与 Authorization

两类语义必须分离：

| 类型 | 回答的问题 | 典型场景 |
|---|---|---|
| **Target / Source Confirmation** | “系统分析的是不是正确对象？” | Paper ↔ Repo 歧义、多个候选 Repo、官方 / 第三方实现不明确 |
| **Permission / Access Authorization** | “系统是否被允许读取？” | 实际执行环境、用户授权范围内的非默认公开信息 |

Target Confirmation 不代表系统已经获得访问权限；Access Authorization 也不代表目标对象已经被事实确认。

### 2.8 核心对象层级

> **Task**  
> ├── Target  
> ├── Materials  
> ├── User Context / Execution Environment  
> └── **Readiness Result**  
> 　　├── RD-01 → Findings → Evidence  
> 　　├── RD-02 → Findings → Evidence  
> 　　├── RD-03 → Findings → Evidence  
> 　　├── Resource Constraint Signal  
> 　　├── Evaluation Conflict Signal  
> 　　├── Overall Gate  
> 　　└── Prioritized Next Actions

Feedback / Correction 与 Finding / Evidence 建立关联。

---

## 3. 页面架构与内容层级

### 3.1 页面设计原则

1. 主路径保持短且连续；
2. 用户先看到总体判断，再按需下钻；
3. Overview 是核心决策入口；
4. Evidence 不应压过主要决策信息；
5. Resource / Evaluation Signal 不建立核心页面；
6. Next Action 与 Finding / Gate 保持直接关联，不扩展为任务管理模块；
7. Confirmation / Authorization 作为条件交互，不扩展为新的核心业务模块。

### 3.2 页面 / 视图总览

当前 MVP 建议使用 **3 个核心页面 + 支撑详情 / 条件交互**。

#### 核心页面

1. **Task Setup**
2. **Readiness Overview**
3. **Dimension Detail**

#### 支撑详情 / 条件交互

- Finding：在 Dimension Detail 中展开或进入详情；
- Evidence Detail：Drawer / Side Panel / Detail View；
- Target / Source Confirmation：Modal / Inline / Supporting View；
- Environment Access / Input：Modal / Setup Section / Supporting View；
- Feedback / Correction：从 Finding / Evidence 上下文触发。

IA 冻结的是信息关系，不锁定最终 UI 组件形式。

### 3.3 Task Setup

**用户问题：**“我要评估哪个项目，需要提供什么？”

核心内容：

- Target Entry；
- Reproduction Goal；
- Target Resolution Status；
- Discovered Materials Summary；
- Execution Environment Status；
- Contextual Inputs；
- 当前仍缺失的 Gate-critical Input。

Target 可处于：

- 已识别；
- 待确认；
- 无法确认。

执行环境获取状态可处于：

- 已获取；
- 部分获取；
- 未授权；
- 无法自动获取；
- 未提供 / 信息不足。

上述为 Environment Acquisition / Input State，不等同于 Readiness Status。若 RD-02 或 Resource 判断依赖缺失的环境事实，则对应业务判断保持 `Unknown`。

Task Setup 不展示完整 Readiness Result，也不提供环境修改、自动修复或训练执行。

### 3.4 Readiness Overview

**用户问题：**“现在能不能继续？最大问题是什么？下一步先做什么？”

默认信息优先级：

1. **Overall Gate + Gate Reason**；
2. **三个核心 Dimension Status**；
3. **当前最重要 Blocker / Gate-critical Unknown / Warning**；
4. **First Next Action**；
5. **重要 Contextual Signal**。

每个 Dimension Card 至少展示：

- Dimension Name；
- Final Status；
- 关键 Finding / Unknown 摘要；
- Gate Impact；
- Detail Entry。

Resource Constraint Signal 与 Evaluation Conflict Signal 必须在视觉和层级上与三个核心 Dimension 分离。

### 3.5 Dimension Detail

**用户问题：**“为什么这个 Dimension 是当前状态？”

核心内容：

- Dimension Name / ID；
- Final Status；
- Status Explanation；
- Gate Impact；
- Key Findings；
- Unknown；
- Related Signal（如有）；
- Related Next Action。

Finding 首屏应优先表达：

- Condition / Check；
- 当前判断；
- Fact / Inference / Unknown；
- `gate_critical`；
- Gate Impact；
- Evidence Availability。

用户可以从 Finding 进一步查看 Evidence。

### 3.6 Evidence Detail

Evidence Detail 是 **支撑详情视图**，不要求成为独立一级页面。

**用户问题：**“这个判断依据是什么？”

至少表达：

- Source / Location；
- Material Type；
- Evidence Summary；
- Verification / Confidence；
- 对应 Finding / Dimension；
- Conflicting Evidence（如有）。

必须支持：

> **Finding → Evidence → Source / Location → 返回原判断上下文**

Evidence Detail 不扩展为 Repository 浏览器或独立资料库。

### 3.7 条件交互

#### Target / Source Confirmation

当 Target 关联存在关键歧义时，展示：

- 用户原始输入；
- 候选 Target / Source；
- 主要关联依据；
- 当前不确定性；
- Confirm / Supplement / Defer。

未确认的关键对象不得作为已验证事实。

#### Environment Access / Input

当 RD-02 / Resource 判断需要实际执行环境时，先明确：

> **本次复现实际计划在哪个环境执行？**

用户可选择：

- 授权只读检测；
- Environment Snapshot / File；
- Manual Input；
- 暂不提供。

当前只读范围可包含：OS、GPU、VRAM、Driver、CUDA、Python、Disk。

拒绝授权或检测失败不等于 Blocked；若判断依赖这些信息，则保持 Unknown。

#### Feedback / Correction

用户可从 Finding / Evidence：

- Confirm；
- Question；
- Correct；
- Add Evidence。

完成后返回原判断上下文，不直接触发环境 / 文件 / 训练执行。

当用户补充或修正的信息足以改变当前判断时，仅重新评估受影响的 Finding / Dimension / Readiness Result；当前 MVP 不要求构建完整 Persistent Decision History。

### 3.8 当前不单独建立的页面

当前 MVP 不单独建设：

- Resource Planning；
- Training Time Estimation；
- Evaluation Alignment；
- Runtime Diagnosis；
- Environment Repair；
- Training Execution；
- GPU Scheduling；
- Persistent / Collaboration Workspace；
- Multi-Agent / MCP Control Center；
- 通用 Project Management。

---

## 4. 导航与条件路径

### 4.1 主导航

核心导航骨架：

> **Task Setup → Readiness Overview → Dimension Detail → Finding → Evidence**

同时：

> **Readiness Overview → First Next Action → Related Finding / Gate Reason**

核心详情深度建议控制在：

> **Overview → Dimension → Finding → Evidence**

Material、Source、Action 与 Signal 不继续扩展成多级独立页面。

### 4.2 下钻与返回

必须保持以下关系：

- Overview → Dimension；
- Dimension → Finding；
- Finding → Evidence；
- Evidence → Source / Location；
- Evidence → Finding；
- Finding → Dimension；
- Dimension → Overview；
- Next Action → Related Finding / Gate Reason；
- Feedback → 原 Finding / Evidence。

具体使用 Back、Breadcrumb、Drawer Close 或 Context Link 由 Figma 决定。

### 4.3 条件路径

| 触发条件 | 路径 | 返回 |
|---|---|---|
| Target / Source 存在关键歧义 | Task Setup / Material Discovery → Confirmation | Task Context |
| RD-02 / Resource 缺少实际环境信息 | Task Setup / RD-02 → Environment Access / Input | Task Setup / RD-02 |
| 用户需要核对判断 | Finding → Evidence | 原判断上下文 |
| 用户需要质疑或补充 | Finding / Evidence → Feedback / Correction | 原判断位置 |
| Overall Gate 需要解释 | Gate → Gate Reason → Finding / Signal | Overview |

### 4.4 Unknown / Warning / Blocked / Ready 的下钻

四种业务状态共享同一基本解释结构：

> **Status → Finding / Unknown Reason → Evidence → Gate Impact → Next Action**

差异仅在于：

- **Unknown**：重点说明缺少什么、为什么无法判断、是否 gate_critical；
- **Warning**：重点说明已知风险以及为什么尚不属于 Blocked；
- **Blocked**：重点说明已确认失败的必要条件与解除路径；
- **Ready**：仍应能够查看正向 Evidence，不能因为“未发现问题”而没有依据。

Unknown 不应成为异常终止页，也不要求用户补齐所有 Unknown 才能继续浏览其他已知结果。

---

## 5. 状态、空态与异常处理

### 5.1 状态分层原则

IA 必须区分 **业务 Readiness Status** 与 **处理 / 获取状态**。

#### 业务 Readiness Status

- Ready；
- Warning；
- Blocked；
- Unknown。

#### 处理 / 获取状态

- Empty；
- Processing；
- Partial Result；
- Acquisition Failure；
- Conflict。

关键语义：

> **Empty ≠ Unknown**  
> **Processing ≠ Unknown**  
> **Acquisition Failure ≠ Blocked**  
> **未授权 ≠ Environment Blocked**

### 5.2 状态定义

| 状态 | 含义 | IA 处理 |
|---|---|---|
| **Empty** | 尚无必要输入 / 尚未开始 | 提示用户提供 Target 或必要上下文，不展示业务结论 |
| **Processing** | 系统仍在发现 / 分析材料 | 展示处理状态，不提前转成 Unknown |
| **Partial Result** | 部分 Dimension 已有结果，部分仍处理中 / Unknown | 已知结果继续可浏览，不阻塞整个 Task |
| **Unknown** | 已基于当前可用信息分析，但仍无法可靠判断 | 展示原因、缺失信息、gate_critical 与 Next Action |
| **Acquisition Failure** | 获取材料或环境事实发生技术失败 | 提供 Retry / Snapshot / Manual 等替代路径，不自动改成 Blocked |
| **Conflict** | 多来源存在关键冲突 | 保留冲突来源；关键影响不确定时进入 Unknown，非阻塞风险可为 Warning |

### 5.3 Target / Material / Environment 异常

- Target 仍在识别 → Processing；
- Target 无法唯一确认 → Confirmation；
- Target 无法建立可信对象 → 暂不形成确定性 Overall Gate；
- Material 部分缺失 → 已知部分继续分析，依赖缺失材料的条件进入 Unknown；
- “未找到 checkpoint / dataset”本身不等于“明确不存在”；
- 用户拒绝环境授权 → 尊重选择，改用 Snapshot / Manual / Unknown；
- 环境检测失败 → Acquisition Failure，不等于 Environment Failure；
- 环境部分获取 → 已知字段进入判断，缺失字段按依赖关系保持 Unknown。

### 5.4 Evidence 异常

#### 无可靠 Evidence

应显示：

- 当前没有可靠可定位依据；
- 当前判断属于 Inference 还是 Unknown；
- 下一步如何核验。

不得伪造 Source / Location。

#### Source 不可访问

应区分：

> **“已知来源但当前无法访问” ≠ “来源不存在”**

若关键判断依赖该来源且无法核验，则进入 Unknown。

#### Conflicting Evidence

应保留多个来源与冲突摘要，不静默选择。Gate-critical 冲突无法解决时进入 Unknown；已知但非阻塞差异可为 Warning。

### 5.5 Overall Gate availability

`PROCEED / CONDITIONAL PROCEED / PAUSE` 是 Overall Gate 的全部业务值。

当以下情况发生时，可以暂不形成正式 Gate：

- Target 尚无法可靠建立；
- 核心分析仍处于 Processing；
- 当前信息不足以形成总体阶段判断。

此时展示：

> **Overall Gate 尚未形成 / Not Available Yet**

这是 **Gate availability / processing state**，不是第四种 Overall Gate。

当已经具备形成 Gate 的基本判断基础，只是存在 Gate-critical Unknown 时，按上游规则进入 `CONDITIONAL PROCEED`。

### 5.6 技术错误不污染业务判断

页面加载失败、Material Fetch Failure、Connector Failure、环境检测失败等技术问题，不自动转换为 Warning / Blocked / PAUSE。

只有当技术失败导致某个业务条件无法可靠判断时，对应条件才进入 Unknown。

---

## 6. 信息优先级与渐进披露

### 6.1 信息优先级模型

ResearchOps 采用：

> **Decision → Explanation → Evidence → Correction**

#### Level 1｜Decision

- Overall Gate；
- 三个 Dimension Status；
- Key Issue；
- First Next Action；
- 重要 Contextual Signal。

#### Level 2｜Explanation

- Dimension Detail；
- Finding / Unknown；
- Gate Impact；
- Related Action。

#### Level 3｜Evidence

- Evidence Summary；
- Source / Location；
- Verification / Confidence；
- Conflict。

#### Level 4｜Correction

- Confirm；
- Question；
- Correct；
- Add Evidence。

### 6.2 默认展开与折叠

默认优先展开：

- Overall Gate；
- 三个核心 Dimension；
- 当前最重要问题；
- First Next Action；
- materially relevant Signal。

默认折叠：

- 次要 Findings；
- 完整 Evidence；
- 完整 Material List；
- 环境字段详情；
- 非 gate-critical Unknown；
- 次要 Warning；
- 原始来源全文。

### 6.3 特殊信息的呈现

- **Blocked**：高优先级突出 Blocking Finding、Evidence、Gate Impact 与解除 Action；
- **Unknown**：优先说明为什么不知道、缺什么、是否 gate_critical；
- **Warning**：说明风险与为什么尚未构成阻塞；
- **Ready**：保持简洁，但必须能下钻正向 Evidence；
- **Resource / Evaluation Signal**：与核心 Dimension 视觉分离，仅在 materially relevant 时突出；
- **Material**：服务于 Target / Finding / Evidence，不作为用户进入产品后的首要信息列表。

### 6.4 信息去重

同一事实按层级表达，不复制完整段落：

> **Overview：一句结论**  
> **Dimension：解释原因**  
> **Finding：精确判断**  
> **Evidence：具体来源与核对依据**

例如：

- Overview：`Dataset Access Unknown`；
- Dimension：说明官方数据需要申请、当前权限状态未知；
- Finding：说明无法确认用户已完成必要审批；
- Evidence：定位官方 Dataset / README / Policy 来源。

---

## 7. 下游交接、待验证问题与 IA 验收

### 7.1 下游交接原则

后续规格继承本 IA 的 **对象语义、信息层级和导航关系**，但不在 IA 中提前展开企业级字段 / 事件 / UI 细节。

| 下游交付物 | 继续定义 |
|---|---|
| **Field Dictionary** | 核心对象字段、枚举、必填性与语义 |
| **Output Schema** | Task → Readiness Result → Dimension → Finding → Evidence / Gate / Action / Signal 的机器可读结构 |
| **Event Tracking** | Concept Test 真正需要观察的关键行为 |
| **Safety Boundary** | 只读授权、不写入 / 不执行、人类最终控制权 |
| **Figma Handoff / Figma** | 3 个核心页面、支撑详情与关键状态的视觉 / 交互表达 |

下游不得重新解释：

- 三个核心 Dimension；
- 四种 Dimension Status；
- 三种 Overall Gate；
- Evidence-linked Findings 的跨维机制；
- Resource / Evaluation Signal 边界；
- Confirmation 与 Authorization 的区别；
- 当前 MVP 授权后只读、不执行的安全边界。

### 7.2 Event Tracking 最小观察集

为支持后续 Concept Test，优先观察：

1. `task_started`；
2. `readiness_result_viewed`；
3. `evidence_expanded`；
4. `evidence_source_opened`；
5. `judgment_returned`；
6. `feedback_submitted`；
7. `next_action_viewed`；
8. `decision_recorded`。

这些事件用于观察产品行为，不代表 H2 / H3 已经成立。

### 7.3 Figma 必须覆盖

#### 核心页面

- Task Setup；
- Readiness Overview；
- Dimension Detail。

#### 支撑详情 / 条件交互

- Finding；
- Evidence Detail；
- Target / Source Confirmation；
- Environment Access / Input；
- Feedback / Correction。

#### 至少需要表达的状态

- Ready / Warning / Blocked / Unknown；
- Empty / Processing / Partial Result / Acquisition Failure / Conflict；
- Gate available / Gate not available yet；
- Target confirmed / pending confirmation；
- Environment authorized / partial / unauthorized / acquisition failure。

### 7.4 待验证问题

后续 Figma / Concept Test 重点验证：

1. 用户能否快速理解 Overall Gate、三个 Dimension 与当前最重要问题；
2. 用户能否区分 Ready / Warning / Blocked / Unknown；
3. 用户是否能够完成 Dimension → Finding → Evidence 的核对路径；
4. 用户能否区分 Target Confirmation 与 Read-only Authorization；
5. 用户是否能够理解 First Next Action 以及为什么优先；
6. Resource / Evaluation Signal 是否会被误认为核心 Dimension 或完整预测能力；
7. 当前 3 个核心页面是否足以支撑首版 Concept Test。

### 7.5 IA 验收清单

- [✅️] IA 仅承接三个核心 Readiness Dimension；
- [✅️] Ready / Warning / Blocked / Unknown 语义与上游一致；
- [✅️] Overall Gate 仅使用 PROCEED / CONDITIONAL PROCEED / PAUSE；
- [✅️] `Gate 尚未形成` 被建模为 availability / processing state，而不是第四种 Gate；
- [✅️] No Finding ≠ Ready，Blocked 必须有明确负向 Evidence；
- [✅️] Finding 只有一个 Primary Dimension，同一 Root Cause 不重复计算；
- [✅️] Resource / Evaluation 保持 Signal，不升级为 Dimension；
- [✅️] Task Setup → Overview → Dimension → Finding → Evidence 主路径清晰；
- [✅️] Target Confirmation 与 Access Authorization 明确分离；
- [✅️] Environment Acquisition Failure 不等于 Environment Blocked；
- [✅️] 技术错误不直接污染业务 Readiness Status；
- [✅️] Next Action 包含 Blocker → Gate-critical Unknown → Warning → Minimum Validation → Higher-cost Reproduction 的完整优先级；
- [✅️] Evidence 可核对但不压过总体决策；
- [✅️] 当前 MVP 不新增 Resource Planning、Runtime Diagnosis、Evaluation Alignment、Training Execution 等非 P0 页面；
- [✅️] 已足以支持 Field Dictionary、Schema 与 Figma，而未提前进入企业级实现规格。

### 7.6 当前状态

**当前状态：COMPLETED FOR SPRINT 2 DAY 4 — READY FOR FIELD DICTIONARY / OUTPUT SCHEMA / FIGMA HANDOFF**

本版本已完成瘦身后一致性审计；后续 Field Dictionary、Output Schema 与 Figma Handoff 应继续继承本 IA 已冻结的对象关系、状态语义、Gate 规则与只读安全边界，不在下游静默改变核心产品决策。
