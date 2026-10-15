# ADR-001：Day 1 采用最小竖切架构

## 状态

已接受

## 日期

2026-07-31

## 背景

ResearchOps Agent 的长期目标是支持论文、代码仓库、数据集、
checkpoint 和运行环境的分析，并进一步完成需要人工审批的复现任务执行。

完整系统未来可能包含：

- 论文 PDF 与 README 解析；
- GitHub 仓库分析；
- LLMPlanner；
- MySQL 持久化；
- Redis 与异步任务队列；
- Docker 或 GPU Runner；
- 人工审批与执行恢复；
- 评估和观测面板。

如果在第一天同时实现以上能力，项目很容易被数据库、网络、密钥、
CUDA、模型文件或第三方仓库环境阻塞，无法形成真正可运行的端到端流程。

## 决策

Day 1 只实现一条最小竖切：

用户输入论文复现需求
→ Streamlit 通过 HTTP 调用 FastAPI
→ FastAPI 创建 task_id
→ LangGraph 生成并校验结构化 reproduction_plan
→ 页面展示计划和人工审批边界

具体决策如下：

1. 使用 RuleBasedPlanner，不调用真实大模型 API。
2. 使用内存中的 AgentState，不接入 MySQL。
3. 不接入 Redis、任务队列、Docker、GPU 或真实 shell 执行。
4. Streamlit 只能通过 HTTP 调用 FastAPI，不能直接调用 LangGraph。
5. LangGraph 使用四个职责明确的节点：
   - normalize_request
   - generate_plan
   - validate_plan
   - finalize
6. 所有具有外部副作用的执行步骤必须标记人工审批。
7. 使用 Pydantic 定义请求、计划、状态和响应。
8. 使用 pytest、Ruff 和结构化日志建立基础质量门禁。

## 原因

该设计优先证明以下能力：

- 工程目录和模块边界正确；
- 用户输入能够贯穿页面、API、工作流和领域模型；
- 工作流状态可追踪；
- 输出结构可以稳定序列化；
- 人工审批边界可以被自动校验；
- 核心功能可以离线测试；
- 后续能力可以沿现有接口逐步替换。

RuleBasedPlanner 与内存状态不是最终实现，而是符合稳定接口的
Day 1 替代实现。

## 后果

### 正面影响

- 项目不依赖网络、API Key、数据库或 GPU 即可运行。
- 自动化测试稳定且可重复。
- FastAPI、Streamlit 和 LangGraph 的边界清晰。
- 后续接入 LLMPlanner 时不需要修改工作流节点接口。
- 后续接入数据库时不需要重写页面和规划逻辑。
- 可以向面试官展示真实运行和测试证据。

### 负面影响

- 当前计划内容由固定规则生成，智能程度有限。
- 当前任务状态不会持久化。
- 页面刷新后只能保留当前 Streamlit 会话中的结果。
- 系统尚不能读取真实论文、仓库、数据集或 checkpoint。
- 系统不会实际执行任何复现命令。

## 后续演进

计划按照以下顺序逐步扩展：

1. 增加论文、README 和仓库解析接口。
2. 使用 LLMPlanner 替换 RuleBasedPlanner。
3. 增加 TaskRepository，并接入 MySQL。
4. 增加人工审批状态和工作流中断恢复。
5. 接入异步任务队列。
6. 接入受控的 Docker 或 GPU Runner。
7. 增加运行指标、日志检索和评估面板。

## 验证结果

Day 1 已验证：

- researchops 包可正常导入；
- LangGraph 四节点闭环可运行；
- GET /health 返回 200；
- POST /api/v1/tasks/plan 返回 201；
- Streamlit 可以通过 HTTP 调用 FastAPI；
- FGI 示例生成 6 个结构化步骤；
- shell 执行步骤要求人工审批；
- pytest 共 24 个测试通过；
- Ruff 静态检查与格式检查通过。