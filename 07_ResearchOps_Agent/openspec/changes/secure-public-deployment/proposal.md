# Proposal

## Why

ResearchOps 在 Mac mini 本地运行正常，但公网域名目前返回 Cloudflare 530/1033；现有 API 缺少身份校验、数据归属检查及全局任务限制。恢复隧道时必须同步建立访问与资源边界，避免公开入口消耗模型额度、暴露评估数据或服务器环境。

## What Changes

- 采用免注册、每人一个可撤销邀请码；验证后通过安全 Cookie 建立会话，由本地管理命令签发、停用和调整额度。
- **BREAKING**：公网部署中的全部业务 API 必须通过会话校验；页面登录入口和最小健康检查采用明确的匿名白名单。
- **BREAKING**：任务、评估、历史、反馈和最终决定按邀请码主体隔离；无归属的历史结果不自动开放给任何访客。
- 为登录尝试、业务请求和模型工作设置限流、有界队列、全局并发、每日额度及模型调用硬上限，额度与归属在重启后保留。
- **BREAKING**：公网部署关闭服务器只读环境检测，保留手动输入与环境快照；增加 CSRF、请求体限制、安全响应头、出站访问约束和敏感信息保护。
- 使用显式配置路径修复 cloudflared 服务；FastAPI 仅监听回环地址，以非 root 身份运行；提供可检查、可回滚的 macOS 常驻部署、日志轮转和验收流程。
- 将 FileVault 解锁、登录前启动、断网恢复、防睡眠和 Windows 旧 connector 检查纳入运维约束，不承诺加密磁盘未解锁时的无人值守启动。
- 经用户确认，将现有研究链与旧测试的契约一致性修复纳入：迁移已退役的测试入口、修复实际缺陷，保留来源验证、失败分类、反馈及 Rule Gate 断言，并完成受控完整流程验收。

## Capabilities

### New Capabilities

- `invitation-access`: 邀请码生命周期、安全会话、登录防猜测及业务接口访问控制。
- `assessment-ownership`: 任务及评估数据的主体归属、跨邀请码隔离和历史数据处理。
- `execution-budgets`: 请求限流、任务准入、有界调度、持久化每日额度与模型调用预算。
- `public-request-security`: 公网模式的请求安全、服务器环境隔离、出站访问防护和日志脱敏。
- `macos-tunnel-operations`: 回环源站、显式隧道配置、常驻运行、诊断、恢复及公网验收。

### Modified Capabilities

无。当前主规格目录没有已定义能力；以上均为新增规格。

## Impact

- `apps/api/main.py`、`apps/mvp/index.html`、`apps/mvp/mvp-api.js`：访问入口、会话、CSRF、错误反馈及路由保护。
- `researchops/core/config.py`、`security.py`、日志模块：公网配置校验、身份及请求安全。
- `assessment_jobs.py`、`readiness_workflow.py`、`human_review.py`、`assessment_review_store.py`、`deepseek_analysis.py` 及材料采集服务：归属传递、持久化准入、模型预算、出站安全。
- 新增基于标准库 SQLite 的访问控制与配额状态、本地管理命令、部署模板及运维文档；尽量复用现有依赖，不引入注册系统、Redis 或云数据库。
- 主机实施涉及 launchd 配置、凭证文件权限和电源设置；需要实施阶段具备管理员执行条件。当前只编写规划，不改系统、不重启。
- 兼容已有本地测试与业务领域模型；公网认证默认启用，本地免认证仅能显式启用且绑定回环地址。
- 不包含开放注册、计费、多节点高可用、公开管理后台、Cloudflare Access 强制登录或默认 Turnstile 集成。
