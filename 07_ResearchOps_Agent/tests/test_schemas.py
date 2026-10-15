"""任务领域模型与 LangGraph 状态模型测试。"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from researchops.schemas import (
    PlanStep,
    ReproductionPlan,
    TaskRequest,
    TaskResponse,
)
from researchops.states import AgentState


def build_example_plan() -> ReproductionPlan:
    """构造供多个测试复用的有效 FGI 复现计划。"""
    return ReproductionPlan(
        objective="Prepare the FGI DFDC pretrained inference workflow.",
        assumptions=["The repository and documentation will be available later."],
        prerequisites=[
            "FGI paper or README",
            "Repository URL",
            "Dataset and checkpoint information",
        ],
        steps=[
            PlanStep(
                step_id=1,
                title="Collect project assets",
                description=(
                    "Collect the paper, repository documentation, "
                    "dataset instructions, and checkpoint information."
                ),
                tool="repository_inspector",
                approval_required=False,
                expected_output="A structured project asset inventory.",
            ),
            PlanStep(
                step_id=2,
                title="Execute inference",
                description=("Run the approved pretrained inference command."),
                tool="shell",
                approval_required=True,
                expected_output="Inference metrics and execution logs.",
            ),
        ],
        risks=["The required checkpoint may not be publicly available."],
        final_outputs=[
            "Validated inference command",
            "Reproduction report",
        ],
    )


def test_task_request_requires_user_request() -> None:
    """验证缺少或只包含空白字符的 user_request 会触发校验错误。"""
    with pytest.raises(ValidationError):
        TaskRequest()

    with pytest.raises(ValidationError):
        TaskRequest(user_request="   ")


def test_reproduction_plan_serialization() -> None:
    """验证结构化复现计划可以稳定序列化为 JSON 兼容数据。"""
    plan = build_example_plan()

    payload = plan.model_dump(mode="json")

    assert payload["objective"].startswith("Prepare the FGI")
    assert len(payload["steps"]) == 2
    assert payload["steps"][1]["tool"] == "shell"
    assert payload["steps"][1]["approval_required"] is True


def test_agent_state_and_response_serialization() -> None:
    """验证 AgentState 转换为 API 响应后不会丢失计划和状态信息。"""
    task_id = uuid4()
    plan = build_example_plan()

    state = AgentState(
        task_id=task_id,
        user_request="Generate an FGI reproduction plan.",
        reproduction_plan=plan,
        status="planned",
    )

    response = TaskResponse(
        task_id=state.task_id,
        status=state.status,
        reproduction_plan=state.reproduction_plan,
        trace_summary=["generate_plan: success"],
    )

    payload = response.model_dump(mode="json")

    assert state.current_stage == "created"
    assert state.errors == []
    assert state.trace == []
    assert payload["task_id"] == str(task_id)
    assert payload["status"] == "planned"
    assert len(payload["reproduction_plan"]["steps"]) == 2
