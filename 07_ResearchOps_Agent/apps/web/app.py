"""ResearchOps Agent 的 Streamlit 页面入口。

该页面只承担用户交互和结果展示职责：

1. 接收用户的论文复现需求；
2. 通过 PlanningApiClient 调用 FastAPI；
3. 展示结构化复现计划；
4. 明确标记需要人工审批的步骤；
5. 将连接错误和业务错误转换为可读提示。

页面不会直接导入或调用 LangGraph，确保前后端边界清晰。
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from researchops.core.config import get_settings
from researchops.schemas import TaskResponse
from researchops.services import (
    ApiClientError,
    PlanningApiClient,
)

DEFAULT_REQUEST = "请分析给定研究项目并生成复现准备计划，实际执行前必须人工审批。"


def get_api_client() -> PlanningApiClient:
    """创建调用 FastAPI 的客户端。

    客户端只保存 API 地址和超时配置，不保存具体任务状态，
    因此可以在页面每次重新执行时安全创建。
    """
    settings = get_settings()

    return PlanningApiClient(
        base_url=settings.api_base_url,
        timeout_seconds=30.0,
    )


def render_string_list(
    title: str,
    items: list[str],
    empty_message: str,
) -> None:
    """以统一格式展示字符串列表。

    Args:
        title: 页面中的小节标题。
        items: 需要展示的字符串项目。
        empty_message: 列表为空时展示的说明。
    """
    st.subheader(title)

    if not items:
        st.info(empty_message)
        return

    for item in items:
        st.markdown(f"- {item}")


def render_plan_steps(response: TaskResponse) -> None:
    """使用表格展示复现步骤，并突出人工审批边界。"""
    plan = response.reproduction_plan

    if plan is None:
        st.warning("当前响应中没有可展示的复现计划。")
        return

    st.subheader("执行步骤")

    step_rows: list[dict[str, Any]] = [
        {
            "序号": step.step_id,
            "步骤": step.title,
            "说明": step.description,
            "工具": step.tool,
            "需要人工审批": ("是" if step.approval_required else "否"),
            "预期产物": step.expected_output,
        }
        for step in plan.steps
    ]

    st.dataframe(
        step_rows,
        use_container_width=True,
        hide_index=True,
    )

    approval_steps = [step for step in plan.steps if step.approval_required]

    if approval_steps:
        approval_titles = "、".join(
            f"步骤 {step.step_id}「{step.title}」" for step in approval_steps
        )

        st.warning(f"以下步骤不会自动执行，必须先获得人工审批：{approval_titles}")
    else:
        st.info("当前计划中没有需要人工审批的步骤。")


def render_task_response(response: TaskResponse) -> None:
    """完整展示 FastAPI 返回的论文复现计划。"""
    st.success("复现计划生成成功。")

    left_column, right_column = st.columns(2)

    with left_column:
        st.metric(
            label="任务状态",
            value=response.status,
        )

    with right_column:
        st.metric(
            label="计划步骤数",
            value=(len(response.reproduction_plan.steps) if response.reproduction_plan else 0),
        )

    st.caption("任务编号")
    st.code(str(response.task_id), language=None)

    plan = response.reproduction_plan

    if plan is None:
        st.warning("FastAPI 未返回有效的复现计划。")
        return

    st.subheader("复现目标")
    st.write(plan.objective)

    render_string_list(
        title="前置条件",
        items=plan.prerequisites,
        empty_message="当前计划未声明前置条件。",
    )

    render_string_list(
        title="规划假设",
        items=plan.assumptions,
        empty_message="当前计划未声明额外假设。",
    )

    render_plan_steps(response)

    render_string_list(
        title="已识别风险",
        items=plan.risks,
        empty_message="当前计划未记录风险。",
    )

    render_string_list(
        title="最终产物",
        items=plan.final_outputs,
        empty_message="当前计划未声明最终产物。",
    )

    with st.expander("查看工作流 Trace"):
        for trace_item in response.trace_summary:
            st.code(trace_item, language=None)


def render_api_error(error_payload: dict[str, Any]) -> None:
    """展示经过客户端转换的安全错误信息。"""
    error_code = error_payload.get(
        "error_code",
        "API_CLIENT_ERROR",
    )
    message = error_payload.get(
        "message",
        "请求处理失败。",
    )
    task_id = error_payload.get("task_id")
    details = error_payload.get("details", [])

    st.error(f"{error_code}：{message}")

    if task_id:
        st.caption("失败任务编号")
        st.code(str(task_id), language=None)

    if details:
        with st.expander("查看错误详情"):
            for detail in details:
                st.markdown(f"- {detail}")


def main() -> None:
    """渲染 ResearchOps Agent 的单页主流程。"""
    settings = get_settings()

    st.set_page_config(
        page_title=settings.app_name,
        page_icon="🧪",
        layout="wide",
    )

    st.title("🧪 ResearchOps Agent")
    st.caption("将论文复现需求转换为结构化、可验证且包含人工审批边界的执行计划。")

    st.info(
        "Day 1 使用 RuleBasedPlanner 生成计划。系统当前不会下载数据、修改环境或实际执行推理命令。"
    )

    with st.sidebar:
        st.header("服务信息")
        st.write(f"API 地址：`{settings.api_base_url}`")
        st.write(f"应用版本：`{settings.app_version}`")

        st.divider()

        st.header("当前边界")
        st.markdown(
            """
- 不解析真实论文 PDF
- 不读取真实 GitHub 仓库
- 不连接 MySQL 或 Redis
- 不执行 shell、Docker 或 GPU 任务
- 所有执行类步骤必须人工审批
"""
        )

    st.subheader("提交复现需求")

    with st.form("reproduction_plan_form"):
        user_request = st.text_area(
            label="论文复现需求",
            value=DEFAULT_REQUEST,
            height=150,
            max_chars=4000,
            help=("请说明论文或项目名称、目标数据集、需要复现的阶段以及审批要求。"),
        )

        submitted = st.form_submit_button(
            "生成复现计划",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        client = get_api_client()

        with st.spinner("正在调用 FastAPI 并生成复现计划……"):
            try:
                response = client.create_plan(user_request)
            except ApiClientError as exc:
                # session_state 中只保存可序列化数据，
                # 避免直接保存异常对象导致页面重载问题。
                st.session_state["last_error"] = {
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "task_id": exc.task_id,
                    "details": exc.details,
                }
                st.session_state.pop(
                    "last_response",
                    None,
                )
            else:
                st.session_state["last_response"] = response.model_dump(mode="json")
                st.session_state.pop(
                    "last_error",
                    None,
                )

    last_error = st.session_state.get("last_error")

    if last_error:
        st.divider()
        render_api_error(last_error)

    last_response = st.session_state.get("last_response")

    if last_response:
        st.divider()

        # 从 session_state 恢复数据时重新经过 Pydantic 校验，
        # 防止页面持久化数据结构与最新模型定义不一致。
        response = TaskResponse.model_validate(last_response)

        render_task_response(response)


if __name__ == "__main__":
    main()
