# ResearchOps

面向人工智能研究者的论文复现决策助手：在投入训练、环境配置和数据获取之前，检查复现所需的证据、缺口与风险。

本仓库记录从用户研究、公开案例、产品设计到可运行应用的完整过程。

**在线演示：** https://researchops-agent.com/mvp/ （仅限受邀人员，需邀请码）。

## 从哪里开始

- **运行应用：** [07_ResearchOps_Agent/README.md](07_ResearchOps_Agent/README.md)
- **产品与交互：** [06_Product_Versions](06_Product_Versions/)
- **分析与决策：** [05_Analysis_and_Decisions](05_Analysis_and_Decisions/)
- **完整资料索引：** [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## 核心能力

- 支持 GitHub 仓库、项目页、DOI、arXiv 与论文标题入口，必要时由用户确认目标。
- 通过 Context & Gap、Tool Acquisition 和局部 Evidence/Finding Draft 组织模型分析。
- 确定性规则校验证据来源、引用与冲突，并计算数据、环境、权重三个 Readiness 维度及 Overall Gate。
- 保留 Unknown 与技术故障的区别，提供可追溯证据、人工反馈、修订历史及最终投资决定。
- 公网使用邀请码、安全会话、资源隔离、限流、有界调度、模型预算和出站防护。

## 目录

| 目录 | 内容 |
|---|---|
| `00_Project_Admin/` | 项目管理与研究问题 |
| `01_FGI_Founder_Case/` | FGI 创始案例 |
| `02_Questionnaire/` | 问卷设计与研究记录 |
| `03_Public_Cases/` | 公开案例与来源归档 |
| `04_Async_Tests/` | 异步验证与基线实验 |
| `05_Analysis_and_Decisions/` | 分析结果、假设与决策 |
| `06_Product_Versions/` | 产品版本、交互原型及 AI 方案 |
| `07_ResearchOps_Agent/` | 可运行的 FastAPI / LangGraph 应用 |

## 快速开始

Python 3.11 或更新版本：

```bash
git clone https://github.com/vtrbrydbety/research-ops.git
cd research-ops/07_ResearchOps_Agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

在 `.env` 中将 `RESEARCHOPS_DEPLOYMENT_MODE` 改为 `local`。运行真实评估时，还需填写自己的 `RESEARCHOPS_LLM_API_KEY`；健康检查与离线测试无需模型密钥。

```bash
python -m researchops.serve
```

访问 http://127.0.0.1:8000/mvp/ 。本地模式仅用于回环开发；公网部署按 [部署说明](07_ResearchOps_Agent/docs/secure-public-deployment.md) 配置。

## 技术与验证

Python、FastAPI、LangGraph、Pydantic、HTTPX、SQLite，以及 HTML/CSS/JavaScript MVP。Streamlit 保留为早期计划功能入口。

2026-10-16 发布准备验证：完整离线测试 403 通过，2 项真实模型测试默认跳过；Ruff 与 Chromium 完整业务流程通过。详细边界与验收状态见 [实施记录](07_ResearchOps_Agent/docs/secure-public-implementation-status.md)。

系统提供复现决策支持，不自动训练模型、下载数据集、运行外部仓库代码或执行复现命令。真实评估会将必要材料发送给配置的模型提供商，并可能产生费用。

## 配置与许可证

真实密钥、隧道凭证、邀请码、用户评估数据和本机运行目录不随源码发布。配置示例见 [`.env.example`](07_ResearchOps_Agent/.env.example)。

本仓库原创代码采用 [MIT License](LICENSE)。第三方论文、仓库内容、截图及引文保留原作者权利；本仓库的许可证不替代这些材料各自的授权。
