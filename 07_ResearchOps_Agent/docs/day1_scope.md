# Day 1 Scope

## Goal

完成一个可运行、可测试、可演示的最小端到端竖切：

用户输入需求
→ FastAPI 创建 task_id
→ LangGraph 生成结构化 reproduction_plan
→ Streamlit 展示结果

---

## In Scope

Day 1 包含以下内容：

1. 创建清晰的 Python 工程目录。
2. 定义 Pydantic 领域模型：
   - TaskRequest
   - PlanStep
   - ReproductionPlan
   - AgentState
   - TaskResponse
3. 实现四个 LangGraph 节点：
   - normalize_request
   - generate_plan
   - validate_plan
   - finalize
4. 实现 RuleBasedPlanner。
5. 实现两个 FastAPI 接口：
   - GET /health
   - POST /api/v1/tasks/plan
6. 实现一个 Streamlit 页面。
7. Streamlit 必须通过 HTTP 调用 FastAPI。
8. 实现结构化 Trace。
9. 所有执行命令类步骤必须设置：
   approval_required = true
10. 至少完成 5 个 pytest 自动化测试。
11. 编写安装、启动和测试说明。
12. 保存 Swagger 和 Streamlit 的运行截图。

---

## Out of Scope

Day 1 不实现以下功能：

1. MySQL 持久化。
2. Redis。
3. Celery 或 RQ。
4. Docker Runner。
5. GPU Worker。
6. 真实 FGI 推理。
7. 真实 CUDA 环境配置。
8. 真实 DFDC 数据集处理。
9. checkpoint 下载与加载。
10. 真实论文 PDF 解析。
11. 真实 GitHub 仓库解析。
12. 真实大模型 API。
13. 多 Agent 协作。
14. 登录和权限系统。
15. 复杂前端页面。
16. AgentEval Dashboard。

---

## Definition of Done

只有同时满足以下条件，Day 1 才算完成：

- [ ] `python -c "import researchops"` 执行成功。
- [ ] `GET /health` 返回 HTTP 200。
- [ ] `POST /api/v1/tasks/plan` 返回 task_id。
- [ ] API 返回结构化 reproduction_plan。
- [ ] LangGraph 包含四个明确节点。
- [ ] LangGraph 能保存基础 Trace。
- [ ] FGI 示例能够生成非空计划。
- [ ] 所有执行类步骤都需要人工审批。
- [ ] Streamlit 通过 HTTP 调用 FastAPI。
- [ ] 页面展示目标、步骤、风险和审批提示。
- [ ] 至少 5 个 pytest 测试真实通过。
- [ ] README 中的命令已经在当前电脑验证。
- [ ] 没有提交 .env、API Key 或个人数据路径。
- [ ] 保存 Swagger 成功响应截图。
- [ ] 保存 Streamlit 成功展示截图。
- [ ] 完成一次 Git commit。
- [ ] 所有遗留问题写入 blockers.md。

---

## Known Risks

### 1. Python 依赖版本冲突

处理策略：

- 使用独立虚拟环境。
- 固定核心依赖版本。
- 遇到冲突时优先保证最小闭环。

### 2. LangGraph API 版本变化

处理策略：

- 第一版只使用最基础的 StateGraph。
- 不使用复杂持久化和中断恢复功能。

### 3. Windows 路径和命令差异

处理策略：

- README 同时记录 PowerShell 和通用启动命令。
- 业务代码中使用 pathlib。

### 4. FastAPI 与 Streamlit 端口冲突

处理策略：

- FastAPI 使用 8000 端口。
- Streamlit 使用 8501 端口。

### 5. 外部网络或 API 不可用

处理策略：

- Day 1 使用 RuleBasedPlanner。
- 自动化测试不得依赖网络。

### 6. 单个问题占用时间过长

处理策略：

- 同一个问题超过 30 分钟仍未解决时，
  降级为 Mock 或占位实现。
- 将问题记录到 blockers.md。