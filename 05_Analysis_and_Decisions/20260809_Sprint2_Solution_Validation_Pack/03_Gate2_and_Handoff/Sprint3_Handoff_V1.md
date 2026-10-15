# ResearchOps — Sprint 3 Handoff V1

**Stage:** Sprint 2 → Sprint 3  
**Date:** 2026-09-09  
**Gate 2:** CONDITIONAL  
**Current PRD:** V0.9  
**Current Prototype:** Figma Prototype V3.6  

## 1. Handoff 目标

Sprint 2 已完成 ResearchOps 的主要产品设计工作。

Sprint 3 不再继续扩充 PRD 或页面，而是将现有产品定义转化为：

> **最小可运行的 Reproduction Readiness Assessment MVP**

目标不是实现完整 ResearchOps，而是先跑通真实输入到结构化判断的核心闭环。

## 2. 冻结的产品定义

### 唯一 P0 主路径

> Reproduction Readiness Assessment

用户提供论文 / Repository 等目标后，系统帮助判断：

- 当前是否适合开始复现；
- 主要风险或 Unknown 是什么；
- 判断依据在哪里；
- 下一步最应该做什么。

### 三个核心 Dimension

- RD-01｜Data & Access Readiness
- RD-02｜Environment & Dependency Readiness
- RD-03｜Weights & Configuration Readiness

状态统一使用：

- Ready
- Warning
- Blocked
- Unknown

Overall Gate 继续使用：

- PROCEED
- CONDITIONAL PROCEED
- PAUSE

## 3. Sprint 3 最小主链

```text
Input Paper / Repository
→ Collect Materials
→ Extract Reproduction Conditions
→ Generate Findings
→ RD-01 / RD-02 / RD-03 Status
→ Overall Gate
→ Evidence
→ First Next Action
```

首版只要求跑通这一条链路。

## 4. 最小输入与分析范围

用户至少提供一个可识别目标：

- Paper Title / DOI / arXiv；
- Paper URL；
- GitHub Repository；
- Project Page。

首版重点分析：

### RD-01
- Dataset；
- 获取入口；
- Access / Application Requirement；
- Split / Path / Input Format；
- 明显缺失信息。

### RD-02
- Python；
- Framework；
- CUDA；
- Dependency；
- requirements / environment 文件；
- 明显版本约束。

### RD-03
- Pretrained Weight / Checkpoint；
- Config；
- Model Setting；
- 关键加载要求。

## 5. Evidence 与 Unknown 原则

关键 Finding 应尽量保留：

- Source；
- Location；
- Evidence Summary；
- Readiness Impact。

无法确认的信息必须保留为 `Unknown`，不通过猜测补齐。

## 6. Gate 与 Next Action

Sprint 3 不重新设计 Gate 规则。

基本原则：

- 关键 Blocker → PAUSE；
- Gate-critical Unknown / Warning → CONDITIONAL PROCEED；
- 关键条件满足 → PROCEED。

同时输出一个明确的：

> First Next Action

## 7. Safety Boundary

Sprint 3 首版保持 **Authorized Read-only**。

可以：

- 读取用户提供和公开材料；
- 分析 Paper / README / Repository / Config；
- 输出 Readiness、Evidence、Gate 与 Next Action。

不做：

- 自动安装依赖；
- 修改 CUDA / Driver / 用户环境；
- 删除或覆盖文件；
- 自动训练；
- 自动完整复现；
- 高成本自动执行。

## 8. Sprint 3 P0 实现优先级

1. **Real Target Input**  
   Paper / Repository → Create Assessment

2. **Material Discovery**  
   至少处理 README、Repository、requirements / config、公开权重或数据入口。

3. **Structured Findings**  
   输出 Dimension / Status / Finding / Evidence / Unknown。

4. **Overall Gate**  
   输出 PROCEED / CONDITIONAL PROCEED / PAUSE。

5. **First Next Action**  
   明确用户当前最优先处理的一步。

6. **Demo UI**  
   跑通 Input → Analysis → Readiness Result → Evidence → Next Action。

## 9. Sprint 3 验收标准

至少完成一个真实案例 End-to-End：

- 输入真实 Paper + Repository；
- 自动分析必要材料；
- 输出 RD-01 / RD-02 / RD-03；
- 输出 Status、Main Risk、Overall Gate；
- 输出至少一个可追溯 Evidence；
- 输出 First Next Action；
- 不修改用户环境。

满足后可标记：

> **MVP Alpha Ready**

## 10. 首个 Demo Case

继续使用：

> Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies（FGI）

这样可以沿用 Sprint 1 / Sprint 2 已形成的案例、Baseline 与原型上下文，不需要重新搭建测试场景。

## 11. MVP 后恢复验证

当 MVP 能真实处理 FGI 输入后，再执行之前 Deferred 的 Concept Test，重点验证：

- 用户是否理解 Overall Gate；
- 是否能指出 Main Risk；
- 是否能明确 First Next Action；
- 是否会查看 Evidence；
- 是否能发现或纠正系统判断问题。

之后再重新评估 Gate 2 是否升级为 PASS。

## 12. Sprint 3 建议交付物

只保留少量高价值产出：

1. `Sprint3_MVP_Scope_V1.md`
2. 可运行 MVP
3. `MVP_Architecture_V1`
4. FGI Demo Result
5. README / Demo Guide
6. MVP Validation Record
7. 更新后的 `PROJECT_STRUCTURE.md`

## 13. Handoff Decision

**HANDOFF READY**

Sprint 3 默认继承：

- PRD V0.9；
- Figma Prototype V3.6；
- 三核心 Dimension；
- 四种 Status；
- Evidence-linked Findings；
- 三种 Overall Gate；
- First Next Action；
- Authorized Read-only Safety Boundary。

除非新的实现证据或用户验证结果证明现有规则存在问题，否则 Sprint 3 不重新打开上述产品定义。
