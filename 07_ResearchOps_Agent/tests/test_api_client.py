"""Streamlit 所使用的 FastAPI 客户端测试。"""

import json
from uuid import uuid4

import httpx
import pytest

from researchops.services import (
    ApiClientError,
    PlanningApiClient,
)


def build_success_payload() -> dict:
    """构造一个符合 TaskResponse 结构的成功响应。"""
    return {
        "task_id": str(uuid4()),
        "status": "planned",
        "reproduction_plan": {
            "objective": "完成 FGI 的 DFDC 预训练推理复现准备。",
            "assumptions": ["当前阶段只生成计划。"],
            "prerequisites": [
                "论文或 README",
                "仓库地址",
                "数据集与 checkpoint 信息",
            ],
            "steps": [
                {
                    "step_id": 1,
                    "title": "收集资产",
                    "description": "收集论文和仓库信息。",
                    "tool": "asset_collector",
                    "approval_required": False,
                    "expected_output": "资产清单。",
                },
                {
                    "step_id": 2,
                    "title": "执行推理",
                    "description": "执行经过批准的推理命令。",
                    "tool": "shell",
                    "approval_required": True,
                    "expected_output": "推理结果。",
                },
            ],
            "risks": ["checkpoint 可能不可用。"],
            "final_outputs": ["复现报告"],
        },
        "trace_summary": [
            "normalize_request: success",
            "generate_plan: success",
            "validate_plan: success",
            "finalize: success",
        ],
    }


def test_api_client_parses_success_response() -> None:
    """验证客户端能够解析 FastAPI 返回的成功响应。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/tasks/plan"

        request_payload = json.loads(request.content.decode("utf-8"))

        assert "FGI" in request_payload["user_request"]

        return httpx.Response(
            status_code=201,
            json=build_success_payload(),
        )

    client = PlanningApiClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )

    response = client.create_plan("请分析 FGI 并生成 DFDC 推理复现计划。")

    assert response.status == "planned"
    assert response.reproduction_plan is not None
    assert len(response.reproduction_plan.steps) == 2
    assert response.reproduction_plan.steps[1].approval_required is True


def test_api_client_rejects_blank_request_locally() -> None:
    """验证空白请求在发出网络调用前就会被拒绝。"""
    client = PlanningApiClient(
        base_url="http://testserver",
    )

    with pytest.raises(
        ApiClientError,
        match="请输入有效的论文复现需求",
    ) as exc_info:
        client.create_plan("   ")

    assert exc_info.value.error_code == "CLIENT_VALIDATION_ERROR"


def test_api_client_converts_api_error_response() -> None:
    """验证 FastAPI 结构化错误可以转换为页面可处理异常。"""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=422,
            json={
                "error_code": "PLANNING_ERROR",
                "message": "系统未能生成有效的论文复现计划。",
                "details": [
                    {
                        "field": None,
                        "message": "计划步骤为空。",
                        "error_type": None,
                    }
                ],
                "task_id": str(uuid4()),
            },
        )

    client = PlanningApiClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ApiClientError) as exc_info:
        client.create_plan("请生成论文复现计划。")

    error = exc_info.value

    assert error.error_code == "PLANNING_ERROR"
    assert error.task_id is not None
    assert "计划步骤为空。" in error.details


def test_api_client_handles_connection_failure() -> None:
    """验证后端不可用时客户端会返回可读的连接错误。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "Connection refused",
            request=request,
        )

    client = PlanningApiClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        ApiClientError,
        match="无法连接 FastAPI 服务",
    ) as exc_info:
        client.create_plan("请生成论文复现计划。")

    assert exc_info.value.error_code == "API_UNAVAILABLE"
