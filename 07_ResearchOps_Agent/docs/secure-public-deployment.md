# ResearchOps 受邀访问与公网部署

## 配置和本地开发

默认 `RESEARCHOPS_DEPLOYMENT_MODE=public`，API 只监听 `127.0.0.1`。公网入口通过 Tunnel；不允许直接把 API_HOST 改成 0.0.0.0。`.env.example` 提供无秘密示例。开发时显式设置 `RESEARCHOPS_DEPLOYMENT_MODE=local`，使用隔离的 `.runtime/security-local`，不要把生产控制库用于免认证测试。

运行测试：`.venv/bin/python -m pytest`。安全测试使用临时目录，不接触生产邀请码和额度。进程控制库不支持多个 API worker，部署只运行一个 worker。

## 本地邀请码管理

在项目目录，以实际运行应用的用户执行：

```sh
.venv/bin/python -m researchops.access create --label alice --days 30 --limit 5
.venv/bin/python -m researchops.access list
.venv/bin/python -m researchops.access update PRINCIPAL_UUID --limit 10
.venv/bin/python -m researchops.access revoke PRINCIPAL_UUID
```

生成命令只显示一次明文邀请码，通过可信渠道单独交给对应的人。列表不提供恢复明文功能；丢失应停用旧码再生成新码。每人独立发码，同一码共享额度和评估数据，停用会使该码所有会话失效。管理命令只在本机提供，没有公网管理 API。

## 控制状态和备份

生产状态位于 `.runtime/security/control.sqlite3`，目录 0700、数据库 0600，仅存邀请码和会话摘要。会话、额度、资源归属在重启后保留，未完成任务不会自动重跑。不要删除数据库以解决额度不足，否则会丢失撤销和归属信息。

升级前停止应用，再一起备份 `.runtime/security` 和 `.runtime/assessment-reviews`，备份目录保持 0700，不放进 Git。运行时备份 SQLite 应使用 sqlite3 backup API，不能随意复制正在写入的数据库。恢复时采用同一时刻的数据库和评估文件；归属缺失默认拒绝访问。

旧评估不会自动对新邀请码公开。确认文件有效并备份后，可显式绑定：

```sh
.venv/bin/python -m researchops.access bind ASSESSMENT_UUID PRINCIPAL_UUID
```

评估有绝对保留期限，读取不会无限续期。控制库定期清理过期会话和限流状态、30 天审计（最多 10,000 条）、90 天之前的日用量和过期终态操作；不会清理仍在运行的任务或重置当日消耗。

## 浏览器访问协议

`POST /api/v1/access/sessions` 提交 JSON `invitation_code`，必须携带同源 Origin。成功返回主体 ID、到期时间和 CSRF，浏览器保存 Secure/HttpOnly/SameSite=Strict Cookie。`GET /api/v1/access/session` 恢复会话。`DELETE /api/v1/access/session` 退出，需要同源 Origin 和 `X-CSRF-Token`。全部已登录写请求都需要这两个校验；邀请码及 CSRF 不存 localStorage。

所有业务接口默认要求会话；匿名仅可加载入口和必要静态资源、兑换邀请码及最小 `/health`。公网关闭 `/docs`、`/redoc`、`/openapi.json`；`/api/v1/readiness` 要求登录且不执行真实模型请求。现有 API 测试显式选择本地模式；`test_public_access.py` 用真实路由和临时库单独验证公网边界。

受邀用户打开域名，输入邀请码即可使用；无需创建账号。会话默认最多 12 小时，邀请码默认 30 天，结果默认绝对保留最多 24 小时。多人使用同一码会共享记录和额度。操作材料会按需发送至模型提供商，请勿提交不希望交给该提供商的敏感材料。公网不检测 Mac mini 环境，复现环境通过手动输入或快照提供。完成评估后可在结果页记录最终投资决定及可选理由；该记录不会改写 Rule Gate，也不执行复现或调用模型。

## 资源限制与错误

默认每码每天 5 次高成本操作，全站 30 次；同步评估、后台评估及反馈重评共享额度。全站同时执行 2 项、等待最多 4 项，每码最多一个未完成任务；排队最多 120 秒，执行最多 900 秒。额度日期按 Asia/Shanghai。材料或模型执行开始后，即使失败也计数；尚未执行就取消的排队任务仅退回一次操作预留。重启中断的任务不会自动重跑。

每操作最多 40 次模型 HTTP 尝试、全站每天 500 次，重试和协议回退都计数，usage 缺失也计数。输入、输出 token 和时限另有硬上限。这控制调用量，不等于人民币账单精确封顶；结合提供商账户余额/额度控制使用。用本地 CLI 调整邀请码额度，全站配置在受控重启后生效。

| 状态 | 含义及处理 |
|---|---|
| 401 | 会话失效，重新输入邀请码；不自动重新提交评估 |
| 403 | Origin/CSRF 错误或服务器探测禁用；刷新会话或手动提供环境 |
| 404 | 资源不存在、已过期或不属于该邀请码 |
| 413 | 请求或模型输入过大，缩小材料 |
| 429 | 请求频繁、主体忙碌或额度耗尽，按 Retry-After 等待 |
| 503 | 容量或安全状态暂不可用，按 Retry-After 手动重试 |
| 504 | 操作超时；真实执行结束前不会释放并发槽 |

默认每码每分钟 120 次业务请求允许正常 750ms 进度轮询。生产出站不支持任意代理配置，避免代理重新解析而绕过目标地址绑定；仅允许标准公网 HTTP/HTTPS 端口。HTTPX/HTTPCore 版本约束用于传输集成，升级前重跑 `test_outbound.py`。

出站传输统一限制每个响应最多 4 MiB，已有采集器更小的限制继续生效；请求使用 Accept-Encoding: identity，拒绝仍返回压缩内容的响应，避免解压绕过大小上限。连接、TLS 和每次读写都按任务剩余时间收紧超时。普通回归测试使用临时评估目录，并默认清空付费模型密钥；真实模型验收须显式单独执行。受限连通性检查使用 `.venv/bin/python tools/check_live_model.py --run-live`：仅发送合成材料，最多 2 次 HTTP、每次输出最多 1,200 token、独立临时账本；会产生真实提供商调用，不能放入常规回归。

## macOS 部署

先完成安全和业务回归再启用公网；模板位于 `deploy/macos/`。以下步骤需要管理员执行条件，逐步执行，不把 sudo 密码写入脚本。检查工具不会自动执行安装或 reboot。

1. 记录发布 Git 提交、`launchctl print`、`lsof -nP -iTCP:8000 -sTCP:LISTEN`、`pmset -g custom`；备份旧 plist、cloudflared 配置及凭证、业务状态和电源原值。备份目录 0700、文件 0600。
2. 停旧用户 Agent 后完成最终数据备份；安装 Python 系统服务，plist 属于 root:wheel、0644。模板通过 `UserName=lanting` 以非 root 身份启动，单 worker、回环监听，禁止 Uvicorn 自动改写原始代理来源。

```sh
launchctl bootout "gui/$(id -u)/com.researchops.agent"
sudo install -o root -g wheel -m 644 deploy/macos/com.researchops.agent.plist /Library/LaunchDaemons/com.researchops.agent.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.researchops.agent.plist
sudo launchctl print system/com.researchops.agent
```

3. 用两个测试邀请码验证回环源站的认证、隔离、撤销、额度和禁用探测。浏览器检查：`.venv/bin/python tools/check_public_browser.py`，使用真实应用与 Chromium 的 ASGI 桥接，配合可控材料和模型 HTTP 响应验证完整评估、反馈及最终决定；不触碰生产凭证或调用付费模型。先安装开发依赖 `pip install -e '.[dev]'`，再安装浏览器：`python -m playwright install chromium`。只读模板检查：`.venv/bin/python tools/check_deployment.py`；可加 `--installed` 检查安装文件权限，不读取凭证内容。
4. 核实 Windows 旧 connector 已停用或同等防护。同隧道多副本是合法冗余；无防护旧源站不得继续承接流量。无法核实时，公网验收保持待完成。
5. 安装显式配置和该隧道 JSON，目录 0700、文件 0600；不复制 cert.pem。两个模板均以 lanting 运行，避免 root 执行用户目录内的 Python。指标只在回环地址开放。

```sh
sudo install -d -o lanting -g staff -m 700 /etc/cloudflared
sudo install -o lanting -g staff -m 600 /Users/lanting/.cloudflared/1be9a224-0f36-4d38-87a9-890024dd4e3e.json /etc/cloudflared/1be9a224-0f36-4d38-87a9-890024dd4e3e.json
sudo install -o lanting -g staff -m 600 deploy/macos/cloudflared.config.yml /etc/cloudflared/config.yml
cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
sudo launchctl bootout system/com.cloudflare.cloudflared
sudo install -o root -g wheel -m 644 deploy/macos/com.cloudflare.cloudflared.plist /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

6. 保存电源原值后执行 `sudo pmset -c sleep 0`，保留显示器睡眠。Cloudflare 侧启用 HTTPS、确认 `/api/*` 和入口不被自定义缓存规则缓存，再配置套餐支持的边缘防护；应用限流仍必须保留。
7. 应用和隧道日志位于 `.runtime/logs/api.log`、`tunnel.log`，各 10 MiB、最多 5 个轮转备份。runner 转发终止信号并脱敏输出，无需重命名仍被 daemon 打开的日志文件。检查注册连接记录，不开启会输出完整请求头的 debug 日志。
8. 用独立移动网络填写 `deploy/macos/acceptance.md`；真实评估计入额度。异常退出、断网和重启在协调时间执行。FileVault 保持开启，卷解锁前不能保证服务启动；必须记录实际解锁前提及解锁后无需手动启动的证据。

## 故障定位及回滚

本地 health 正常而公网 530/1033 时，依次检查实际启动参数、显式配置和权限、connector 注册日志、域名路由和旧副本；PID 存在不代表隧道可用。401/404 是访问控制结果；用受保护 readiness 和任务安全错误区分模型故障，不在 health 调用模型。

回滚先 `sudo launchctl bootout system/com.cloudflare.cloudflared`，确认没有其他 connector 仍承接旧服务；必要时暂时移除域名隧道路由。停新应用、保留新控制库备份，再恢复匹配版本的配置和业务数据。旧无防护应用只以回环地址运行，不重新公开匿名 API。恢复电源设置使用此前记录的原值。不把可能重新激活已撤销邀请码的旧数据库直接上线。
