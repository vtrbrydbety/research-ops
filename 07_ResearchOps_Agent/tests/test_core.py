"""应用配置和结构化日志测试。"""

import json
import logging
import sys

from researchops.core.config import Settings
from researchops.core.logging import JsonFormatter


def test_settings_read_environment_variables(monkeypatch) -> None:
    """验证环境变量可以覆盖 Settings 中定义的默认配置。"""
    monkeypatch.setenv("APP_NAME", "ResearchOps Test")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    # 禁用 .env 文件，保证该测试只验证环境变量覆盖行为。
    settings = Settings(_env_file=None)

    assert settings.app_name == "ResearchOps Test"
    assert settings.api_port == 9000
    assert settings.log_level == "DEBUG"


def test_json_formatter_contains_required_fields() -> None:
    """验证 JSON 日志包含任务追踪所需的全部基础字段。"""
    record = logging.LogRecord(
        name="researchops.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Configuration loaded",
        args=(),
        exc_info=None,
    )

    record.task_id = "task-123"
    record.component = "test"

    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["level"] == "INFO"
    assert payload["task_id"] == "task-123"
    assert payload["component"] == "test"
    assert payload["message"] == "Configuration loaded"
    assert "timestamp" in payload


def test_json_formatter_redacts_credentials_from_message_and_exception() -> None:
    secret = "sk-examplecredential123456789"
    try:
        raise RuntimeError(f"provider failed with Authorization: Bearer {secret}")
    except RuntimeError:
        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name="researchops.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=f"api_key={secret}",
        args=(),
        exc_info=exc_info,
    )

    formatted = JsonFormatter().format(record)

    assert secret not in formatted
    assert "[REDACTED:" in formatted
