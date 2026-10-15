# ResearchOps Agent 代码风格约定

## 1. 命名规范

类名、函数名、变量名和文件名使用英文，并遵循 Python 社区常用命名规范：

- 类名使用 PascalCase，例如 `ReproductionPlan`
- 函数和变量使用 snake_case，例如 `get_settings`
- 常量使用 UPPER_SNAKE_CASE，例如 `DEFAULT_TIMEOUT`
- Python 文件名使用 snake_case，例如 `task_repository.py`

第三方框架规定的名称，例如 FastAPI 路由参数、LangGraph 节点名和 Pydantic 字段名，不随意修改。

---

## 2. 中文注释规范

本项目统一采用：

> 英文标识符 + 必要的中文注释

以下位置应当添加中文说明：

1. Python 模块顶部的模块说明。
2. 对外使用的类和函数。
3. 复杂的判断、状态流转和异常处理。
4. 不容易直接理解的架构设计。
5. 人工审批、安全边界和降级策略。
6. 自动化测试的测试目的。

示例：

```python
def get_settings() -> Settings:
    """返回经过缓存的应用配置对象。"""
    return Settings()
```

---

## 3. 注释内容原则

注释优先解释以下内容：

- 为什么这样设计；
- 该代码承担什么职责；
- 输入和输出分别是什么；
- 有什么限制或安全边界；
- 为什么选择当前实现，而不是其他实现；
- 异常发生后系统如何处理。

避免添加没有实际价值的注释。

不推荐：

```python
# 将 count 加一
count += 1
```

推荐：

```python
# 使用一基制编号，便于在页面和复现报告中直接展示步骤顺序。
step_id = index + 1
```

注释应当帮助理解设计，而不是简单翻译代码。

---

## 4. Docstring 规范

Python 模块、类和函数使用中文 docstring。

模块示例：

```python
"""论文复现任务的领域模型。

该模块定义 API 请求、复现步骤、完整计划和任务响应的数据结构。
"""
```

类示例：

```python
class ReproductionPlan(BaseModel):
    """一个完整、结构化的论文复现计划。"""
```

函数示例：

```python
def normalize_request(user_request: str) -> str:
    """清理用户请求中的多余空白并返回标准化结果。"""
```

较复杂的函数可以说明参数、返回值和异常：

```python
def create_task(user_request: str) -> TaskResponse:
    """创建论文复现规划任务。

    Args:
        user_request: 用户提交的自然语言复现需求。

    Returns:
        包含 task_id、任务状态和复现计划的响应对象。

    Raises:
        ValueError: 当用户请求为空或不符合要求时抛出。
    """
```

FastAPI、LangGraph、Pydantic、Streamlit、Trace、API 等专业名称保留英文，不强制翻译。

---

## 5. 行内注释规范

只有当代码意图不能直接从代码本身看出时，才添加行内注释。

推荐：

```python
# 执行 shell 命令会改变外部环境，因此必须先经过人工审批。
if step.tool == "shell":
    step.approval_required = True
```

不推荐：

```python
# 判断 tool 是否等于 shell
if step.tool == "shell":
    step.approval_required = True
```

行内注释应放在相关代码上方，尽量避免在代码行末尾添加很长的注释。

---

## 6. 类型标注规范

对外函数、业务函数和重要变量应尽量添加明确的类型标注。

推荐：

```python
def build_plan(user_request: str) -> ReproductionPlan:
    """根据用户需求生成结构化复现计划。"""
```

避免在核心业务模型中使用模糊类型：

```python
dict[str, Any]
```

当数据结构固定时，应优先使用：

- Pydantic 模型
- dataclass
- TypedDict
- Literal
- Enum
- 明确的列表或字典类型

例如：

```python
steps: list[PlanStep]
status: Literal["created", "planning", "planned", "failed"]
```

---

## 7. 异常处理规范

异常处理应满足以下原则：

1. 不静默吞掉异常。
2. 日志中保留开发人员排查所需的信息。
3. API 返回安全、可读的错误摘要。
4. 不直接向用户返回完整 Python 堆栈。
5. 错误响应应尽量保留 `task_id`。
6. 能使用明确异常类型时，不随意捕获所有异常。

推荐：

```python
try:
    plan = planner.generate_plan(normalized_request)
except PlanningError as exc:
    logger.exception("生成复现计划失败")
    errors.append(str(exc))
```

谨慎使用：

```python
except Exception:
    pass
```

如果必须捕获未知异常，应记录日志并转换为安全响应。

---

## 8. 日志规范

项目日志至少包含：

- `timestamp`
- `level`
- `task_id`
- `component`
- `message`

示例：

```python
logger = get_logger(
    component="planning",
    task_id=str(task_id),
)

logger.info("复现计划生成完成")
```

禁止在日志中记录：

- API Key
- 密码
- Access Token
- 用户隐私信息
- 完整数据集本地路径
- 不必要的原始请求内容

---

## 9. LangGraph 节点规范

每个 LangGraph 节点应当：

1. 只承担一个明确职责。
2. 接收共享状态。
3. 返回状态的局部更新。
4. 不直接操作 Streamlit 页面。
5. 不直接处理 FastAPI Request 对象。
6. 不直接连接数据库。
7. 不直接执行 shell 命令。
8. 记录必要的 Trace 信息。
9. 对错误进行结构化处理。

示例：

```python
def normalize_request_node(state: AgentState) -> dict:
    """清理用户输入并生成标准化请求。"""

    normalized_request = " ".join(state.user_request.split())

    return {
        "normalized_request": normalized_request,
        "current_stage": "normalize_request",
    }
```

节点中应避免混入与当前职责无关的代码。

---

## 10. 人工审批规范

任何可能改变外部环境的操作都必须明确标记人工审批。

通常需要审批的操作包括：

- 执行 shell 命令；
- 下载大文件；
- 修改文件；
- 删除文件；
- 启动模型推理；
- 使用 GPU；
- 写入数据库；
- 调用具有副作用的外部工具。

示例：

```python
PlanStep(
    step_id=6,
    title="执行预训练模型推理",
    description="执行经过确认的 FGI 推理命令。",
    tool="shell",
    approval_required=True,
    expected_output="推理日志和评估结果。",
)
```

不能仅依赖步骤标题判断风险，应同时参考 `tool` 和步骤行为。

---

## 11. 测试规范

每个测试函数应说明：

- 测试什么场景；
- 预期结果是什么；
- 该测试防止什么问题。

测试函数名称继续使用英文，便于 pytest 输出和工程检索。

示例：

```python
def test_task_request_requires_user_request() -> None:
    """验证缺少或只包含空白字符的请求会触发校验错误。"""
```

测试应尽量满足：

1. 不依赖网络。
2. 不依赖 MySQL、Redis 或 Docker。
3. 不依赖真实模型文件。
4. 每个测试可以独立运行。
5. 测试结果稳定、可重复。
6. 同时覆盖正常路径和错误路径。

---

## 12. 文件职责规范

业务逻辑统一放在 `researchops` 包中。

目录职责如下：

```text
apps/api/                 FastAPI 应用入口
apps/web/                 Streamlit 应用入口
researchops/graphs/       LangGraph 构建与编译
researchops/nodes/        工作流节点
researchops/states/       共享状态模型
researchops/schemas/      请求、响应和领域模型
researchops/services/     可替换的业务服务
researchops/repositories/ 数据持久化接口
researchops/core/         配置、日志等基础设施
tests/                    自动化测试
```

禁止将大量业务逻辑直接写入：

- `apps/api/main.py`
- `apps/web/app.py`

FastAPI 和 Streamlit 文件主要负责接入层逻辑。

---

## 13. 代码修改原则

每次修改代码后应当：

1. 运行相关测试。
2. 运行完整测试。
3. 检查 `git diff`。
4. 确认没有提交 `.env`、密钥、缓存或大文件。
5. 使用清晰的 Git commit 信息。
6. 将未解决问题记录到 `blockers.md`。

功能修改、代码重构和文档修改尽量分开提交。

例如：

```text
feat: implement rule-based reproduction planner
test: add graph approval validation tests
refactor: simplify workflow state updates
docs: document LangGraph node responsibilities
```

---

## 14. 核心原则

代码首先应当做到：

- 可以运行；
- 可以测试；
- 可以理解；
- 可以替换；
- 可以追踪；
- 可以安全失败。

中文注释用于帮助理解代码设计，但不能替代清晰的代码结构和命名。