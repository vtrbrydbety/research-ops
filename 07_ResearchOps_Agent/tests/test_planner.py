"""RuleBasedPlanner 规则规划器测试。"""

import pytest

from researchops.services import RuleBasedPlanner

EXAMPLE_REQUEST = "请分析 FGI 论文仓库并生成 DFDC 预训练模型推理复现计划，实际执行前必须人工审批。"


def test_rule_based_planner_generates_required_steps() -> None:
    """验证规则规划器能够生成顺序完整的六步复现计划。

    该测试防止规划器遗漏 Day 1 文档规定的关键阶段。
    """
    planner = RuleBasedPlanner()

    plan = planner.generate_plan(EXAMPLE_REQUEST)

    assert len(plan.steps) == 6
    assert [step.step_id for step in plan.steps] == [1, 2, 3, 4, 5, 6]

    titles = [step.title for step in plan.steps]

    assert "收集论文与仓库资产" in titles
    assert "分析运行环境依赖" in titles
    assert "检查数据集与 checkpoint" in titles
    assert "生成预训练推理命令" in titles
    assert "人工审批执行方案" in titles
    assert "执行推理并生成结果报告" in titles


def test_rule_based_planner_marks_execution_for_approval() -> None:
    """验证执行命令和人工审批步骤都被标记为需要批准。

    该测试防止系统在没有用户授权的情况下进入具有副作用的执行阶段。
    """
    planner = RuleBasedPlanner()

    plan = planner.generate_plan(EXAMPLE_REQUEST)

    approval_step = next(step for step in plan.steps if step.tool == "human_approval")
    execution_step = next(step for step in plan.steps if step.tool == "shell")

    assert approval_step.approval_required is True
    assert execution_step.approval_required is True


def test_rule_based_planner_rejects_empty_request() -> None:
    """验证空的标准化请求会触发明确错误。

    该测试防止规划器为无效输入生成没有实际意义的固定计划。
    """
    planner = RuleBasedPlanner()

    with pytest.raises(ValueError, match="标准化请求不能为空"):
        planner.generate_plan("   ")
