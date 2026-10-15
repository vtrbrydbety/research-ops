"""论文复现规划 LangGraph 端到端测试。"""

from uuid import uuid4

from researchops.graphs import (
    build_reproduction_graph,
    invoke_reproduction_graph,
)
from researchops.nodes import SIDE_EFFECT_TOOLS
from researchops.states import AgentState

EXAMPLE_REQUEST = (
    "  请分析   FGI 论文仓库，\n并生成 DFDC 预训练模型推理复现计划，实际执行前必须人工审批。  "
)


def run_example_graph(user_request: str) -> AgentState:
    """构建并运行一次独立工作流，返回最终状态。"""
    graph = build_reproduction_graph()

    initial_state = AgentState(
        task_id=uuid4(),
        user_request=user_request,
    )

    return invoke_reproduction_graph(
        graph=graph,
        initial_state=initial_state,
    )


def test_graph_generates_plan() -> None:
    """验证完整 LangGraph 能够为 FGI 示例生成结构化计划。

    该测试证明四个节点已经通过真实的图边连接，而不是仅能单独调用。
    """
    final_state = run_example_graph(EXAMPLE_REQUEST)

    assert final_state.status == "planned"
    assert final_state.current_stage == "completed"
    assert final_state.errors == []
    assert final_state.reproduction_plan is not None
    assert len(final_state.reproduction_plan.steps) == 6

    assert final_state.normalized_request == (
        "请分析 FGI 论文仓库，并生成 DFDC 预训练模型推理复现计划，实际执行前必须人工审批。"
    )

    assert [event.node for event in final_state.trace] == [
        "normalize_request",
        "generate_plan",
        "validate_plan",
        "finalize",
    ]

    assert all(event.status == "success" for event in final_state.trace)


def test_graph_marks_execution_for_approval() -> None:
    """验证完整工作流生成的副作用步骤都要求人工审批。

    该测试防止规划器或校验节点允许系统未经授权执行外部命令。
    """
    final_state = run_example_graph(EXAMPLE_REQUEST)

    assert final_state.reproduction_plan is not None

    steps = final_state.reproduction_plan.steps
    side_effect_steps = [step for step in steps if step.tool in SIDE_EFFECT_TOOLS]

    assert side_effect_steps
    assert all(step.approval_required is True for step in side_effect_steps)

    approval_step_ids = [step.step_id for step in steps if step.tool == "human_approval"]

    assert approval_step_ids

    for execution_step in side_effect_steps:
        assert any(
            approval_step_id < execution_step.step_id for approval_step_id in approval_step_ids
        )


def test_graph_returns_structured_failure_for_empty_request() -> None:
    """验证空请求会完整经过工作流并返回结构化失败状态。

    该测试防止无效输入造成图执行崩溃或丢失节点 Trace。
    """
    final_state = run_example_graph("   \n\t  ")

    assert final_state.status == "failed"
    assert final_state.current_stage == "failed"
    assert final_state.reproduction_plan is None
    assert "用户请求不能为空。" in final_state.errors

    assert [event.node for event in final_state.trace] == [
        "normalize_request",
        "generate_plan",
        "validate_plan",
        "finalize",
    ]

    assert [event.status for event in final_state.trace] == [
        "error",
        "skipped",
        "skipped",
        "success",
    ]
