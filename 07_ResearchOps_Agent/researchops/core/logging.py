"""结构化日志工具模块。

日志统一输出为 JSON，便于后续根据 task_id、component 和 level
检索某个任务的完整执行过程。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from researchops.core.security import redact_sensitive_text


class JsonFormatter(logging.Formatter):
    """将 Python 日志记录格式化为 JSON 字符串。"""

    def format(self, record: logging.LogRecord) -> str:
        """把一条 LogRecord 转换为结构化 JSON。

        除了日志系统自带的时间和等级，还会读取业务模块传入的
        task_id 与 component。缺少这些字段时使用安全默认值。
        """
        payload: dict[str, Any] = {
            # 后端日志统一使用 UTC，避免不同运行环境产生时区歧义。
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "task_id": getattr(record, "task_id", "-"),
            "component": getattr(record, "component", record.name),
            "message": redact_sensitive_text(record.getMessage()),
        }

        # 发生异常时保留格式化后的堆栈，供开发人员排查问题。
        if record.exc_info:
            payload["exception"] = redact_sensitive_text(self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """初始化 ResearchOps Agent 的结构化日志。

    Args:
        level: 日志等级，例如 INFO、DEBUG 或 ERROR。

    Raises:
        ValueError: 当传入的日志等级不受 Python logging 支持时抛出。
    """
    normalized_level = level.upper()
    numeric_level = getattr(logging, normalized_level, None)

    if not isinstance(numeric_level, int):
        raise ValueError(f"Unsupported log level: {level}")

    application_logger = logging.getLogger("researchops")
    application_logger.setLevel(numeric_level)

    # 阻止日志继续传播到根日志器，避免同一条日志被重复输出。
    application_logger.propagate = False

    # 重新配置时先移除旧 Handler，避免应用热重载后重复添加。
    application_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)
    handler.setFormatter(JsonFormatter())

    application_logger.addHandler(handler)


def get_logger(
    component: str,
    task_id: str = "-",
) -> logging.LoggerAdapter:
    """创建包含业务上下文的日志适配器。

    Args:
        component: 当前产生日志的业务组件名称。
        task_id: 当前任务的唯一标识；无任务上下文时使用默认值。

    Returns:
        自动携带 component 和 task_id 的 LoggerAdapter。
    """
    logger = logging.getLogger(f"researchops.{component}")

    return logging.LoggerAdapter(
        logger,
        {
            "component": component,
            "task_id": task_id,
        },
    )
