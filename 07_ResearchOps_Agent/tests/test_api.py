"""ResearchOps Agent FastAPI 接口测试。"""

from uuid import UUID

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


EXAMPLE_REQUEST = {
    "user_request": (
        "请分析 FGI 论文仓库并生成 DFDC 预训练模型推理复现计划，实际执行前必须人工审批。"
    )
}


def test_health_endpoint() -> None:
    """验证健康检查接口返回服务状态和版本号。"""
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["service"] == "ResearchOps Agent"
    assert payload["status"] == "ok"
    assert payload["version"] == "0.1.0"


def test_plan_endpoint() -> None:
    """验证核心接口能够创建 task_id 并返回六步复现计划。"""
    response = client.post(
        "/api/v1/tasks/plan",
        json=EXAMPLE_REQUEST,
    )

    assert response.status_code == 201

    payload = response.json()

    # UUID 构造成功即证明接口返回了合法的 task_id。
    UUID(payload["task_id"])

    assert payload["status"] == "planned"
    assert payload["reproduction_plan"] is not None
    assert len(payload["reproduction_plan"]["steps"]) == 6
    assert len(payload["trace_summary"]) == 4

    shell_step = next(
        step for step in payload["reproduction_plan"]["steps"] if step["tool"] == "shell"
    )

    assert shell_step["approval_required"] is True


def test_plan_endpoint_rejects_blank_request() -> None:
    """验证空白 user_request 会返回统一的校验错误响应。"""
    response = client.post(
        "/api/v1/tasks/plan",
        json={"user_request": "   "},
    )

    assert response.status_code == 422

    payload = response.json()

    assert payload["error_code"] == "VALIDATION_ERROR"
    assert payload["message"] == "请求参数校验失败。"
    assert payload["task_id"] is None
    assert payload["details"]


def test_plan_endpoint_rejects_unknown_field() -> None:
    """验证未声明字段会被拒绝，防止字段拼写错误被静默忽略。"""
    response = client.post(
        "/api/v1/tasks/plan",
        json={
            **EXAMPLE_REQUEST,
            "unknown_field": "不应被接受",
        },
    )

    assert response.status_code == 422

    payload = response.json()

    assert payload["error_code"] == "VALIDATION_ERROR"
    assert any(detail["error_type"] == "extra_forbidden" for detail in payload["details"])
