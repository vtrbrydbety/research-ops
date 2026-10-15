# Blockers

用于记录 Day 1 开发过程中遇到的问题、定位过程和降级策略。

| 时间 | 问题 | 影响 | 已尝试方案 | 解决或降级方案 | 状态 |
|---|---|---|---|---|---|
| 2026-07-31 | Streamlit 调用本地 FastAPI 时返回 HTTP 502 | 页面无法生成复现计划 | 检查 FastAPI、关闭代理、使用 HTTPX 单独访问 `/health` | 在 `PlanningApiClient` 中设置 `trust_env=False`，避免本地请求读取系统代理配置；重启 Streamlit 后恢复正常 | RESOLVED |
| 2026-07-31 | Ruff `format --check` 在显示格式差异时发生自身 panic | 首次格式检查未正常结束 | 分析 Ruff 输出，确认 pytest 仍通过 | 先运行 `ruff check . --fix` 和 `ruff format .`，再重新执行质量门禁，最终全部通过 | RESOLVED |

## 当前未解决问题

暂无阻塞 Day 1 验收的问题。

## 已知技术债

1. RuleBasedPlanner 只能生成固定结构计划，尚未接入真实 LLM。
2. 尚未解析真实论文 PDF、README 或 GitHub 仓库。
3. 任务状态仅存在于单次工作流和页面会话中，尚未持久化。
4. 尚未实现人工审批后的中断恢复。
5. 尚未执行 Docker、GPU 或真实模型推理。
6. 当前依赖未完全锁定到精确版本，后续需要增加锁文件或约束文件。