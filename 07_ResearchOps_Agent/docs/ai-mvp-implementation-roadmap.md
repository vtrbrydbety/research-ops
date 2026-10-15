# ResearchOps 真实 AI MVP 实施路线图

状态：执行中  
更新时间：2026-09-17  
设计文档：只读。本路线图不修改既有 PRD、AI Solution、Prompt Design、字段字典、信息架构或 Figma 交接文档。

## 目标与边界

目标是完成真实的 ResearchOps AI MVP，而不是 FGI 固定案例演示。系统必须遵守以下决策链：

```text
Target / Material / User Context
  → AI 识别缺口与受影响范围
  → 受控确定性工具补充材料（必要时）
  → AI 提出 Evidence / Conflict / Finding 候选
  → Rule 校验证据并裁决 Status / Gate / Next Action
  → Human 反馈或补充事实
  → 仅重评受影响范围
```

- AI：理解、关联材料、识别缺口、提出候选；不得输出正式 Dimension Status、Overall Gate 或最终投入决定。
- Rule：验证来源、引用和位置；计算 Readiness Status、Overall Gate、Next Action。
- Human：确认真实 Target 歧义、授权只读环境访问、提供第一方事实、纠错并作最终投入决定。
- Evidence 必须可回溯至 Material 或 User Context；没有行号时显示真实可用定位，不伪造精确位置。
- 当前 MVP 只读；不得安装、写入、删除、训练或执行高成本复现。

## P0：阻断真实 MVP 验收的问题

### P0-1 真实模型结构化输出可靠性（已完成，2026-09-17）

**问题**：真实模型调用可能以 `invalid_model_response` 结束，导致没有任何可裁决的候选结果。

**实施**：

1. 定位 Provider 响应解析、严格工具调用/JSON Schema、重试修复提示之间的失配。
2. 保留有限重试及请求取消；失败时保存脱敏的契约失败类别、请求 ID、阶段和轮次。
3. 区分 Provider 不可用、模型输出无效、材料/工具获取失败；不得把处理失败伪装成业务 Unknown。

**验收**：

- 已配置真实模型时，跨项目最小请求可形成有效 Evidence Extraction 输出。
- 无效输出经有限修复重试后仍失败时，API 和界面显示准确处理状态及可重试原因。
- API Key 不进入响应、Trace 或普通日志。

**完成记录**：严格工具调用仍是首选；发生可恢复的工具信封/契约失败时，客户端仅一次降级至 `responses` JSON Schema 传输，并继续使用同一 Pydantic 候选契约。Trace 记录实际传输模式、请求 ID、尝试次数与脱敏失败类别；严格模式为该降级保留一个受 Trace 上限约束的尝试槽位。已通过同步、异步、有限失败及真实 Provider 的最小 Evidence Extraction 验收（严格工具与 JSON Schema 两种模式）。

### P0-2 Evidence Drawer 与 Evidence 身份连续性（已完成，2026-09-17）

**问题**：已验证 Evidence 因缺少行号、重判 revision 变化或静态回退而不可打开、错配或显示为不可用。

**实施**：

1. Evidence Drawer 使用当前 Assessment revision 中的真实 Evidence ID，不从静态 Demo 取默认数据。
2. 有文件行范围时展示文件和精确行范围；无行范围时展示真实 URL、环境字段、探测记录或其他 locator 及其粒度。
3. 反馈后的重新裁决保留仍有效的原始 Evidence，并保留与新 User Context Evidence 的关系。

**验收**：

- 当前 Finding 关联的每条已验证 Evidence 均可打开。
- 重判后不会打开旧 revision 或静态 Evidence。
- 外部链接、环境事实和探测结果不会因没有文件行号被误标记为不可用。

**完成记录**：前端 Evidence Drawer 只使用当前 Assessment API 返回的 Evidence ID；反馈不再依据已渲染的来源/位置文字猜测身份。文件材料继续显示已验证的精确行范围；无文件行号的真实 Evidence 改为展示其真实 locator，不会被过滤或以静态示例替代。反馈触发重判时会关闭旧抽屉，避免旧 revision 继续作为可操作对象。后端既有的“保留已验证 Evidence、重新纳入模型和 Rule 重判”的链路保持不变，并已由定向重判测试覆盖。

### P0-3 清理静态 Demo 与 FGI 专用生产回退（已完成，2026-09-17）

**问题**：静态页面/监听器/默认 Evidence 与真实 Assessment 并存，可能导致结果串用。

**实施**：

1. 删除或隔离只用于视觉原型的静态 Finding、Evidence、Gate 和交互监听器。
2. 真实 Assessment UI 只接受当前 API revision 返回的数据。
3. FGI 仅作为可选示例输入，不得影响任意项目的分析结果。

**验收**：

- 切换不同 Target 后没有任何 FGI 默认 Finding/Evidence 出现。
- 静态 DOM 或旧 hash 不能触发生产 Assessment 流程。

**完成记录**：MVP 不再预填 FGI 仓库或 FGI 复现目标；旧 Streamlit 入口亦改为通用示例。MVP 的旧 hash 路由在生产脚本加载后会清除并回到任务设置页；冻结原型监听器被生产层拦截，Finding/Evidence 反馈只能由当前 Assessment 的真实 ID 打开。评测冲突服务已移除基于 FGI 历史数据集文件名的选择性分支，改为对任何仓库保持确定性的来源顺序。冻结设计源文件保持未修改。

### P0-4 反馈驱动的完整重判闭环（已完成，2026-09-17）

**问题**：当前补充/纠正可触发部分重判，但不会在出现新缺口时重新规划和受控获取材料。

**实施**：

1. 接入冻结 Prompt 的 Feedback Reassessment 阶段，先识别受影响 Finding、Dimension、Signal 和新 Gap。
2. 若新 Gap 可通过允许的确定性工具解决，进入 Research Planning / Tool Acquisition；否则请求最小 Human Input 或保留 Unknown。
3. 将原始材料、原 Evidence、用户补充内容及新材料一起交给 Evidence/Finding 分析。
4. Rule 仅对受影响的真实依赖范围重新裁决；不得全局无差别重跑。
5. 单纯 Confirm 保持记录但不触发重判；Question 在没有新事实时保持 no-change。

**验收**：

- 用户“我有该数据集访问权限”作为第一方 User Context Fact，可改变对应访问条件，不要求 URL 或截图。
- 用户补充的链接/文本若揭示信息缺口，AI 可受控请求下一步材料。
- 原始 Evidence 不会被静默删除；相互矛盾时保留冲突双方。

**完成记录**：`HumanReviewService` 现接收与首次评估相同的受限 Research Loop。任何需要重判的用户材料先与原 Bundle、原 Finding/Evidence 和 `HumanReviewContext` 合并；AI Research Planning 可据此提出允许的确定性读取，工具结果再进入 Evidence、Conflict/Finding 与 Rule 链。Research Tool Executor 会在每轮保留 Human context。仅 Confirm 与未附材料的 Question 仍只留下审计记录；Question 若附带新的用户材料则进入重判。已验证反馈触发的规划、受控采集、新旧材料共同 Evidence Extraction、原证据保留，以及普通 Question 不重跑的边界。

### P0-5 Prompt Case 运行时回归（已完成，2026-09-17）

**问题**：PC-01 至 PC-09 已完成 desk test，但尚未形成运行时代码回归基线。

**实施**：将每个 Prompt Case 映射为契约测试、服务测试或真实模型冒烟验收；建立明确 Case ID 与测试名称映射。

**验收**：

- PC-01～PC-09 各有自动化覆盖和预期断言。
- PC-02、PC-05、PC-06、PC-07、PC-08、PC-09 至少各有一次真实模型或受控 Provider 集成验收。
- 回归报告明确区分 Fake Model、真实 Provider 和人工桌面测试。

**完成记录**：PC-01～PC-09 均已映射到可执行的 pytest 节点，并由 `tools/run-prompt-case-regression.ps1` 统一运行。受控 runtime / Provider 基线当前为 13 项测试并全部通过。真实 Provider 与真实仓库矩阵由 `tools/run_live_cross_project_acceptance.py` 独立执行并输出 `.acceptance/pa09-live-results.json`；其失败或 Partial 不会被受控基线掩盖。2026-09-20 的首轮真实验收仍发现 Provider 偶发无效 JSON、未知 `source_id` 与 Tool Acquisition 语义偏差，因此 PA-09 的“真实模型矩阵通过”状态保持未完成，详见 `docs/pa09-live-model-acceptance.md`。

## P1：设计已定义但需要完整落实的能力

### P1-1 独立 Feedback Reassessment 阶段（已完成，2026-09-17）

反馈不再由代码直接猜测重评范围；AI 输出受影响 Finding、Dimension、Signal 与新 Gap，再决定是否调用工具。`ContextGapSnapshot` 仅作为已支持事实、最小缺口、确认/授权需求与停止原因的审计工件，不替代本阶段。

**完成记录**：所有需要重判的反馈现在都必须先经过 `reassess_feedback`；模型不可用或未实现该阶段时明确返回配置/Provider 状态，不会回退为代码自动扩展研究范围。Rule 校验模型列出的 Finding/Evidence 引用是否属于当前 Assessment，并确认范围覆盖用户实际挑战的对象；只有 `tool_acquisition` handoff 才可进入受控研究循环。模型声明的范围、Gap、handoff、请求 ID 与耗时都保留在审计链中。

### P1-2 Context & Gap 与 Tool Acquisition 显式拆分（已完成，2026-09-17）

将可追踪 Gap、最小获取计划、Tool Result 和停止原因拆为独立工件，便于审计与调试。`ToolAcquisitionPlan` 只能引用已经识别的 `gap_id`，不得生成新 Gap，也不携带任何 Tool Result；实际执行结果仍只保留在 `ResearchToolExecutionResult`。每个 Research Loop round 现在同时保存 AI Gap 分析、独立获取计划和（如执行）确定性结果，且 Ready 的计划会明确形成 `stop_acquisition / sufficient_context` handoff。

### P1-3 官方权重逐级获取（已完成，2026-09-17）

`probe_checkpoint_access` 现在先经过确定性来源授权，而不是相信模型选择的 URL：仅允许已采集官方 Repository 的 GitHub Release 下载资产，或在已采集 README 中按文件与行号定位到的精确外链。执行器强制将官方 Release 放在前面；其公开可用时 README 外链会记录为 `skipped`，仅在官方 Release 未验证公开可用时才降级探测 README 外链。任意模型临时编造的 Drive/外链会在连接器之前被拒绝。

### P1-4 Tool Loop 停止与替代输入（已完成，2026-09-17）

研究上限已扩至五轮。Loop 现在明确区分：确认请求、环境只读未授权、工具获取失败、无可靠下一来源、重复 Gap、无新增材料和预算停止；每次停止都生成独立 `ResearchLoopHandoff`，不生成或篡改业务 Status / Gate。仅当环境只读获取未授权或失败时，handoff 才提供 Snapshot / Manual Input；获取失败还会显式允许 Retry。`ContextGapSnapshot` 同步记录 acquisition state 与可用替代输入，但保持为流程审计工件。

### P1-5 可观测性与失败诊断（已完成，2026-09-17）

模型 Provider 不可用、模型结构化输出无效、确定性工具失败和材料部分获取失败现在保留为独立 API/前端流程状态。审计 Trace 保留 Provider request ID（如请求已发出）、耗时、研究轮次、相关 source ID、工具结果和停止原因；不保留 Prompt、原始模型响应、材料正文或凭据。工具获取失败但已有材料仍可继续分析时，Assessment 标记为 `partial_result`，而不是改写业务 Dimension 或 Gate。现有 Acquisition Failure、Gate unavailable 和 Partial Result 页面就地显示安全 Trace 摘要。

### P1-6 Unknown 的用户可见解释（已完成，2026-09-17）

Overview 和 Dimension 页面展示具体主 Finding：缺少何种事实、影响哪个 Condition、现有证据是什么、最低成本验证动作是什么；不以通用规则兜底文案替代业务解释。裁决层现在以具体 criterion 生成 Dimension Gate Impact，并为无 Fact 覆盖的条件说明当前材料集合缺什么、应查找哪类权威来源以及必须提供精确位置；前端将无可检查证据明确显示为“未在已收集材料中定位”，而非误称“证据不可用”。

## P2：在核心闭环验收后再做的增强

1. 多候选 Target 的真实材料解释与确认体验（已完成，2026-09-17）：按 Target Resolution API 返回的实际候选动态渲染，展示公开元数据依据、稳定 DOI/arXiv 身份和链接，并明确确认前尚未读取仓库、论文或项目材料。
2. 跨项目、非英文项目、无权重项目、需权限权重、恶意 Prompt Injection 项目的验收集（已完成，2026-09-17）：Stage 12 的受控验收矩阵覆盖九类材料范围，并把 Provider、网络与材料采集故障保持为技术结果；不伪造成业务 Gate 或 Dimension。
3. Evidence / Finding revision 的历史对比和差异视图（已完成，2026-09-17）：Assessment 现在保留初始及每次反馈后的不可变领域快照；`/revisions` 返回相邻版本的 Gate、Dimension、Finding 和 Evidence 差异。Overview 仅在用户请求时展开内嵌历史，且不暴露原始材料、Prompt 或凭据。
4. 新的受控连接器或第三方材料来源（已完成，2026-09-18）：新增 Hugging Face 公共模型卡／数据集卡连接器。它只接受已在当前 Target 或已收集材料中出现的规范 `huggingface.co` 卡片 URL，通过固定 Hub API 读取有界公开元数据；拒绝下载、resolve 链接、查询参数和凭据 URL。返回结果作为不可信、可定位 Material 进入 AI→Rule 主链，卡片存在或列出文件不等于权重已下载、可公开访问或可用于复现。

## 执行顺序

1. P0-1 真实模型结构化输出可靠性。
2. P0-2 Evidence Drawer 与 Evidence 身份连续性。
3. P0-3 清理静态 Demo 与 FGI 专用生产回退。
4. P0-4 反馈驱动的完整重判闭环。
5. P0-5 Prompt Case 运行时回归。
6. 按 P1-1 至 P1-5 顺序推进。
7. 完成 P0/P1 后再评估 P2。

## 开发纪律

- 每次只实现一个编号项，并完成该项的针对性测试后再进入下一项。
- 不修改设计文档；若实现发现设计冲突，只报告并等待产品决策。
- 不自行新增产品页面、状态、核心 Dimension、Gate 值或权限。
- 每个变更必须保持 AI → Rule → Human 的职责边界，并保留可审计证据链。
