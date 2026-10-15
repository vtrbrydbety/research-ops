"""应用配置管理模块。

该模块使用 pydantic-settings 统一管理环境变量、.env 文件和默认配置，
避免 FastAPI、Streamlit 以及业务模块分别维护重复配置。
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ResearchOps Agent 的应用配置。

    配置优先从系统环境变量或本地 .env 文件中读取；
    当外部没有提供对应配置时，使用类中定义的默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "ResearchOps Agent"
    app_version: str = "0.1.0"

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    web_port: int = 8501
    api_base_url: str = "http://127.0.0.1:8000"

    log_level: str = "INFO"

    deployment_mode: Literal["public", "local"] = Field(
        default="public", validation_alias="RESEARCHOPS_DEPLOYMENT_MODE"
    )
    public_origin: str = Field(
        default="https://researchops-agent.com", validation_alias="RESEARCHOPS_PUBLIC_ORIGIN"
    )
    security_store_dir: Path = Field(
        default=Path(".runtime/security"), validation_alias="RESEARCHOPS_SECURITY_STORE_DIR"
    )
    session_seconds: int = Field(default=43200, ge=60, le=86400)
    invitation_days: int = Field(default=30, ge=1, le=365)
    invitation_daily_limit: int = Field(default=5, ge=1, le=10000)
    global_daily_limit: int = Field(default=30, ge=1, le=100000)
    execution_concurrency: int = Field(default=2, ge=1, le=8)
    execution_queue_size: int = Field(default=4, ge=0, le=100)
    execution_queue_seconds: int = Field(default=120, ge=1, le=600)
    execution_timeout_seconds: int = Field(default=900, ge=1, le=3600)
    operation_model_attempts: int = Field(default=40, ge=1, le=100)
    global_daily_model_attempts: int = Field(default=500, ge=1, le=100000)
    request_max_bytes: int = Field(default=1048576, ge=1024, le=10485760)
    model_request_max_bytes: int = Field(default=1048576, ge=1024, le=2097152)
    login_ip_limit: int = Field(default=10, ge=1, le=1000)
    login_global_limit: int = Field(default=60, ge=1, le=10000)
    business_principal_limit: int = Field(default=120, ge=1, le=10000)
    business_global_limit: int = Field(default=600, ge=1, le=100000)
    trusted_proxy_ips: tuple[str, ...] = ("127.0.0.1", "::1")

    @model_validator(mode="after")
    def validate_deployment(self) -> "Settings":
        from ipaddress import ip_address
        from urllib.parse import urlsplit

        if not ip_address(self.api_host).is_loopback:
            raise ValueError("API_HOST 必须为回环地址；公网仅通过 Tunnel 访问")
        origin = urlsplit(self.public_origin)
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.username is not None
            or origin.password is not None
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
            or origin.port not in {None, 443}
        ):
            raise ValueError("公网 Origin 必须为标准 HTTPS 域名源")
        self.public_origin = self.public_origin.rstrip("/")
        for proxy in self.trusted_proxy_ips:
            if not ip_address(proxy).is_loopback:
                raise ValueError("当前仅支持同机回环可信代理")
        if self.deployment_mode == "local" and self.security_store_dir == Path(".runtime/security"):
            self.security_store_dir = Path(".runtime/security-local")
        return self

    llm_provider: str = Field(default="deepseek", validation_alias="RESEARCHOPS_LLM_PROVIDER")
    llm_api_mode: Literal["strict_tools", "responses", "chat_completions"] = Field(
        default="strict_tools",
        validation_alias="RESEARCHOPS_LLM_API_MODE",
    )
    llm_base_url: str = Field(
        default="https://api.deepseek.com",
        validation_alias="RESEARCHOPS_LLM_BASE_URL",
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="RESEARCHOPS_LLM_API_KEY",
    )
    llm_model: str = Field(
        default="deepseek-flash",
        validation_alias="RESEARCHOPS_LLM_MODEL",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        le=300,
        validation_alias="RESEARCHOPS_LLM_TIMEOUT_SECONDS",
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias="RESEARCHOPS_LLM_MAX_RETRIES",
    )
    llm_max_output_tokens: int = Field(
        default=16384,
        ge=256,
        le=32768,
        validation_alias="RESEARCHOPS_LLM_MAX_OUTPUT_TOKENS",
    )
    llm_context_max_total_chars: int = Field(
        default=120_000,
        ge=1_000,
        le=500_000,
        validation_alias="RESEARCHOPS_LLM_CONTEXT_MAX_TOTAL_CHARS",
    )
    llm_context_max_source_chars: int = Field(
        default=40_000,
        ge=500,
        le=100_000,
        validation_alias="RESEARCHOPS_LLM_CONTEXT_MAX_SOURCE_CHARS",
    )
    llm_context_max_sources: int = Field(
        default=32,
        ge=1,
        le=64,
        validation_alias="RESEARCHOPS_LLM_CONTEXT_MAX_SOURCES",
    )
    llm_context_max_candidate_chars: int = Field(
        default=1_000_000,
        ge=1_000,
        le=2_000_000,
        validation_alias="RESEARCHOPS_LLM_CONTEXT_MAX_CANDIDATE_CHARS",
    )
    llm_analysis_run_ttl_seconds: float = Field(
        default=3600.0,
        gt=0,
        le=86_400,
        validation_alias="RESEARCHOPS_LLM_ANALYSIS_RUN_TTL_SECONDS",
    )
    llm_analysis_run_max_entries: int = Field(
        default=100,
        ge=1,
        le=10_000,
        validation_alias="RESEARCHOPS_LLM_ANALYSIS_RUN_MAX_ENTRIES",
    )
    assessment_review_ttl_seconds: float = Field(
        default=86_400.0,
        gt=0,
        le=604_800,
        validation_alias="RESEARCHOPS_ASSESSMENT_REVIEW_TTL_SECONDS",
    )
    assessment_review_store_dir: Path = Field(
        default=Path(".runtime/assessment-reviews"),
        validation_alias="RESEARCHOPS_ASSESSMENT_REVIEW_STORE_DIR",
    )
    llm_https_proxy: str | None = Field(
        default=None,
        validation_alias="RESEARCHOPS_LLM_HTTPS_PROXY",
    )
    research_max_rounds: int = Field(
        default=5,
        ge=1,
        le=5,
        validation_alias="RESEARCHOPS_RESEARCH_MAX_ROUNDS",
    )
    research_max_tool_requests: int = Field(
        default=12,
        ge=1,
        le=12,
        validation_alias="RESEARCHOPS_RESEARCH_MAX_TOOL_REQUESTS",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """将日志等级统一转换为大写形式。

        这样无论用户配置 info、Info 还是 INFO，
        后续日志模块都可以按照统一格式处理。
        """
        return value.upper()

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        """当前真实模型适配器只接受 DeepSeek。"""
        normalized = value.strip().lower()
        if normalized != "deepseek":
            raise ValueError("当前仅支持 deepseek LLM provider")
        return normalized

    @field_validator("llm_base_url")
    @classmethod
    def normalize_llm_base_url(cls, value: str) -> str:
        """只允许 HTTPS 模型端点，避免密钥通过明文链路发送。"""
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("RESEARCHOPS_LLM_BASE_URL 必须使用 HTTPS")
        return normalized

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, value: str) -> str:
        """拒绝空模型名，具体可用性由服务端响应确认。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("RESEARCHOPS_LLM_MODEL 不得为空")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """返回经过缓存的应用配置对象。

    使用缓存可以避免应用中的不同模块反复读取环境变量和 .env 文件。
    """
    return Settings()
