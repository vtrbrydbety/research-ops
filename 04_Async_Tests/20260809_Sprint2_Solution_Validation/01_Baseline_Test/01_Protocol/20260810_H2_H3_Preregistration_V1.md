# H2 / H3 Preregistration

Preregistration ID: H2_H3_Preregistration_V1
Version: V1
Date: 2026-08-10
Status: FREEZE

Purpose:
在正式验证开始前，预先冻结 H2 / H3 的研究问题、比较对象、
指标、通过门槛、判定规则以及 Sprint 2 可支持与不可支持的结论。

本文件不记录实验结果，也不根据后续观察修改原始通过标准。

## 1. H2 Preregistration

### 1.1 Hypothesis

H2:
稳定的 ResearchOps 结构化准备卡是否比通用大模型自由对话，
更帮助用户完成可执行的复现决策。

### 1.2 Formal Comparison

Control:
通用大模型自由对话 Baseline

Treatment:
ResearchOps 结构化复现准备度方案

正式验证时，两组应尽量保持以下条件一致：

- 相同复现任务；
- 相同论文与 Repository 基础材料；
- 相同用户硬件、系统、存储和时间约束；
- 相同任务目标；
- 尽量控制模型、上下文及其他非产品结构因素。

本次 Sprint 2 Baseline A 仅用于建立 Control 的基线表现，
不等同于完成 H2 正式验证。

### 1.3 Core Metrics

H2 正式验证的核心指标为：

1. Task Completion Rate
   用户是否能够完成复现准备判断，并形成明确、可执行的决策。

2. Median Decision Time
   从开始执行任务到形成最终复现决策及第一步行动的中位耗时。

### 1.4 Passing Threshold

H2 的原预注册通过门槛为：

满足以下至少一项：

- ResearchOps 的任务完成率高于自由对话 Baseline；

或

- ResearchOps 的中位决策时间相比自由对话 Baseline 下降 ≥30%。

### 1.5 Decision Rule

只有在正式对照条件满足，并获得足以支持比较的真实测试数据后，
才允许对 H2 做正式判定。

若仅观察到部分效率改善、个别用户理解更快或单次输出质量更好，
只能记录为探索性支持信号，不得据此判定 H2 正式通过。

### 1.6 Sprint 2 Boundary

Sprint 2 中：

- Baseline 同题测试用于建立现有替代方案的对照表现；
- Figma / Concept Test 主要验证用户是否理解准备度结论、风险和下一步行动；
- Sprint 2 可以记录与 H2 相关的探索性信号；
- 在 ResearchOps 尚未形成稳定产品输出、且未完成正式受控对照前，不判定 H2 通过。

### 1.7 What Sprint 2 Cannot Claim

Sprint 2 结束时，除非正式验证条件已满足，否则不得声称：

- H2 已被正式验证；
- ResearchOps 已证明优于通用大模型；
- ResearchOps 已证明任务完成率更高；
- ResearchOps 已证明决策时间下降 ≥30%。

允许表述为：

“观察到与 H2 一致的探索性信号，正式验证仍待后续实验完成。”


## 2. H3 Preregistration

### 2.1 Hypothesis

H3:
证据定位机制是否能够提升用户对复现准备判断的信任与纠错能力。

具体研究问题：

用户是否会主动查看 ResearchOps 提供的证据，
并利用这些证据发现、确认或修正复现准备判断中的问题。

### 2.2 Validation Object

H3 关注的不是“用户觉得有证据很好”，
而是用户是否真实产生与证据相关的行为。

正式验证应观察用户在 ResearchOps 准备度结果中的证据查看和纠错过程。

### 2.3 Core Behaviors

H3 重点记录以下行为：

1. Evidence Expand
   用户是否主动展开或查看某条判断对应的证据。

2. Evidence Location
   用户是否进一步定位到论文、README、Repository、
   GitHub Issue 或其他具体证据来源。

3. Return to Decision
   查看证据后，用户是否返回原判断、风险或准备度结论进行核对。

4. User Correction
   用户是否基于证据指出、确认或修正至少一个问题。

### 2.4 Passing Threshold

H3 的原预注册通过门槛为：

同时满足以下两个条件：

- ≥60% 的测试用户主动查看证据；

且

- 至少 2 名测试用户能够基于证据指出或修正至少 1 个问题。

只有两个条件同时满足，才达到 H3 的正式通过门槛。

### 2.5 Decision Rule

以下情况不能单独视为 H3 通过：

- 用户表示“有证据更可信”，但没有实际查看证据；
- 用户点击或展开证据，但没有利用证据核对判断；
- 用户查看证据，但没有发现、确认或修正任何问题；
- 个别用户完成纠错，但整体主动证据查看比例未达到 60%。

正式判定必须依据实际用户行为记录，而不是仅依据主观评价。

### 2.6 Sprint 2 Boundary

Sprint 2 的 Figma / Concept Test 可以记录：

- 是否主动展开证据；
- 是否尝试定位证据来源；
- 是否返回准备度判断进行核对；
- 是否利用证据提出质疑或纠错。

这些结果在 Sprint 2 中主要作为 H3 的探索性信号。

由于 Sprint 2 Concept Test 预计仅包含少量真实用户，
其结果不得自动视为 H3 正式通过。

### 2.7 What Sprint 2 Cannot Claim

除非正式验证条件和样本要求均已满足，否则 Sprint 2 不得声称：

- H3 已被正式验证；
- 证据定位已被证明能够提升用户信任；
- 证据定位已被证明能够提升纠错能力；
- ≥60% 用户主动查看证据的正式门槛已经稳定成立。

Sprint 2 可使用的表述为：

“概念测试中观察到与 H3 一致的证据查看与纠错行为信号，
但正式验证仍需后续实验完成。”


## 3. Preregistration Freeze Rules

1. H2 / H3 的研究问题、正式比较对象、核心指标、通过门槛和判定边界在正式验证前冻结。

2. 后续不得根据 Baseline、Concept Test 或其他实验结果修改原始通过门槛。

3. Sprint 2 中观察到的结果若尚未满足正式实验条件，只能记录为：
   - 支持性探索信号；
   - 反驳性探索信号；
   - 仍不确定。

4. 不得将单个案例、个别用户表现或主观反馈直接写成 H2 / H3 正式通过。

5. 若后续确认预注册本身存在设计错误，应：
   - 保留 V1；
   - 记录修改原因；
   - 创建新版本；
   - 明确旧版本与新版本的适用实验范围；
   - 不得覆盖原始 V1。

6. 所有正式 H2 / H3 结论必须基于对应版本的预注册规则进行判定。