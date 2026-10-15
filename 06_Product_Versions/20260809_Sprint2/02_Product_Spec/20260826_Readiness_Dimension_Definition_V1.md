# ResearchOps Readiness Dimension Definition

**Document ID：** `20260826_Readiness_Dimension_Definition_V1`  
**Version：** V1  
**Date：** 2026-08-26  
**Status：** FROZEN FOR MVP CONCEPT DESIGN  
**Stage：** Sprint 2 · Day 4 · Product Specification  
---

## 1. 文档目的与产品上下文

### 1.1 文档目的

本文件用于将 Sprint 1 已冻结的问题证据与 Sprint 2 Baseline 决策断点转化为 ResearchOps MVP 的正式 Readiness 判断结构，为后续 PRD、Information Architecture、Field Dictionary、Output Schema 与 Figma Concept Design 提供统一上游定义。

本文件主要回答四个问题：

1. 当前 MVP 应保留哪些核心 Readiness Dimensions；
2. 每个 Dimension 判断什么、不判断什么；
3. Ready / Warning / Blocked / Unknown 如何解释；
4. 三个 Dimension 与上下文 Signal 如何形成 Overall Gate 与 Next Action。

本文件不重新验证 Sprint 1 问题是否存在，不重新执行 Baseline A / B / C，也不用于证明 H2 / H3 已成立。

### 1.2 当前 P0 主路径

ResearchOps 当前唯一 P0 主路径为：

> **Reproduction Readiness Assessment｜复现前准备度评估**

当前优先级保持：

| Priority | Scope | 当前处理 |
|---|---|---|
| P0 | P01｜数据与权限 | 进入核心 Dimension |
| P0 | P02｜依赖与环境 | 进入核心 Dimension |
| P0 | P03｜权重与配置 | 进入核心 Dimension |
| P0 | P07｜证据链 | 作为跨 Dimension 的 Evidence-linked Findings |
| P1 | P04｜资源需求 | 完整能力保持 P1；当前仅保留轻量 Resource Constraint Signal |
| P1 | P05｜运行后诊断 | 不进入复现前 P0 主路径 |
| P2 | P06｜评测口径 | 仅保留明显 Evaluation Conflict Signal |

### 1.3 当前 MVP 核心结构

当前 MVP 的核心产品结构保持为三个模块：

1. **Structured Readiness Card**：承载三个核心 Dimension 及其 Status；
2. **Evidence-linked Findings**：将关键判断与可定位 Evidence 绑定；
3. **Next Action / Gate**：输出总体阶段判断，并告诉用户下一步最应该先处理什么。

辅助机制包括：

- Resource Constraint Signal；
- Evaluation Conflict Signal。

上述辅助机制不新增核心 Readiness Dimension。

---

## 2. Dimension 筛选结果

### 2.1 筛选原则

候选 Dimension 只有在同时满足以下条件时，才进入当前 MVP：

1. 存在 Sprint 1 Problem Evidence；
2. 存在 Sprint 2 Baseline / Decision Evidence；
3. 能在正式复现投入前至少部分核验；
4. 能直接影响 Readiness Status 或 Overall Gate；
5. 与已有 Dimension 不存在明显语义重复；
6. 不替代 Evidence-linked Findings 或 Next Action / Gate。

### 2.2 Candidate Screening

| Candidate | Scope | Decision | 当前保留方式 |
|---|---|---|---|
| Data & Access Readiness | P01 | **KEEP** | `RD-01` 核心 Dimension |
| Environment & Dependency Readiness | P02 | **KEEP** | `RD-02` 核心 Dimension |
| Weights & Configuration Readiness | P03 | **KEEP** | `RD-03` 核心 Dimension |
| Resource Constraint Readiness | P04 | 不作为独立 Dimension | Resource Constraint Signal |
| Evidence Readiness | P07 | 不作为独立 Dimension | Evidence-linked Findings |
| Evaluation Alignment Readiness | P06 | 不进入 P0 | Evaluation Conflict Signal |
| Runtime Diagnosis Readiness | P05 | 不进入 P0 | P1 Future Capability |

### 2.3 Resource Constraint Decision

资源问题具有真实问题证据，也可能直接影响用户是否继续投入，但当前不升级为第四个核心 Dimension，原因是：

- P04｜完整资源需求能力已冻结为 P1；
- 当前主要 Decision Breakpoint 仍是“信息发现后未稳定转化为结构化判断”，尚无独立资源专属 Breakpoint；
- 当前证据只支持基于 GPU、VRAM、Disk 与 Time Budget 做基础约束判断；
- 当前不支持精确训练耗时预测、完整存储需求预测、GPU 成本估算、资源配置优化或 GPU 调度进入 P0。

因此当前保留：

> **Resource Constraint Signal / Contextual Gate Constraint**

### 2.4 Final Screening Result

当前 MVP 最终保留三个核心 Readiness Dimensions：

1. `RD-01｜Data & Access Readiness`
2. `RD-02｜Environment & Dependency Readiness`
3. `RD-03｜Weights & Configuration Readiness`

并保留：

- `Evidence-linked Findings`：P07 横向机制；
- `Resource Constraint Signal`：P04-light 上下文 Gate Signal；
- `Evaluation Conflict Signal`：P06-light Warning / Unknown Signal。

同时保持以下非 Dimension 边界：Repository Understanding 属于 Evidence 获取能力；Safety 属于产品执行边界；Collaboration / Handoff 与 Persistent State / Decision Update 属于后续工作流能力，不进入当前核心 Readiness Dimension。

---

## 3. Evidence Mapping

### 3.1 Sprint 1 × Sprint 2 双证据映射

| Dimension | Sprint 1 Problem Evidence | Sprint 2 Baseline Evidence | Decision Breakpoint | Decision |
|---|---|---|---|---|
| **RD-01 Data & Access** | P-01：数据获取、访问权限与路径要求难以提前确认；Q11 数据/权限问题 7/20（35%）；命令/配置/路径说明缺失 5/20（25%）；公开案例存在数据缺失、访问限制、metadata / 输入格式问题 | A / C 能识别数据、权限与 Unknown；B 虽发现 DFDC 获取要求等信息，但未稳定转化为完整 Readiness 判断 | D-002｜信息发现 → 结构化决策转换不足 | KEEP |
| **RD-02 Environment & Dependency** | P-02：依赖、版本与环境兼容问题；Q11 依赖冲突 11/20（55%）；Python / CUDA / Framework 不匹配 8/20（40%）；公开案例存在依赖、编译与环境兼容问题 | A / C 能将环境条件纳入判断；B 已读取环境材料，但未完整转换为结构化条件与 Gate | D-002｜信息发现 → 结构化决策转换不足 | KEEP |
| **RD-03 Weights & Configuration** | P-03：权重缺失 / 不兼容与配置不完整；Q11 权重缺失或不兼容 8/20（40%）；命令/配置/路径说明缺失 5/20（25%）；公开案例存在 checkpoint、配置、加载契约问题 | A / C 能识别权重、配置与论文—代码差异；B 已读取脚本与参数信息，但未完整进入最终结构化判断 | D-002｜信息发现 → 结构化决策转换不足 | KEEP |

### 3.2 Evidence Mapping 结论

三个 Dimension 均同时具有：

- 可识别的 Sprint 1 Problem Evidence；
- 复现前至少部分可核验属性；
- Sprint 2 Baseline 中的实际判断需求；
- 对 Blocker / Warning / Unknown 与 Overall Gate 的实际影响。

三个 Dimension 并不存在三个彼此独立的 Baseline Breakpoint，而是共同服务于同一个跨维度断点：

> **Evidence Discovery → Evidence Organization → Readiness Decision → Next Action**

需要特别说明：

- Baseline Evidence 用于证明这些条件需要进入结构化准备判断，不用于证明 ResearchOps 已优于 Baseline；
- Sprint 1 H5 的 18/20（90%）仅表示“环境 + 数据/路径 + checkpoint/配置”对有效公开案例的联合覆盖，不代表任何单一 Dimension 的覆盖率，也不代表产品诊断准确率。

---

## 4. Final Dimension Definitions

### 4.1 Dimension Summary

| ID | Dimension | 核心用户问题 | 核心检查范围 | 当前不负责 | Gate Role |
|---|---|---|---|---|---|
| **RD-01** | Data & Access Readiness | 我是否知道需要什么数据、从哪里获得、是否有权限，以及是否存在数据侧前置问题？ | Dataset / Subset、获取入口、注册/申请/审批/权限、关键文件、metadata / split / annotation、路径与输入格式、数据相关冲突与 Unknown | 自动下载完整 Dataset、自动申请权限、代接受 License / Terms、完整预处理、完整数据质量审计、运行后通用 Debug | Direct |
| **RD-02** | Environment & Dependency Readiness | 用户当前环境与项目要求是否基本匹配，是否存在明确版本冲突或重要兼容风险？ | Python、Framework、CUDA / Runtime / Toolkit、关键 Dependency、环境文件、明显版本差异、用户已提供环境与项目要求的匹配关系 | 自动安装依赖、自动修改 Conda / Python / CUDA / Driver、自动解决所有编译问题、通用 Debug Agent | Direct |
| **RD-03** | Weights & Configuration Readiness | 当前复现所需权重、checkpoint、配置与关键参数是否能够定位并合理匹配？ | pretrained weights / checkpoint、下载入口、配置文件、关键参数、模型初始化、权重—模型结构匹配、论文—代码配置差异 | 自动训练替代权重、自动修复 checkpoint、自动改模型结构、复杂超参数搜索、保证实际加载成功或最终指标 | Direct |

### 4.2 RD-01｜Data & Access Readiness

**Definition**

用于判断当前复现所必需的数据资产、获取方式、访问权限及关键输入要求是否已经明确，以及是否存在能够在正式投入前识别的数据侧阻塞、风险或 Unknown。

RD-01 关注的是：

> **用户是否具备进入数据准备阶段所需要的基本信息与访问条件。**

它不要求完整数据集已经下载、预处理并通过训练验证。

### 4.3 RD-02｜Environment & Dependency Readiness

**Definition**

用于判断论文 / Repository 所要求的软件环境、关键依赖与用户当前环境之间，是否存在明确兼容条件、冲突风险或尚未确认的重要差异。

RD-02 关注的是：

> **在正式配置和运行前，是否已经能识别关键环境要求与明显兼容问题。**

它不负责替用户自动搭建或修改环境。

### 4.4 RD-03｜Weights & Configuration Readiness

**Definition**

用于判断当前复现路径所需要的模型权重、Checkpoint、配置文件及关键运行参数是否能够被定位和合理匹配，以及是否存在资产缺失、配置冲突或重要 Unknown。

RD-03 关注的是：

> **复现所需模型资产和配置契约是否基本具备。**

它不保证权重在实际运行阶段一定能够成功加载，也不提前保证最终实验效果。

### 4.5 Cross-cutting / Gate Mechanisms

#### Evidence-linked Findings

Evidence 是所有 Readiness 判断的可信度基础，而不是独立 Dimension。

关键 Finding 应能够说明：

- 当前判断是什么；
- Evidence Source / Location 在哪里；
- 当前内容属于 Fact、Inference 还是 Unknown；
- 是否影响 Gate；
- 如需要，下一步应核验什么。

原则：

> **Citation 存在 ≠ 事实已经独立验证。**

#### Resource Constraint Signal

当前可使用：

- GPU；
- VRAM；
- Disk；
- Time Budget。

仅用于判断当前是否存在明显：

- Resource Blocked Signal；
- Resource Warning Signal；
- Resource Unknown Signal。

当前不提供完整 Resource Ready 认证。

#### Evaluation Conflict Signal

当发现明显的：

- Dataset split；
- Metric definition；
- Aggregation method；
- Paper / Code evaluation setting；

冲突时，可形成 Warning / Unknown Signal。

当前不建设完整 Evaluation Alignment Dimension。

---

## 5. Readiness Status Rules

### 5.1 四种状态语义

所有核心 Dimension 统一使用：

| Status | 核心含义 | 最低证据要求 |
|---|---|---|
| **Ready** | 当前 Gate-critical 条件已有足够证据支持基本满足，且无重要已知问题 | Positive / sufficient evidence |
| **Warning** | 已知存在风险、差异或非理想条件，但尚未证明会阻止继续 | Known risk evidence |
| **Blocked** | 已有明确证据证明某个 Gate-critical 必要条件当前不满足 | Explicit blocking evidence |
| **Unknown** | 当前证据不足、互相冲突或缺少关键输入，无法可靠判断 | Missing / conflicting / insufficient evidence |

四种状态用于表达：

> **当前证据支持下的准备度判断。**

不用于承诺实际运行一定成功。

### 5.2 Status Resolution Order

每个 Dimension 可以包含多个 Finding，但最终只输出一个 Dimension-level Status。

按以下顺序判断：

1. 存在 confirmed Gate-critical Blocker → `Blocked`；
2. 无 Blocker，但存在 Gate-critical Unknown → `Unknown`；
3. Gate-critical 条件基本明确，但存在已知非阻塞风险 → `Warning`；
4. Gate-critical 条件已有足够证据，且无重要 Blocker / Unknown / Warning → `Ready`。

### 5.3 必须保持的状态原则

- **No Finding ≠ Ready**；
- **没有找到 ≠ 确认不存在**；
- **Unknown ≠ Blocked**；
- **Warning ≠ Unknown**；
- Blocked 必须有明确负向证据；
- Ready 必须有足够正向 Evidence；
- Ready 不保证后续实际运行成功。

### 5.4 代表性示例

| 场景 | 建议状态 |
|---|---|
| 已知 Dataset 需要申请，但当前无法确认用户是否获得权限 | Unknown |
| Dataset 明确无法获得，且无替代路径 | Blocked |
| 用户环境与推荐 CUDA 版本存在差异，但尚无证据证明不兼容 | Warning |
| Repository 缺少足够信息确认关键 Python / Framework 要求 | Unknown |
| 必需 checkpoint 明确不存在，且无替代路径 | Blocked |
| checkpoint 可定位、配置关系明确且无重要已知冲突 | 可支持 Ready |

### 5.5 Contextual Signal 规则

Resource Constraint Signal 可为：

- **Blocked Signal**：存在明确最低资源要求，且当前资源明确低于该必要条件；
- **Warning Signal**：存在明显资源余量或投入风险，但尚未证明一定无法继续；
- **Unknown Signal**：项目资源要求或当前 GPU / VRAM / Disk / Time Budget 信息不足，无法可靠比较。

Resource Constraint Signal 不输出完整的正向 Ready 认证。

Evaluation Conflict Signal 当前仅为：

- **Warning Signal**：已知存在评测口径差异，但尚未证明会阻止复现；
- **Unknown Signal**：无法确定应采用哪个评测口径。

Evaluation Conflict Signal 当前不独立产生 P0 Blocked。

Resource / Evaluation Signal 不生成新的核心 Dimension Status。

---

## 6. Overall Gate & Cross-Dimension Rules

### 6.1 Overall Gate

Overall Gate 与 Dimension Status 不同：

- Dimension Status 描述某一类准备条件当前处于什么状态；
- Overall Gate 描述用户当前是否适合进入下一阶段投入。

当前 Overall Gate 固定为：

| Overall Gate | 含义 |
|---|---|
| **PROCEED** | 当前核心准备条件已有足够证据支持，可以进入下一阶段 |
| **CONDITIONAL PROCEED** | 当前无明确硬阻塞，但仍存在需要先核验或缓解的 Warning / Unknown |
| **PAUSE** | 当前存在已确认 Gate-critical Blocker，应先解除阻塞再继续高成本投入 |

PAUSE 不表示永久放弃项目；PROCEED 也不表示保证复现成功。

### 6.2 Gate Resolution Rules

Overall Gate 按以下规则聚合：

1. 任一核心 Dimension = `Blocked`，或存在 confirmed Resource Blocked Signal → **PAUSE**；
2. 无 confirmed Blocker，但任一核心 Dimension = `Warning / Unknown`，或存在 Resource / Evaluation Warning / Unknown Signal → **CONDITIONAL PROCEED**；
3. RD-01 / RD-02 / RD-03 均为 `Ready`，且不存在 material Resource Constraint 或优先 Evaluation Conflict → **PROCEED**。

Gate 不采用：

- 平均分；
- 多数投票；
- 加权总分。

Unknown 默认不升级为 PAUSE。`CONDITIONAL PROCEED` 只支持继续低成本、可逆的核验或准备行为；进入高成本复现前，应优先解决 Gate-critical Unknown。

### 6.3 Next Action Priority

Next Action 默认按以下顺序：

> **1. Resolve Blocker**  
> **2. Resolve Gate-critical Unknown**  
> **3. Mitigate Warning**  
> **4. Minimum Validation**  
> **5. Higher-cost Reproduction**

只有在关键 Gate 条件满足后，才建议进入 full dataset preparation、long training、large-scale preprocessing 或 high-cost GPU execution。

每个 `PAUSE` 或 `CONDITIONAL PROCEED` 结果至少应对应一条明确的 Next Action，用于说明下一步需要解除、核验或缓解什么。

Minimum Validation 可以包括：

- environment smoke test；
- small-sample inference；
- minimum data check；
- checkpoint load check。

当前 Next Action 是决策建议，不等于系统自动执行。

### 6.4 Cross-Dimension Rules

当前 MVP 保留以下八条跨维规则：

1. **Primary Ownership**：每个 Finding 只有一个 Primary Dimension 或 Signal Type；
2. **Related Dimension**：一个 Finding 可以关联其他受影响 Dimension；
3. **No Double-counting**：同一 Root Cause 不重复建立多个等价 Finding，也不重复计算为多个 Blocker；
4. **Conflict Preservation**：Paper / README / Repository / Config / User Environment 之间的关键冲突必须显式保留，不静默覆盖；
5. **Fact / Inference / Unknown Separation**：事实、推断与未知必须分离，Inference 必须可追溯到 Evidence，Unknown 不得被猜成 Fact；
6. **Unknown Propagation**：一个 Dimension 的 Unknown 不自动传播到其他 Dimension；只有当另一 Dimension 的判断确实依赖同一必要未知事实时，才建立跨 Dimension 影响；
7. **Gate-critical Flag**：Finding 必须区分 `gate_critical = true / false`；只有 Gate-critical Finding 才能单独触发 Blocked、Gate-critical Unknown 或 PAUSE；
8. **Evidence Traceability**：跨 Dimension 的 Finding、冲突与关联关系必须能够回溯到 Evidence。

示例：

> 某 checkpoint 只能在特定 PyTorch 版本下正常加载。

可定义为：

- Primary Dimension：RD-03｜Weights & Configuration；
- Related Dimension：RD-02｜Environment & Dependency；
- 只维护一个 Root Finding。

### 6.5 Resource / Evaluation Attachment

Resource Constraint 保持独立 Signal，不因磁盘或显存不足直接改写成新的 Resource Dimension。

若资源问题与某个复现阶段相关，可以建立 contextual link，但应保持：

> **数据问题 ≠ 资源问题。**

Evaluation Conflict 同样按其实际语义作为独立 Signal 处理，不因为冲突出现在 Repository 文件中就强行归入 Configuration Dimension。

---

## 7. Final Decision & Validation Items

### 7.1 Final Frozen Definition

**Decision：FROZEN FOR MVP CONCEPT DESIGN**

当前核心结构冻结为：

| Item | Frozen Decision |
|---|---|
| Core Dimensions | RD-01 Data & Access；RD-02 Environment & Dependency；RD-03 Weights & Configuration |
| Dimension Status | Ready / Warning / Blocked / Unknown |
| Cross-cutting Mechanism | Evidence-linked Findings |
| Contextual Signal | Resource Constraint Signal |
| Lightweight Observation Signal | Evaluation Conflict Signal |
| Overall Gate | PROCEED / CONDITIONAL PROCEED / PAUSE |
| Next Action Priority | Blocker → Gate-critical Unknown → Warning → Minimum Validation → Higher-cost Reproduction |

当前决策流程为：

> **Evidence → Finding → Dimension / Signal → Status → Gate Impact → Overall Gate → Next Action**

### 7.2 当前仍需验证

本文件冻结的是 MVP Concept Design 的结构，不代表产品效果已经成立。

后续 Concept Test 重点验证：

1. 用户能否理解三个核心 Dimension；
2. 用户能否区分 Ready / Warning / Blocked / Unknown；
3. 用户是否能够定位并使用关键 Evidence 核对 Finding；
4. Overall Gate 是否帮助用户形成“继续 / 有条件继续 / 暂停”的阶段判断；
5. 用户能否明确说出第一优先 Next Action；
6. Resource Constraint Signal 的轻量表达是否足够清晰；
7. 当前三个核心 Dimensions 是否足以支持“是否值得开始复现”的判断，并能够承载主要复现前条件。

当前不得宣称：

- 三维结构已经通过真实用户验证；
- ResearchOps 已优于通用大模型或 Codex；
- H2 / H3 已正式成立；
- 当前 Readiness 判断已经证明具有足够产品准确性。

### 7.3 下游交接边界

后续 PRD、IA、Field Dictionary、Output Schema 与 Figma 应继承本文件的核心语义，但各自只继续定义其职责范围内的内容：

- PRD：用户流程、功能需求与验收；
- IA：信息对象、页面层级与下钻关系；
- Field Dictionary / Schema：字段与机器可读结构；
- Figma：页面表达与 Concept Test 原型。

本文件不再预定义详细页面、字段、事件、权限交互或完整 Concept Test 执行方案。Safety 仍属于产品执行边界而非 Readiness Dimension；涉及授权、删除、覆盖或高风险执行的能力如在后续版本引入，必须保留 Human Confirmation。

如后续需要改变核心 Dimension、Status、Gate 或 P0 / P1 / P2 边界，应形成新的产品决策，而不是在下游文件中静默修改。

---
