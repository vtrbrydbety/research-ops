# Opportunity & Readiness Analysis

Document ID: 20260810_Opportunity_Readiness_Analysis_V1  
Version: V1  
Date: 2026-08-10  
Status: COMPLETED

## 1. Analysis Objective

基于 Sprint 1 用户/公开案例证据，以及 Sprint 2 Baseline A / B / C 同题测试结果，识别 ResearchOps 当前最值得解决的产品机会，并判断这些机会是否已有足够证据进入后续 Concept Test 与产品规格设计。

本分析不用于证明 H2 / H3 成立，也不用于声明 ResearchOps 已经优于通用大模型、人工流程或 Codex。

本分析同时遵守 Sprint 1 Gate 1 已冻结的产品优先级边界：

- 唯一 P0 主路径仍为：**复现前准备度评估**；
- P0 主路径继续覆盖：
  - P01｜数据与权限；
  - P02｜依赖与环境；
  - P03｜权重与配置；
  - P07｜证据链；
- P04｜资源需求、P05｜运行后诊断仍为 P1；
- P06｜评测口径仍为 P2 / 持续观察项。

Sprint 2 的目标不是重新划分 P0 / P1 / P2，而是在既有问题优先级不变的前提下，进一步收敛 P0 主路径的 MVP 产品形态。

---

## 2. Baseline Evidence Summary

### 2.1 Baseline A｜通用大模型自由对话

- Formal Decision Time 为 5 分钟，User Follow-up Count 为 0。
- 在 Baseline Rubric V1 的六个质量维度中均达到 2 分锚点。
- 首轮即可形成明确的“有条件继续”判断，并覆盖环境、数据权限、磁盘、算力 / 显存、训练时间、论文—代码不一致以及后续行动路径。
- 能够通过公开 Web 与 Repository 检索形成较完整的复现准备判断。
- 内部搜索次数、材料切换和部分工具过程无法完全观察。
- 当前评分说明其输出在结构、覆盖和证据可追溯性上达到 Rubric V1 高锚点，但不代表其中所有技术事实均已被独立验证。

### 2.2 Baseline B｜人工现有流程

- Formal Decision Time 为 56 分钟，未超时。
- 决策完整性达到 2 分，其余五个质量维度均为 1 分。
- 人工执行过程中实际读取或核对了论文、README、package-list.txt、DFDC 数据获取方式、训练脚本、测试脚本和部分实验参数。
- 最终输出却主要集中在训练集分块、训练集大小和磁盘空间问题。
- 因此本轮最明显的 Decision Breakpoint 不是“无法找到信息”，而是：

  > **信息发现 → 结构化决策转换不足**
- 人工流程存在明显的跨材料搜索、阅读、核对和整合成本。

### 2.3 Baseline C｜Codex App

- Formal Decision Time 为 7 分钟，User Follow-up Count 为 0。
- 另外存在 5 分钟 Pre-test Setup Cost，用于 clone Repository、checkout Frozen Commit 和在 Codex App 中打开项目。
- 在 Baseline Rubric V1 的六个质量维度中均达到 2 分锚点。
- 对 Repository 中环境、数据、训练、测试、参数和代码路径具有较强的文件级 / 代码级定位能力。
- 能够把主要未知映射为资源与授权 Gate、冒烟测试和短训练标定等行动。
- Codex App 的内部搜索、命令和文件切换次数无法完全观察。
- Repository workspace 带来了较强代码理解能力，但同时存在额外 Setup Cost。

### 2.4 Cross-Baseline Observation

当前 Baseline 结果表明：

1. 人工流程的主要问题不仅是信息搜索成本，更重要的是从分散证据到完整决策之间存在较高的组织和整合成本。
2. 通用大模型已经能够在很短时间内生成高质量的单次复现准备判断，因此“生成一份完整复现建议”本身不足以构成 ResearchOps 的核心差异化。
3. Codex 已经能够提供较强的代码仓库级分析能力，因此 ResearchOps 不能仅依靠“自动阅读 Repository”建立产品价值。
4. A 与 C 在当前 Baseline Rubric V1 中均达到全部最高锚点，表明当前 Rubric 对高质量 AI 工具出现 ceiling effect；本轮不得通过事后修改 Rubric 或重新评分来人为拉开差距。
5. 当前更值得继续验证的产品机会应收敛在：
   - 结构化准备度；
   - 统一证据呈现；
   - 明确下一步行动。
6. 这些机会是对 Sprint 1 P0 主路径的**解决方案形态收敛**，不是重新定义新的 P0 / P1 / P2。

---

## 3. Opportunity Statements

### O1｜Structured Readiness Card

**Opportunity Statement**

ResearchOps 将论文、Repository 与用户环境中的分散信息统一整理为结构化的复现准备度结果，至少包含：

- 关键缺失项；
- 主要风险；
- Unknown；
- Readiness 状态。

**对应 Sprint 1 范围**

O1 主要承接：

- P01｜数据与权限；
- P02｜依赖与环境；
- P03｜权重与配置；

并服务于唯一 P0 主路径：

> **复现前准备度评估**

其中可读取 GPU、显存、磁盘、时间预算等用户资源约束，用于形成当前准备度判断；但这不等同于把 P04 资源需求整体升级为 P0。

P0 中只需要回答：

> 当前已有资源条件是否构成明显阻塞 / 风险 / Unknown？

而完整的训练时间预测、资源成本估算、GPU 配置优化等能力仍属于 P04｜P1。

**Why this opportunity exists**

Sprint 1 已将“复现前准备度评估”确定为 P0 主路径；问题侧证据支持用户在真正投入下载、配环境和运行前，会遇到数据、环境、权重、配置等可提前核验的问题。

Sprint 2 Baseline B 又进一步表明：人工流程并非完全找不到信息，而是在有限时间内难以把分散材料完整转化为结构化判断。

**Potential Product Value**

ResearchOps 不需要比通用大模型“回答得更长”，而是通过固定信息结构降低遗漏，让用户更快看清：

> 当前是否适合继续、卡在哪里、哪些还不知道。

---

### O2｜Evidence-linked Findings

**Opportunity Statement**

ResearchOps 在 Readiness Card 中，将关键判断与论文、README、源码或外部页面依据以统一产品结构呈现，降低用户在长对话或多个材料之间定位和核对证据的成本。

**对应 Sprint 1 范围**

O2 主要承接：

- P07｜证据链。

它不是 Sprint 2 新增出来的需求，而是把 Sprint 1 已冻结的“关键判断必须有依据、未知不可猜测”进一步落实为产品表现形式。

**Why this opportunity exists**

Baseline A 与 C 已经证明现有 AI 工具可以提供较好的证据引用，尤其 Codex 能做到源码文件和行级定位。

因此：

> **“提供 citation”本身不应被视为 ResearchOps 的独有能力。**

真正值得验证的是：

> 当证据被固定呈现在结构化 Readiness Card 中时，用户是否更容易理解结论、定位依据并发现问题。

**Potential Product Value**

ResearchOps 的价值不是“比 ChatGPT / Codex 提供更多引用”，而是把 Evidence-linked Findings 标准化到固定产品界面中，使关键结论更容易核对和纠错。

---

### O3｜Next Action / Gate

**Opportunity Statement**

ResearchOps 将复现准备判断进一步转化为按优先级排列的下一步行动，并对关键条件呈现：

- Ready；
- Warning；
- Blocked；
- Unknown。

**对应 Sprint 1 范围**

O3 不是新的问题类别，而是 P0“复现前准备度评估”的输出与行动引导机制。

它承接的是：

> 准备度判断完成后，用户下一步应该做什么。

不改变 P04 / P05 / P06 的优先级。

**Why this opportunity exists**

Baseline A 与 C 都自然形成了：

> 环境检查 → 数据 / 磁盘检查 → 最小闭环 → 再决定是否全量训练

这样的行动路径，说明 Gate 式表达与复现准备任务高度匹配。

Baseline B 虽然给出了前三步行动，但由于前置缺失和风险没有完整结构化，行动路径也存在前提不充分的问题。

**Potential Product Value**

用户不仅知道“哪里有问题”，还可以直接知道：

> 当前第一步做什么；哪些条件通过后才能进入下一阶段。

---

## 4. Opportunity Evidence Strength

| Opportunity | Sprint 1 Evidence | Sprint 2 Baseline Evidence | Decision Log / Breakpoint ID | Evidence Strength | 当前判断 |
|---|---|---|---|---|---|
| O1 Structured Readiness Card | P0 主路径已冻结为复现前准备度评估；P01/P02/P03 为其核心检查内容 | B 暴露“信息发现 → 结构化决策”断点；A/C 证明结构化输出可覆盖主要准备问题 | D-002 | **Strong** | 进入当前 MVP |
| O2 Evidence-linked Findings | P07 证据链已属于 P0 主路径；Sprint 1 已要求关键判断可追溯、未知不可猜测 | A/C 已能提供证据绑定，说明 citation 本身不是差异化；固定 UI 是否提升理解和纠错仍需用户测试 | D-005 | **Moderate** | 进入 MVP，但 Concept Test 必须验证呈现价值 |
| O3 Next Action / Gate | P0 价值承诺已包含阶段性判断与前三步行动 | A/C 自然生成 Gate / 最小闭环；B 的行动路径受前置信息遗漏影响 | D-002；A/C 行动表现（Comparison § 4.1） | **Moderate–Strong** | 进入 MVP，并重点验证“第一步是否清晰可执行” |

### 4.1 Evidence Strength Interpretation

- **Strong**：已有 Sprint 1 问题证据与 Sprint 2 Baseline 断点共同支持，可以直接进入 MVP，不需要再次证明“问题是否存在”。
- **Moderate–Strong**：问题与方案方向均有较明确证据，但仍需要 Concept Test 验证具体交互是否真正帮助用户。
- **Moderate**：方向合理且已有部分证据，但当前尚不能证明用户会实际使用或从该设计中获得增量价值。

本轮不设置 Weak Opportunity，也不为凑功能数量新增机会。

---

## 5. Product Readiness Judgment

### 5.1 Overall Judgment

**CONDITIONAL READY FOR CONCEPT TEST / PRODUCT SPEC**

当前证据已经足够支持 ResearchOps 从“问题探索”进入“轻量 MVP 概念验证”，但还不足以声明产品效果已被验证。

### 5.2 Sprint 1 → Sprint 2 Priority Alignment

当前 P0 主路径仍保持 Sprint 1 冻结的：

> **复现前准备度评估**

并继续覆盖：

- P01｜数据与权限；
- P02｜依赖与环境；
- P03｜权重与配置；
- P07｜证据链。

Sprint 2 基于 Baseline 结果，将该 P0 主路径的 MVP 产品形态进一步收敛为：

1. **Structured Readiness Card**
2. **Evidence-linked Findings**
3. **Next Action / Gate**

因此：

> **问题优先级没有变化，变化的是 P0 主路径的解决方案表达方式变得更具体。**

### 5.3 P1 / P2 Boundary

Sprint 1 已冻结的 P1 / P2 不因本轮 MVP 收敛而改变。

#### P04｜资源需求｜P1

当前 MVP 可以读取并展示：

- GPU；
- VRAM；
- Disk；
- Time Budget；

并将其用于：

- Blocked；
- Risk；
- Unknown；

判断。

但以下能力仍不进入 P0：

- 精确训练耗时预测；
- 完整存储需求预测；
- GPU 成本估算；
- 资源配置优化；
- GPU 调度。

#### P05｜运行后诊断｜P1

仍作为辅助路径 / 后续能力，不进入当前 P0 核心闭环。

当前 Concept Test 不要求证明：

- 错误分类准确性；
- Debug 能力；
- 自动修复能力。

#### P06｜评测口径｜P2 / 持续观察

若准备度分析发现明显的：

- 数据划分冲突；
- 指标定义冲突；
- 聚合方式不一致；
- 论文 / 代码结果口径差异；

可以作为 Risk / Unknown 展示。

但当前不建设独立的高级 Evaluation Alignment 模块，也不将 P06 升级为 P0。

### 5.4 Current MVP Scope

当前 MVP 只保留三个核心模块：

1. **Structured Readiness Card**
2. **Evidence-linked Findings**
3. **Next Action / Gate**

上述三个模块描述当前 MVP 的产品结构。其中，Structured Readiness Card 统一承载复现前准备度的核心检查维度与状态。

Day 3 采用三级冻结：

#### Level 1｜已冻结：产品主路径

P0 主路径保持为 **Reproduction Readiness Assessment（复现前准备度评估）**。现有证据已足以支持该方向，D4 不重新讨论或扩展 P0 主路径。

#### Level 2｜已冻结：Readiness Card 决策结构

Readiness Card 至少包含：

> 条件 / 检查项 → 状态 → 关键发现 → Evidence → Unknown → Gate 影响 → Next Action

状态语义冻结为：

- Ready；
- Warning；
- Blocked；
- Unknown。

D4 在此结构上输出状态字段、Gate 最小规则、Evidence-linked Findings 和 Next Action 字段，不重新定义三个 MVP 模块之间的关系。

#### Level 3｜D4 冻结：Readiness Dimensions

维度候选由 **Sprint 1 Pain Point / Hypothesis Evidence × Baseline Decision Breakpoint** 双重证据映射产生。最终维度数量、正式名称、定义及 Gate 权重在 D4 PRD 中冻结，不预设必须为六维，也不为满足历史数量补足缺乏证据支持的维度。

### 5.5 Not Required for Current MVP

以下能力不作为当前校招求职项目 MVP 的必须项：

- Persistent State；
- 自动 Decision Update；
- Collaboration / Handoff；
- 完整历史 Audit Trail；
- 自动完整复现；
- 多 Agent / MCP 平台化；
- GPU 调度；
- 复杂团队项目管理。

上述能力仅保留为 Future Roadmap。

---

## 6. Open Questions

后续 Concept Test 只重点回答以下问题：

1. 用户能否在较短时间内理解 Readiness Card 的总体状态、关键缺失、风险与 Unknown？
2. Structured Readiness Card 相比自由对话，是否让用户更容易找到“当前最重要的问题”？
3. Evidence-linked Findings 是否容易被注意、理解和定位，而不是成为额外信息负担？
4. 用户是否会主动查看至少一条关键证据，并能据此发现或指出问题？
5. Ready / Warning / Blocked / Unknown 四种状态是否容易理解，是否存在语义混淆？
6. 用户能否明确说出“当前第一步应该做什么”，以及为什么先做这一步？
7. P01 / P02 / P03 / P07 是否已经被三个核心模块充分表达？
8. 当前对 P04 资源信息的轻量使用是否足够，是否误导用户理解为“系统已经完成精确资源预测”？
9. 三个核心模块是否已足够支撑“是否值得开始复现”的决策，是否存在必须补充的 P0 信息？

当前不要求 Concept Test 回答：

- P05 运行后诊断是否有效；
- P06 高级评测对齐是否有效；
- 用户是否愿意长期使用 Persistent Workspace；
- 多人协作是否有价值；
- 自动决策更新是否有效；
- ResearchOps 是否已经优于通用大模型；
- H2 / H3 是否正式通过。

---

## 7. Decision

### 7.1 Decision

**PROCEED**

基于 Sprint 1 已冻结的问题证据与 Sprint 2 A / B / C Baseline 结果，当前可以进入 Product Spec / Figma Concept Test 设计。

### 7.2 Carry Forward to MVP

- Structured Readiness Card
- Evidence-linked Findings
- Next Action / Gate
- D4 PRD 首项任务：通过 Sprint 1 Evidence × Baseline Breakpoint 双证据映射，冻结 Readiness Dimensions 的数量、正式名称、定义与 Gate 权重。

### 7.3 Priority Boundary Retained

继续保持 Sprint 1 冻结结果：

- P0：
  - 复现前准备度评估；
  - P01 数据与权限；
  - P02 依赖与环境；
  - P03 权重与配置；
  - P07 证据链。
- P1：
  - P04 资源需求；
  - P05 运行后诊断。
- P2：
  - P06 评测口径。

本轮不重新调整 P0 / P1 / P2。

### 7.4 Keep as Future Roadmap

- Persistent State
- Decision Update
- Collaboration / Handoff
- Full Audit Trail
- 精细资源预测 / 优化
- 高级评测一致性管理

### 7.5 Do Not Claim Yet

- 不声明 ResearchOps 已优于通用大模型或 Codex；
- 不声明 H2 / H3 已正式成立；
- 不把 A / C 的高 Rubric 分数解释为所有事实已经独立验证；
- 不把 Evidence-linked Findings 宣称为行业创新或 ResearchOps 独有能力；
- 不把 P04 的轻量资源输入误称为完整资源需求分析；
- 不把发现评测冲突误称为已经实现 P06 高级评测对齐能力。

### 7.6 Handoff

下一阶段不再扩大机会点，而是把上述三个 MVP 模块转换成：

1. 明确的 Product Spec；
2. 可测试的低 / 中保真页面；
3. 2–3 名真实用户可执行的 Concept Test 任务。

Non-goals 继续继承 § 5.5，不因进入 D4 而扩展当前 MVP 范围。

**Safety Boundary：**继续继承 Start Brief 与 Baseline Protocol 的安全边界。高风险执行、删除、覆盖及授权类操作必须经过人工确认；当前 MVP 只输出准备度判断、证据与行动建议，不自动执行复现，也不自动实施上述高风险操作。

本文件至此完成，可作为当前 Opportunity / Readiness 阶段的 V1 分析结论。
