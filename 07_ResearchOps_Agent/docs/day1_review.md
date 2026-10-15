# ResearchOps Agent Day 1 复盘

## 今日目标

完成。

已建立以下最小端到端闭环：

```text
用户输入论文复现需求
→ Streamlit
→ FastAPI 创建 task_id
→ LangGraph 生成并校验 reproduction_plan
→ Streamlit 展示结构化结果
```

---

## 真实运行证据

### 自动化测试

执行命令：

```powershell
python -m pytest
```

真实运行结果：

```text
24 passed
```

### 代码质量

执行命令：

```powershell
ruff check .
ruff format --check .
```

真实运行结果：

```text
All checks passed!
39 files already formatted
```

### FastAPI

已完成以下接口的真实调用：

```text
GET /health
→ HTTP 200

POST /api/v1/tasks/plan
→ HTTP 201
```

正常规划接口可以返回：

- 合法 UUID 格式的 `task_id`；
- `planned` 任务状态；
- 结构化 `reproduction_plan`；
- 6 个复现步骤；
- 4 条工作流 Trace；
- 需要人工审批的执行步骤。

### Streamlit

Streamlit 已通过 HTTP 成功调用 FastAPI，并展示：

- 任务编号；
- 任务状态；
- 计划步骤数量；
- 复现目标；
- 前置条件；
- 规划假设；
- 6 个执行步骤；
- 已识别风险；
- 最终产物；
- 人工审批提醒；
- 工作流 Trace。

### 演示截图

Swagger 成功响应截图：

```text
docs/screenshots/day1_swagger_plan_success.jpeg
```

Streamlit 成功页面截图：

```text
docs/screenshots/day1_streamlit_plan_success.png
```

---

## 最重要的架构决策

Day 1 采用最小竖切，而不是同时接入数据库、大模型、Docker 和 GPU。

具体决策如下：

1. 使用 `RuleBasedPlanner` 保证项目可以离线运行。
2. 使用 Pydantic 定义稳定的领域模型与工作流状态。
3. 使用四个职责明确的 LangGraph 节点表达规划流程。
4. Streamlit 必须通过 HTTP 调用 FastAPI。
5. FastAPI 路由不直接承载 LangGraph 业务逻辑。
6. 所有具有外部副作用的步骤必须经过人工审批。
7. 使用结构化 Trace 和 JSON 日志保留运行证据。
8. 使用 pytest 和 Ruff 建立基础质量门禁。

详细架构决策记录：

```text
docs/decisions/ADR-001-day1-minimal-vertical-slice.md
```

---

## LangGraph 工作流

当前工作流包含四个节点：

```text
START
  ↓
normalize_request
  ↓
generate_plan
  ↓
validate_plan
  ↓
finalize
  ↓
END
```

各节点职责：

### normalize_request

负责：

- 清理用户请求中的多余空格；
- 压缩换行和制表符；
- 处理中文标点附近的不自然空格；
- 将空请求转换为结构化错误；
- 记录 Trace。

### generate_plan

负责：

- 调用 `PlannerService`；
- 使用 `RuleBasedPlanner` 生成结构化复现计划；
- 处理可预期规划错误；
- 将未知异常记录到服务端日志；
- 记录 Trace。

### validate_plan

负责：

- 检查计划是否包含步骤；
- 检查步骤编号是否连续；
- 检查人工审批步骤；
- 检查 shell 等副作用工具是否需要审批；
- 检查执行步骤前是否存在人工审批步骤；
- 将校验问题写入 `errors`；
- 记录 Trace。

### finalize

负责：

- 汇总工作流状态；
- 根据错误和计划内容确定成功或失败；
- 成功时设置 `status="planned"`；
- 失败时设置 `status="failed"`；
- 记录最终 Trace。

---

## 人工审批边界

当前系统将以下类型的工具视为具有外部副作用：

```text
shell
docker
gpu
file_writer
database_writer
download
```

这些步骤必须设置：

```python
approval_required = True
```

对于 shell 等执行步骤，还要求在它之前存在明确的人工审批步骤。

当前六步计划中的：

```text
步骤 5：人工审批执行方案
步骤 6：执行推理并生成结果报告
```

都需要人工审批。

Day 1 系统只生成计划，不会实际执行步骤 6。

---

## 遇到的最大阻塞

### Streamlit 调用 FastAPI 返回 HTTP 502

Streamlit 首次调用本地 FastAPI 时曾返回：

```text
HTTP 502
```

经过排查确认：

- FastAPI 服务本身正常；
- `/health` 可以正常返回 HTTP 200；
- LangGraph 可以正常运行；
- 502 来自系统代理对本地 HTTP 请求的截获；
- 请求没有正常到达 FastAPI。

通过以下命令验证：

```powershell
python -c "import httpx; r=httpx.get('http://127.0.0.1:8000/health', trust_env=False); print(r.status_code, r.text)"
```

结果：

```text
200 {"service":"ResearchOps Agent","status":"ok","version":"0.1.0"}
```

最终解决方案是在 `PlanningApiClient` 中设置：

```python
trust_env = False
```

并完全停止、重新启动 Streamlit，使新代码被重新加载。

该设置避免 HTTPX 读取系统中的代理环境变量，确保对：

```text
http://127.0.0.1:8000
```

的请求直接发送到本地 FastAPI。

---

## 其他开发问题

### Ruff 首次格式检查发生 panic

第一次执行：

```powershell
ruff format --check .
```

时，Ruff 在展示格式差异的过程中发生自身 panic。

当时：

- pytest 仍然全部通过；
- Python 业务代码可以正常运行；
- Ruff 已经识别出需要调整的 import 和格式问题。

采用以下方式处理：

```powershell
ruff check . --fix
ruff format .
```

随后重新执行：

```powershell
ruff check .
ruff format --check .
python -m pytest
```

最终结果：

```text
All checks passed!
39 files already formatted
24 passed
```

---

## 采用的降级与 Mock 策略

为了保证第一天完成可运行闭环，采用了以下策略。

### 1. 使用 RuleBasedPlanner

当前不调用真实大模型 API。

原因：

- 不依赖 API Key；
- 不依赖网络；
- 输出结构稳定；
- 测试结果可重复；
- 可以先验证工程架构。

后续可通过实现 `LLMPlanner` 替换，而不修改 LangGraph 节点接口。

### 2. 不解析真实论文和仓库

当前不读取：

- 真实论文 PDF；
- README；
- GitHub 仓库源码；
- 配置文件；
- checkpoint 说明。

Day 1 只预留相应的工具和服务边界。

### 3. 不接入真实数据和模型

当前不处理：

- DFDC 数据集；
- 数据预处理；
- checkpoint 下载；
- checkpoint 加载；
- CUDA；
- GPU；
- 真实 FGI 推理。

### 4. 不执行外部命令

当前只生成候选命令和执行步骤，不实际调用：

- shell；
- Docker；
- GPU Worker；
- 文件下载；
- 文件写入；
- 数据库写入。

### 5. 不接入持久化基础设施

当前不接入：

- MySQL；
- Redis；
- Celery；
- RQ；
- 其他异步任务队列。

任务状态仅存在于当前 LangGraph 工作流和 Streamlit 会话中。

---

## 当前测试覆盖

Day 1 共完成 24 个自动化测试，覆盖以下内容。

### Python 包与基础设施

- `researchops` 包可以正常导入；
- 项目版本号可以正确读取；
- Settings 可以读取环境变量；
- 环境变量可以覆盖默认配置；
- JSON 日志包含必要字段。

### Pydantic 模型

- `TaskRequest` 必须包含有效的 `user_request`；
- 空白请求会触发校验错误；
- `ReproductionPlan` 可以序列化；
- `AgentState` 可以保存计划；
- `TaskResponse` 可以稳定转换成 JSON。

### RuleBasedPlanner

- 可以生成六步计划；
- 步骤编号连续；
- 关键阶段齐全；
- 人工审批步骤设置正确；
- shell 步骤设置正确；
- 空请求会触发明确异常。

### LangGraph 节点

- 请求空白可以正常规范化；
- 中文标点附近空格可以正确处理；
- 空请求会转换为结构化错误；
- 四个节点可以顺序执行；
- 未审批 shell 步骤会被校验节点拒绝。

### 完整 LangGraph

- FGI 示例可以生成有效计划；
- 最终状态为 `planned`；
- 最终阶段为 `completed`；
- 四条 Trace 顺序正确；
- 空请求能够完整经过工作流并返回失败状态；
- 副作用步骤必须人工审批。

### FastAPI

- `/health` 返回 HTTP 200；
- 计划接口返回 HTTP 201；
- 返回合法 `task_id`；
- 返回六个计划步骤；
- shell 步骤要求审批；
- 空请求返回统一错误响应；
- 未声明字段会被拒绝。

### Streamlit HTTP 客户端

- 可以解析 FastAPI 成功响应；
- 空输入在本地被拒绝；
- 可以处理 FastAPI 结构化错误；
- FastAPI 不可用时返回可读连接错误。

所有自动化测试均不依赖：

- 互联网；
- MySQL；
- Redis；
- Docker；
- GPU；
- 真实模型文件；
- 真实数据集。

---

## 当前已完成内容

- [x] Git 仓库初始化。
- [x] Python 虚拟环境创建。
- [x] `pyproject.toml` 配置。
- [x] `.env.example` 配置模板。
- [x] `.gitignore`。
- [x] Pydantic 领域模型。
- [x] AgentState 与 TraceEvent。
- [x] PlannerService 抽象接口。
- [x] RuleBasedPlanner。
- [x] 四个 LangGraph 节点。
- [x] LangGraph 构建和编译。
- [x] 结构化日志。
- [x] FastAPI 健康检查接口。
- [x] FastAPI 计划生成接口。
- [x] 统一错误响应。
- [x] Streamlit HTTP 客户端。
- [x] Streamlit 页面。
- [x] 人工审批边界。
- [x] 自动化测试。
- [x] Ruff 静态检查。
- [x] Ruff 格式检查。
- [x] Swagger 成功截图。
- [x] Streamlit 成功截图。
- [x] ADR 架构决策记录。
- [x] blockers 和技术债记录。
- [x] README 运行说明。

---

## 遗留技术债

1. `RuleBasedPlanner` 的计划内容仍以固定规则模板为主。
2. 尚未接入真实 LLM。
3. 尚未解析真实论文 PDF。
4. 尚未解析 README 和 GitHub 仓库。
5. 尚未提取仓库依赖、命令和数据路径。
6. 任务数据尚未持久化。
7. 尚未实现人工审批后的工作流中断和恢复。
8. 尚未实现异步任务队列。
9. 尚未实现受控 Docker Runner。
10. 尚未实现 GPU Worker。
11. 尚未真正执行 FGI 推理。
12. 尚未进行 DFDC 数据检查和预处理。
13. 尚未完全锁定全部依赖版本。
14. 尚未配置持续集成流水线。
15. 尚未实现 Agent 效果评估面板。

这些问题不阻塞 Day 1 最小闭环验收。

---

## 明天第一项任务

设计并实现真实资产解析接口：

```text
论文、README 或仓库输入
→ 资产解析
→ 结构化 RepositoryProfile
→ 提供给 PlannerService
```

建议优先实现：

1. 定义 `RepositoryProfile` 数据模型；
2. 定义 `RepositoryInspector` 抽象接口；
3. 解析仓库 README；
4. 提取安装命令；
5. 提取推理命令；
6. 提取数据集与 checkpoint 要求；
7. 将真实解析结果传给 PlannerService；
8. 使用 Mock 仓库内容完成离线测试。

Day 2 暂时仍不直接执行真实 FGI 推理，先增强输入信息的真实性。

---

## Day 1 最终验收

### 工程骨架

- [x] `python -c "import researchops"` 成功。
- [x] Python 包可以编辑安装。
- [x] 目录和模块职责清晰。

### LangGraph

- [x] 包含四个明确节点。
- [x] 四个节点已经通过真实图边连接。
- [x] 工作流可以完成编译和调用。
- [x] 可以保存基础 Trace。
- [x] 可以生成结构化计划。
- [x] 可以返回结构化失败状态。

### FastAPI

- [x] `GET /health` 返回 200。
- [x] `POST /api/v1/tasks/plan` 返回 201。
- [x] 接口创建合法 UUID。
- [x] 接口返回结构化 TaskResponse。
- [x] 请求错误返回统一 ErrorResponse。
- [x] Swagger 可以直接调用接口。

### Streamlit

- [x] 页面可以输入论文复现需求。
- [x] 页面通过 HTTP 调用 FastAPI。
- [x] 页面不直接调用 LangGraph。
- [x] 页面展示任务编号。
- [x] 页面展示目标和前置条件。
- [x] 页面展示六个步骤。
- [x] 页面展示风险和最终产物。
- [x] 页面展示人工审批提醒。
- [x] 页面展示工作流 Trace。
- [x] 后端不可用时显示可读错误。

### 安全边界

- [x] shell 步骤要求人工审批。
- [x] 执行步骤前存在人工审批步骤。
- [x] 不直接执行外部命令。
- [x] 不在日志中记录密钥。
- [x] `.env` 不提交到 Git。
- [x] API 不直接返回 Python 堆栈。

### 测试与质量

- [x] pytest 共 24 个测试通过。
- [x] Ruff 静态检查通过。
- [x] Ruff 格式检查通过。
- [x] 测试不依赖网络、数据库或真实模型。
- [x] Git 中没有提交虚拟环境和缓存。

### 文档与证据

- [x] README 已完善。
- [x] `docs/day1_scope.md` 已完成。
- [x] `docs/day1_board.md` 已完成。
- [x] `docs/code_style.md` 已完成。
- [x] ADR 已完成。
- [x] blockers 已记录。
- [x] Swagger 截图已保存。
- [x] Streamlit 截图已保存。

---

## Day 1 结论

Day 1 已经证明系统架构可以继续生长：

- 用户请求具有明确入口；
- API 可以创建唯一任务；
- LangGraph 具有清晰节点和状态流转；
- 输出使用稳定的领域模型；
- 执行操作具有人工审批边界；
- 运行过程具有 Trace 和结构化日志；
- 核心流程具有自动化测试；
- 页面、API 和工作流已经真正串通；
- 后续实现可以沿当前接口逐步替换和扩展。

当前系统不是“大而全但无法运行”的 Demo，而是一条经过测试、可以演示、可以解释、可以继续扩展的真实工程主干。