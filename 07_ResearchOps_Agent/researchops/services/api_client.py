"""ResearchOps FastAPI 客户端。

该模块封装 Streamlit 页面与 FastAPI 服务之间的 HTTP 通信，
使页面只负责收集输入和展示结果，不直接处理复杂的请求、
响应解析和异常转换逻辑。
"""

from __future__ import annotations

import httpx
from pydantic import ValidationError

from researchops.schemas import ErrorResponse, TaskRequest, TaskResponse


class ApiClientError(RuntimeError):
    """调用 ResearchOps API 失败时抛出的统一客户端异常。"""

    def __init__(
        self,
        *,
        message: str,
        error_code: str = "API_CLIENT_ERROR",
        task_id: str | None = None,
        details: list[str] | None = None,
    ) -> None:
        """保存页面展示错误所需的安全信息。"""
        super().__init__(message)

        self.message = message
        self.error_code = error_code
        self.task_id = task_id
        self.details = details or []


class PlanningApiClient:
    """用于调用论文复现规划接口的同步 HTTP 客户端。"""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        trust_env: bool = False,
    ) -> None:
        """初始化 API 地址、超时时间和可选测试传输层。

        Args:
            base_url: FastAPI 服务根地址。
            timeout_seconds: 单次 HTTP 请求的最长等待时间。
            transport: 测试时可注入 MockTransport，避免依赖真实网络。
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.trust_env = trust_env

    def create_plan(
        self,
        user_request: str,
    ) -> TaskResponse:
        """调用 FastAPI 创建论文复现计划。

        Args:
            user_request: 用户在 Streamlit 页面输入的复现需求。

        Returns:
            经过 Pydantic 校验的 TaskResponse。

        Raises:
            ApiClientError: 网络失败、服务端拒绝请求或响应格式异常时抛出。
        """
        try:
            # 在发起 HTTP 请求前先执行本地模型校验，
            # 可以更快地向用户反馈空输入等明显错误。
            request_model = TaskRequest(
                user_request=user_request,
            )
        except ValidationError as exc:
            raise ApiClientError(
                error_code="CLIENT_VALIDATION_ERROR",
                message="请输入有效的论文复现需求。",
                details=[error["msg"] for error in exc.errors()],
            ) from exc

        request_url = f"{self.base_url}/api/v1/tasks/plan"

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
                # 本项目默认访问本地 FastAPI，避免请求经过系统代理。
                trust_env=self.trust_env,
            ) as client:
                response = client.post(
                    request_url,
                    json=request_model.model_dump(mode="json"),
                )
        except httpx.TimeoutException as exc:
            raise ApiClientError(
                error_code="API_TIMEOUT",
                message="FastAPI 服务响应超时，请稍后重试。",
            ) from exc
        except httpx.RequestError as exc:
            raise ApiClientError(
                error_code="API_UNAVAILABLE",
                message=("无法连接 FastAPI 服务，请确认后端已经启动，并检查 API 地址。"),
                details=[str(exc)],
            ) from exc

        if response.is_success:
            try:
                return TaskResponse.model_validate(response.json())
            except (
                ValueError,
                ValidationError,
            ) as exc:
                raise ApiClientError(
                    error_code="INVALID_API_RESPONSE",
                    message="FastAPI 返回了无法识别的成功响应。",
                ) from exc

        self._raise_api_error(response)

    @staticmethod
    def _raise_api_error(
        response: httpx.Response,
    ) -> None:
        """将 FastAPI 错误响应转换为 ApiClientError。"""
        try:
            error_response = ErrorResponse.model_validate(response.json())
        except (
            ValueError,
            ValidationError,
        ) as exc:
            raise ApiClientError(
                error_code="INVALID_API_ERROR_RESPONSE",
                message=(f"FastAPI 请求失败，HTTP 状态码为 {response.status_code}。"),
            ) from exc

        details = [detail.message for detail in error_response.details]

        raise ApiClientError(
            error_code=error_response.error_code,
            message=error_response.message,
            task_id=(str(error_response.task_id) if error_response.task_id else None),
            details=details,
        )
