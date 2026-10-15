"""FastAPI 接口使用的公共响应模型。

该模块只定义 API 接入层的数据结构，不包含工作流或业务处理逻辑。
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from researchops.schemas.task import StrictModel


class HealthResponse(StrictModel):
    """服务健康检查响应。"""

    service: str = Field(
        min_length=1,
        description="当前服务名称。",
    )
    status: Literal["ok"] = Field(
        default="ok",
        description="服务健康状态。",
    )
    version: str = Field(
        min_length=1,
        description="当前应用版本。",
    )


class ErrorDetail(StrictModel):
    """一条具体的 API 错误信息。"""

    field: str | None = Field(
        default=None,
        description="发生错误的请求字段。",
    )
    message: str = Field(
        min_length=1,
        description="可安全展示给调用方的错误说明。",
    )
    error_type: str | None = Field(
        default=None,
        description="校验器或业务层返回的错误类型。",
    )


class ErrorResponse(StrictModel):
    """API 统一错误响应。"""

    error_code: str = Field(
        min_length=1,
        description="供程序识别的稳定错误码。",
    )
    message: str = Field(
        min_length=1,
        description="供用户阅读的错误摘要。",
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="具体字段或业务错误信息。",
    )
    task_id: UUID | None = Field(
        default=None,
        description="已经创建任务时返回对应 task_id。",
    )
