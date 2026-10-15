"""论文复现规划工作流节点。

该模块实现 Day 1 最小 LangGraph 所需的四个节点：

1. normalize_request：规范化用户请求；
2. generate_plan：调用规划服务生成结构化计划；
3. validate_plan：检查计划结构与人工审批边界；
4. finalize：汇总任务最终状态。

节点只处理共享状态和业务服务，不直接依赖 FastAPI、Streamlit、
数据库连接或 shell 命令。
"""

import re

from researchops.core.logging import get_logger
from researchops.services import PlannerService
from researchops.states import (
    AgentState,
    AgentStateUpdate,
    TraceEvent,
    TraceStatus,
)

# 这些工具会改变外部环境，因此对应步骤必须明确要求人工审批。
SIDE_EFFECT_TOOLS = frozenset(
    {
        "shell",
        "docker",
        "gpu",
        "file_writer",
        "database_writer",
        "download",
    }
)


class PlanningNodes:
    """论文复现规划节点集合。

    通过构造函数注入 PlannerService，使节点只依赖抽象接口。
    测试时可以使用 RuleBasedPlanner，未来也可以替换为 LLMPlanner。
    """

    def __init__(self, planner: PlannerService) -> None:
        """保存工作流使用的计划生成服务。"""
        self.planner = planner

    @staticmethod
    def _append_trace(
        state: AgentState,
        node: str,
        status: TraceStatus,
        summary: str,
    ) -> list[TraceEvent]:
        """在现有 Trace 后追加一条事件并返回新列表。

        不直接修改 state.trace，避免节点产生难以追踪的原地副作用。
        """
        return [
            *state.trace,
            TraceEvent(
                node=node,
                status=status,
                summary=summary,
            ),
        ]

    def normalize_request(
        self,
        state: AgentState,
    ) -> AgentStateUpdate:
        """清理用户请求中的多余空白并生成标准化请求。

        空请求不会抛出原始 Python 异常，而是写入 errors 和 Trace，
        由后续节点跳过处理，最后统一形成失败状态。
        """
        logger = get_logger(
            component="normalize_request",
            task_id=str(state.task_id),
        )

        # 先将连续空格、换行和制表符统一压缩为一个普通空格。
        normalized_request = " ".join(state.user_request.split())

        # 删除中文标点前多余的空格，例如“仓库 ，”修正为“仓库，”。
        normalized_request = re.sub(
            r"\s+([，。！？；：、])",
            r"\1",
            normalized_request,
        )

        # 当中文标点后仍然是中文字符时，删除中间空格。
        #    例如“仓库， 并生成”修正为“仓库，并生成”。
        normalized_request = re.sub(
            r"([，。！？；：、])\s+(?=[\u4e00-\u9fff])",
            r"\1",
            normalized_request,
        )

        if not normalized_request:
            error_message = "用户请求不能为空。"

            logger.warning(error_message)

            return {
                "normalized_request": None,
                "current_stage": "normalize_request",
                "status": "failed",
                "errors": [*state.errors, error_message],
                "trace": self._append_trace(
                    state=state,
                    node="normalize_request",
                    status="error",
                    summary=error_message,
                ),
            }

        logger.info("用户请求规范化完成")

        return {
            "normalized_request": normalized_request,
            "current_stage": "normalize_request",
            "status": "planning",
            "trace": self._append_trace(
                state=state,
                node="normalize_request",
                status="success",
                summary="用户请求已经完成空白清理和标准化。",
            ),
        }

    def generate_plan(
        self,
        state: AgentState,
    ) -> AgentStateUpdate:
        """调用 PlannerService 生成结构化论文复现计划。"""
        logger = get_logger(
            component="generate_plan",
            task_id=str(state.task_id),
        )

        # 上游已经失败时不继续调用规划器，避免产生无意义的后续异常。
        if state.errors or not state.normalized_request:
            logger.warning("因上游状态无效，跳过复现计划生成")

            return {
                "current_stage": "generate_plan",
                "status": "failed",
                "trace": self._append_trace(
                    state=state,
                    node="generate_plan",
                    status="skipped",
                    summary="由于请求规范化失败，已跳过复现计划生成。",
                ),
            }

        try:
            reproduction_plan = self.planner.generate_plan(state.normalized_request)
        except ValueError as exc:
            # 可预期的规划错误可以向用户返回经过整理的具体原因。
            error_message = f"复现计划生成失败：{exc}"

            logger.warning(error_message)

            return {
                "reproduction_plan": None,
                "current_stage": "generate_plan",
                "status": "failed",
                "errors": [*state.errors, error_message],
                "trace": self._append_trace(
                    state=state,
                    node="generate_plan",
                    status="error",
                    summary=error_message,
                ),
            }
        except Exception:
            # 未知异常的完整堆栈只进入日志，不直接暴露给用户。
            error_message = "复现计划生成失败，请检查规划器运行日志。"

            logger.exception(error_message)

            return {
                "reproduction_plan": None,
                "current_stage": "generate_plan",
                "status": "failed",
                "errors": [*state.errors, error_message],
                "trace": self._append_trace(
                    state=state,
                    node="generate_plan",
                    status="error",
                    summary=error_message,
                ),
            }

        logger.info("结构化复现计划生成完成")

        return {
            "reproduction_plan": reproduction_plan,
            "current_stage": "generate_plan",
            "status": "planning",
            "trace": self._append_trace(
                state=state,
                node="generate_plan",
                status="success",
                summary=(f"规划器已生成包含 {len(reproduction_plan.steps)} 个步骤的复现计划。"),
            ),
        }

    def validate_plan(
        self,
        state: AgentState,
    ) -> AgentStateUpdate:
        """校验复现计划的完整性、顺序和人工审批边界。"""
        logger = get_logger(
            component="validate_plan",
            task_id=str(state.task_id),
        )

        if state.errors:
            logger.warning("因上游节点失败，跳过复现计划校验")

            return {
                "current_stage": "validate_plan",
                "status": "failed",
                "trace": self._append_trace(
                    state=state,
                    node="validate_plan",
                    status="skipped",
                    summary="由于上游节点失败，已跳过复现计划校验。",
                ),
            }

        if state.reproduction_plan is None:
            error_message = "没有可供校验的复现计划。"

            logger.warning(error_message)

            return {
                "current_stage": "validate_plan",
                "status": "failed",
                "errors": [*state.errors, error_message],
                "trace": self._append_trace(
                    state=state,
                    node="validate_plan",
                    status="error",
                    summary=error_message,
                ),
            }

        plan = state.reproduction_plan
        validation_errors: list[str] = []

        if not plan.steps:
            validation_errors.append("复现计划至少需要包含一个步骤。")

        # 步骤编号必须从 1 开始连续递增，避免页面展示和执行顺序产生歧义。
        actual_step_ids = [step.step_id for step in plan.steps]
        expected_step_ids = list(range(1, len(plan.steps) + 1))

        if actual_step_ids != expected_step_ids:
            validation_errors.append("计划步骤编号必须从 1 开始连续递增。")

        human_approval_step_ids = [
            step.step_id for step in plan.steps if step.tool == "human_approval"
        ]

        for step in plan.steps:
            if step.tool in SIDE_EFFECT_TOOLS and not step.approval_required:
                validation_errors.append(
                    f"步骤 {step.step_id} 使用工具 {step.tool}，但没有设置人工审批。"
                )

            if step.tool == "human_approval" and not step.approval_required:
                validation_errors.append(
                    f"人工审批步骤 {step.step_id} 必须设置 approval_required=True。"
                )

            # 对 shell 等执行步骤，还要求计划中存在位于它之前的人工审批步骤。
            if step.tool in SIDE_EFFECT_TOOLS:
                has_prior_approval = any(
                    approval_step_id < step.step_id for approval_step_id in human_approval_step_ids
                )

                if not has_prior_approval:
                    validation_errors.append(f"执行步骤 {step.step_id} 之前缺少人工审批步骤。")

        if validation_errors:
            logger.warning(
                "复现计划校验失败，共发现 %s 个问题",
                len(validation_errors),
            )

            return {
                "current_stage": "validate_plan",
                "status": "failed",
                "errors": [*state.errors, *validation_errors],
                "trace": self._append_trace(
                    state=state,
                    node="validate_plan",
                    status="error",
                    summary=(f"复现计划校验失败，共发现 {len(validation_errors)} 个问题。"),
                ),
            }

        logger.info("复现计划校验通过")

        return {
            "current_stage": "validate_plan",
            "status": "planning",
            "trace": self._append_trace(
                state=state,
                node="validate_plan",
                status="success",
                summary="计划结构、步骤顺序和人工审批边界校验通过。",
            ),
        }

    def finalize(
        self,
        state: AgentState,
    ) -> AgentStateUpdate:
        """根据计划和错误信息确定任务最终状态。"""
        logger = get_logger(
            component="finalize",
            task_id=str(state.task_id),
        )

        task_failed = bool(state.errors) or state.reproduction_plan is None

        if task_failed:
            logger.warning(
                "任务规划以失败状态结束，共记录 %s 个错误",
                len(state.errors),
            )

            return {
                "current_stage": "failed",
                "status": "failed",
                "trace": self._append_trace(
                    state=state,
                    node="finalize",
                    status="success",
                    summary=(f"工作流已完成失败状态汇总，共记录 {len(state.errors)} 个错误。"),
                ),
            }

        logger.info("任务规划成功完成")

        return {
            "current_stage": "completed",
            "status": "planned",
            "trace": self._append_trace(
                state=state,
                node="finalize",
                status="success",
                summary="复现计划已经完成生成、校验和最终汇总。",
            ),
        }
