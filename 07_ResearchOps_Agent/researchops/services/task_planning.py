"""任务规划应用服务。

该服务位于 FastAPI 和 LangGraph 之间，负责：

1. 创建全局唯一的 task_id；
2. 构造 LangGraph 初始状态；
3. 调用论文复现规划工作流；
4. 将内部 AgentState 转换为公共 TaskResponse；
5. 将工作流失败转换为统一业务异常。

这样可以避免把业务编排逻辑直接写入 FastAPI 路由。
"""

from uuid import UUID, uuid4

from langgraph.graph.state import CompiledStateGraph

from researchops.core.logging import get_logger
from researchops.graphs import (
    build_reproduction_graph,
    invoke_reproduction_graph,
)
from researchops.schemas import TaskRequest, TaskResponse
from researchops.states import AgentState


class TaskPlanningError(RuntimeError):
    """任务规划失败时抛出的结构化业务异常。"""

    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        task_id: UUID,
        details: list[str] | None = None,
    ) -> None:
        """保存 API 错误响应所需的安全信息。"""
        super().__init__(message)

        self.error_code = error_code
        self.message = message
        self.task_id = task_id
        self.details = details or []


class TaskPlanningService:
    """负责创建并执行论文复现规划任务。"""

    def __init__(
        self,
        graph: CompiledStateGraph | None = None,
    ) -> None:
        """初始化任务服务并复用已经编译的 LangGraph。

        图只需要编译一次。后续每个请求会创建独立的 AgentState，
        不会在请求之间共享任务状态。
        """
        self.graph = graph or build_reproduction_graph()

    def create_plan(
        self,
        request: TaskRequest,
    ) -> TaskResponse:
        """创建并执行一次论文复现规划任务。

        Args:
            request: 已通过 Pydantic 校验的用户请求。

        Returns:
            包含 task_id、计划和 Trace 摘要的任务响应。

        Raises:
            TaskPlanningError: 当图执行异常或无法生成有效计划时抛出。
        """
        task_id = uuid4()
        logger = get_logger(
            component="task_planning_service",
            task_id=str(task_id),
        )

        logger.info("开始创建论文复现规划任务")

        initial_state = AgentState(
            task_id=task_id,
            user_request=request.user_request,
        )

        try:
            final_state = invoke_reproduction_graph(
                graph=self.graph,
                initial_state=initial_state,
            )
        except Exception as exc:
            # 未知异常的完整堆栈只写入服务端日志，
            # API 调用方只能获得安全的错误摘要。
            logger.exception("LangGraph 执行过程中发生未知异常")

            raise TaskPlanningError(
                error_code="INTERNAL_ERROR",
                message="任务规划工作流执行失败。",
                task_id=task_id,
                details=["请检查服务端日志以获取详细信息。"],
            ) from exc

        if final_state.status != "planned" or final_state.reproduction_plan is None:
            logger.warning(
                "工作流未生成有效复现计划，共记录 %s 个错误",
                len(final_state.errors),
            )

            raise TaskPlanningError(
                error_code="PLANNING_ERROR",
                message="系统未能生成有效的论文复现计划。",
                task_id=task_id,
                details=final_state.errors,
            )

        # 对外只返回可读的 Trace 摘要，不直接暴露内部状态对象。
        trace_summary = [
            (f"{event.node}: {event.status} - {event.summary}") for event in final_state.trace
        ]

        logger.info("论文复现规划任务创建完成")

        return TaskResponse(
            task_id=task_id,
            status=final_state.status,
            reproduction_plan=final_state.reproduction_plan,
            trace_summary=trace_summary,
        )
