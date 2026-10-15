# ResearchOps Agent

ResearchOps 是 AI 论文复现决策助手：先收集和核验证据，再判断是否值得投入复现工作。

[在线演示](https://researchops-agent.com/mvp/)需要邀请码；本地开发可以使用显式的 local 模式。

## 当前工作流

目标解析与确认 → 有界材料采集 → Context & Gap → Tool Acquisition（需要时）→ 每个条件的局部 Evidence/Finding Draft → 确定性 Rule → Readiness 结果 → 人工反馈与最终决定。

AI 提出结构化候选；Rule 决定证据受理、维度状态与 Gate；Human 确认目标、补充事实和记录投资决定。缺少证据保留为 Unknown，模型或网络故障单独作为技术状态呈现。

## 功能

- 输入 GitHub 仓库、项目页、DOI、arXiv 或论文标题。
- 分析 Data & Access、Environment & Dependency、Weights & Configuration 三个维度。
- 展示可定位证据、冲突双方、资源和评测信号及 First Next Action。
- 支持后台任务进度、反馈重评、修订历史和独立的最终决定记录。
- 公网支持免注册邀请码、HttpOnly 会话、CSRF、资源归属、限流、持久化额度和模型请求预算。

## 安装

需要 Python 3.11+。从整个仓库克隆，保留相邻的 `06_Product_Versions` 产品基线资料：

```bash
git clone https://github.com/vtrbrydbety/research-ops.git
cd research-ops/07_ResearchOps_Agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
RESEARCHOPS_DEPLOYMENT_MODE=local
API_HOST=127.0.0.1
RESEARCHOPS_LLM_API_KEY=填写你自己的模型密钥
```

密钥留空可以运行健康检查、离线回归与规则计划接口；完整 Readiness 评估需要真实模型及网络，不会在模型不可用时伪造分析结果。公网应使用 `public` 模式；local 模式仅用于回环开发。

## 运行

```bash
python -m researchops.serve
```

- MVP： http://127.0.0.1:8000/mvp/
- 健康检查： http://127.0.0.1:8000/health
- 本地开发 API 文档： http://127.0.0.1:8000/docs

可选的早期 Streamlit 计划页面，在另一个终端执行：

```bash
python -m streamlit run apps/web/app.py --server.address 127.0.0.1 --server.port 8501
```

## 测试

```bash
python -m pytest
python -m ruff check .
python -m playwright install chromium
python tools/check_public_browser.py
```

2026-10-16：离线 pytest 为 **403 passed、2 skipped**，Ruff 和 Chromium 完整流程通过。普通回归使用临时状态并默认屏蔽付费模型密钥；浏览器检查使用可控材料和模型 HTTP 响应，执行真实的认证、调度、图与 Rule。

真实模型检查需单独明确启用：

```bash
python tools/check_live_model.py --run-live
```

该命令会发送合成材料并产生真实提供商调用，最多 2 次 HTTP 尝试；它不是离线测试，也不代替公网完整评估验收。

## 工程结构

| 路径 | 职责 |
|---|---|
| `apps/api/` | FastAPI 业务入口 |
| `apps/mvp/` | 主 MVP 页面与接线 |
| `researchops/graphs/` | LangGraph 编排 |
| `researchops/services/` | 模型、采集、规则、审核与调度 |
| `researchops/core/` | 配置、可信上下文和公网防护 |
| `researchops/schemas/` | 强类型契约 |
| `tests/` | 离线回归与显式真实模型测试 |
| `deploy/macos/` | macOS 系统服务及隧道模板 |
| `openspec/` | 设计规范与变更记录 |

技术栈：Python、FastAPI、LangGraph、Pydantic、HTTPX/HTTPCore、SQLite、HTML/CSS/JavaScript；Streamlit 用于早期计划界面。

## 公网部署与边界

部署见 [公网部署说明](docs/secure-public-deployment.md)。macOS 模板含原部署机器的绝对路径、用户名和隧道 ID；用于其他机器时需按自己的用户、路径和 Tunnel 调整。应用始终使用回环监听和单 worker。

每个邀请码对应独立的数据与额度。系统不执行外部仓库代码、模型训练或复现命令；公网不采集服务器环境，使用 manual、snapshot 或 later 输入。真实评估会向模型提供商发送必要材料，请勿提交不希望交给该提供商的敏感内容。

[实施与验收记录](docs/secure-public-implementation-status.md)保留实际已验证范围和未验证的主机条件；源码发布不代表其他机器已完成部署。

本仓库原创代码采用 [MIT License](../LICENSE)，第三方研究资料保留各自权利。开发过程的早期记录位于 `docs/`，其中的阶段性状态以本 README 和当前实现为准。
