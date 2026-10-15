"""论文复现规划工作流节点测试。"""

from uuid import uuid4

from researchops.nodes import PlanningNodes
from researchops.schemas import PlanStep, ReproductionPlan
from researchops.services import RuleBasedPlanner
from researchops.states import AgentState, AgentStateUpdate

EXAMPLE_REQUEST = "  请分析   FGI 论文仓库，\n并生成 DFDC 预训练模型推理复现计划。  "


def apply_update(
    state: AgentState,
    update: AgentStateUpdate,
) -> AgentState:
    """将节点局部更新应用到完整状态并重新执行 Pydantic 校验。"""
    payload = state.model_dump()
    payload.update(update)

    return AgentState.model_validate(payload)


def test_normalize_request_removes_redundant_whitespace() -> None:
    """验证规范化节点能够压缩连续空格和换行。"""
    nodes = PlanningNodes(RuleBasedPlanner())
    state = AgentState(
        task_id=uuid4(),
        user_request=EXAMPLE_REQUEST,
    )

    update = nodes.normalize_request(state)

    assert update["status"] == "planning"
    assert update["normalized_request"] == (
        "请分析 FGI 论文仓库，并生成 DFDC 预训练模型推理复现计划。"
    )
    assert update["trace"][-1].status == "success"


def test_normalize_request_records_empty_input_error() -> None:
    """验证空输入会被转换为结构化错误，而不是导致节点崩溃。"""
    nodes = PlanningNodes(RuleBasedPlanner())
    state = AgentState(
        task_id=uuid4(),
        user_request="   ",
    )

    update = nodes.normalize_request(state)

    assert update["status"] == "failed"
    assert update["normalized_request"] is None
    assert "用户请求不能为空。" in update["errors"]
    assert update["trace"][-1].status == "error"


def test_planning_nodes_complete_successful_flow() -> None:
    """验证四个节点顺序执行后能够形成 planned 最终状态。"""
    nodes = PlanningNodes(RuleBasedPlanner())
    state = AgentState(
        task_id=uuid4(),
        user_request=EXAMPLE_REQUEST,
    )

    state = apply_update(
        state,
        nodes.normalize_request(state),
    )
    state = apply_update(
        state,
        nodes.generate_plan(state),
    )
    state = apply_update(
        state,
        nodes.validate_plan(state),
    )
    state = apply_update(
        state,
        nodes.finalize(state),
    )

    assert state.status == "planned"
    assert state.current_stage == "completed"
    assert state.reproduction_plan is not None
    assert len(state.reproduction_plan.steps) == 6
    assert state.errors == []
    assert [event.node for event in state.trace] == [
        "normalize_request",
        "generate_plan",
        "validate_plan",
        "finalize",
    ]


def test_validate_plan_rejects_unapproved_shell_step() -> None:
    """验证未设置人工审批的 shell 执行步骤会导致校验失败。"""
    nodes = PlanningNodes(RuleBasedPlanner())

    unsafe_plan = ReproductionPlan(
        objective="测试不安全执行步骤。",
        steps=[
            PlanStep(
                step_id=1,
                title="人工审批",
                description="由用户检查执行方案。",
                tool="human_approval",
                approval_required=True,
                expected_output="用户审批结果。",
            ),
            PlanStep(
                step_id=2,
                title="执行命令",
                description="运行未经审批标记的 shell 命令。",
                tool="shell",
                approval_required=False,
                expected_output="命令执行结果。",
            ),
        ],
    )

    state = AgentState(
        task_id=uuid4(),
        user_request="测试安全校验。",
        normalized_request="测试安全校验。",
        reproduction_plan=unsafe_plan,
        status="planning",
    )

    update = nodes.validate_plan(state)

    assert update["status"] == "failed"
    assert any("没有设置人工审批" in error for error in update["errors"])
    assert update["trace"][-1].status == "error"
