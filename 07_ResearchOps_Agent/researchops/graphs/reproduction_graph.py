"""论文复现规划 LangGraph 的构建与调用模块。

该模块负责将四个独立规划节点连接成一条可执行工作流：

START
→ normalize_request
→ generate_plan
→ validate_plan
→ finalize
→ END

节点内部只处理业务状态；图构建模块负责节点注册、边连接和编译。
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from researchops.nodes import PlanningNodes
from researchops.services import PlannerService, RuleBasedPlanner
from researchops.states import AgentState


def build_reproduction_graph(
    planner: PlannerService | None = None,
) -> CompiledStateGraph:
    """构建并编译论文复现规划工作流。

    Args:
        planner: 可选的计划生成服务。未传入时使用 RuleBasedPlanner。

    Returns:
        已完成节点注册、边连接和编译的 LangGraph。
    """
    planner_service = planner or RuleBasedPlanner()
    nodes = PlanningNodes(planner_service)

    # StateGraph 负责维护各节点共享的 AgentState。
    graph_builder = StateGraph(AgentState)

    # 显式指定节点名称，确保 Trace、测试输出和后续可视化保持稳定。
    graph_builder.add_node(
        "normalize_request",
        nodes.normalize_request,
    )
    graph_builder.add_node(
        "generate_plan",
        nodes.generate_plan,
    )
    graph_builder.add_node(
        "validate_plan",
        nodes.validate_plan,
    )
    graph_builder.add_node(
        "finalize",
        nodes.finalize,
    )

    # Day 1 使用最简单的线性流程。
    # 即使上游失败，后续节点也会以 skipped 状态留下完整 Trace。
    graph_builder.add_edge(START, "normalize_request")
    graph_builder.add_edge("normalize_request", "generate_plan")
    graph_builder.add_edge("generate_plan", "validate_plan")
    graph_builder.add_edge("validate_plan", "finalize")
    graph_builder.add_edge("finalize", END)

    # StateGraph 只是构建器，必须编译后才能调用 invoke。
    return graph_builder.compile()


def invoke_reproduction_graph(
    graph: CompiledStateGraph,
    initial_state: AgentState,
) -> AgentState:
    """调用已编译工作流并返回经过校验的最终 AgentState。

    LangGraph 使用 Pydantic 作为状态模式时，最终 invoke 结果仍然是字典。
    因此在工作流边界统一执行 model_validate，避免 API 层重复转换。

    Args:
        graph: 已通过 build_reproduction_graph 编译的工作流。
        initial_state: 包含 task_id 和用户请求的初始状态。

    Returns:
        经过 Pydantic 校验的最终工作流状态。
    """
    result = graph.invoke(initial_state)

    return AgentState.model_validate(result)
