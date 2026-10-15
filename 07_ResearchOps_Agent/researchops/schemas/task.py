"""论文复现任务相关的领域模型。

这些模型定义 API 请求、复现步骤、完整计划以及 API 响应的稳定数据结构。
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 任务当前允许出现的生命周期状态。
TaskStatus = Literal[
    "created",
    "planning",
    "planned",
    "failed",
]


class StrictModel(BaseModel):
    """领域模型的统一基类。

    禁止接收未声明字段，可以尽早发现字段拼写错误；
    同时自动清理字符串首尾空白。
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class TaskRequest(StrictModel):
    """用户提交的论文复现规划请求。"""

    user_request: str = Field(
        min_length=1,
        max_length=4000,
        description="Natural-language description of the reproduction task.",
    )
    paper_name: str | None = Field(
        default=None,
        description="Optional paper or method name.",
    )
    repository_url: str | None = Field(
        default=None,
        description="Optional source-code repository URL.",
    )


class PlanStep(StrictModel):
    """复现计划中的一个有序步骤。"""

    step_id: int = Field(
        ge=1,
        description="One-based step sequence number.",
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Short step title.",
    )
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Detailed explanation of the step.",
    )
    tool: str = Field(
        min_length=1,
        max_length=100,
        description="Tool or capability expected to perform the step.",
    )
    approval_required: bool = Field(
        default=False,
        description="Whether a human must approve the step before execution.",
    )
    expected_output: str = Field(
        min_length=1,
        max_length=1000,
        description="Expected evidence or artifact produced by the step.",
    )


class ReproductionPlan(StrictModel):
    """一个完整、结构化的论文复现计划。"""

    objective: str = Field(
        min_length=1,
        max_length=1000,
        description="Primary objective of the reproduction task.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made while generating the plan.",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Assets and conditions required before execution.",
    )
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Ordered reproduction steps.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Known technical, data, or safety risks.",
    )
    final_outputs: list[str] = Field(
        default_factory=list,
        description="Artifacts expected after the plan is executed.",
    )


class TaskResponse(StrictModel):
    """FastAPI 返回给调用方的任务响应。"""

    task_id: UUID = Field(
        description="Unique identifier assigned to the task.",
    )
    status: TaskStatus = Field(
        description="Current lifecycle status of the task.",
    )
    reproduction_plan: ReproductionPlan | None = Field(
        default=None,
        description="Generated plan when planning succeeds.",
    )
    trace_summary: list[str] = Field(
        default_factory=list,
        description="Human-readable summaries of workflow events.",
    )
