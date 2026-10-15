"""Exercise the real API behind the public perimeter without production state."""

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api
from researchops.core.access_middleware import COOKIE_NAME, AccessMiddleware
from researchops.core.config import Settings
from researchops.services.access_store import AccessStore

ORIGIN = "https://researchops-agent.com"


@pytest.fixture
def public_app(tmp_path, monkeypatch):
    config = Settings(_env_file=None, deployment_mode="public", security_store_dir=tmp_path / "s")
    store = AccessStore(config)
    monkeypatch.setattr(api, "settings", config)
    monkeypatch.setattr(api.app.state, "access_store", store, raising=False)
    wrapped = AccessMiddleware(api.app, settings=config, store_provider=lambda: store)
    client = TestClient(wrapped, base_url=ORIGIN, client=("127.0.0.1", 50000))
    yield client, store
    client.close()


def login(client, store, label="alice"):
    principal, code = store.create_invitation(label)
    response = client.post(
        "/api/v1/access/sessions", json={"invitation_code": code}, headers={"Origin": ORIGIN}
    )
    assert response.status_code == 200, response.text
    return principal, response.json()["csrf_token"]


def test_business_routes_are_protected_before_execution(public_app):
    client, store = public_app
    endpoints = [
        ("POST", "/api/v1/targets/resolve"),
        ("POST", "/api/v1/tasks/plan"),
        ("POST", "/api/v1/assessments"),
        ("POST", "/api/v1/assessment-jobs"),
        ("GET", "/api/v1/assessment-jobs/unknown"),
        ("GET", "/api/v1/assessments/unknown"),
        ("POST", "/api/v1/environment-authorizations"),
    ]
    for method, path in endpoints:
        assert client.request(method, path).status_code == 401
    assert client.get("/mvp/").status_code == 200
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404


def test_secure_cookie_csrf_logout_and_revoke(public_app):
    client, store = public_app
    principal, csrf = login(client, store)
    cookie = client.cookies.get(COOKIE_NAME)
    assert client.get("/api/v1/access/session").json()["principal_id"] == principal
    assert (
        client.post("/api/v1/targets/resolve", json={}, headers={"Origin": ORIGIN}).status_code
        == 403
    )
    assert (
        client.delete(
            "/api/v1/access/session", headers={"Origin": "https://evil.test", "X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    response = client.delete(
        "/api/v1/access/session", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    client.cookies.set(COOKIE_NAME, cookie)
    assert client.get("/api/v1/access/session").status_code == 401
    client.cookies.clear()
    principal, _ = login(client, store, "bob")
    store.update_invitation(principal, revoke=True)
    assert client.get("/api/v1/access/session").status_code == 401


def test_login_rejects_cross_origin_and_is_limited(public_app):
    client, store = public_app
    store.settings.login_ip_limit = 1
    payload = {"invitation_code": "x" * 43}
    assert client.post("/api/v1/access/sessions", json=payload).status_code == 403
    assert (
        client.post("/api/v1/access/sessions", json=payload, headers={"Origin": ORIGIN}).status_code
        == 401
    )
    response = client.post("/api/v1/access/sessions", json=payload, headers={"Origin": ORIGIN})
    assert response.status_code == 429 and "retry-after" in response.headers


def test_untrusted_forwarded_headers_do_not_change_login_limit(public_app):
    _, store = public_app
    store.settings.login_ip_limit = 1
    wrapped = AccessMiddleware(api.app, settings=store.settings, store_provider=lambda: store)
    with TestClient(wrapped, base_url=ORIGIN, client=("198.51.100.9", 50000)) as client:
        for index, expected in [(1, 401), (2, 429)]:
            response = client.post(
                "/api/v1/access/sessions",
                json={"invitation_code": "x" * 43},
                headers={
                    "Origin": ORIGIN,
                    "CF-Connecting-IP": f"8.8.8.{index}",
                    "X-Forwarded-For": f"9.9.9.{index}",
                },
            )
            assert response.status_code == expected


def test_response_headers_and_streamed_body_limit(public_app):
    client, store = public_app
    response = client.get("/mvp/")
    assert response.headers["cache-control"] == "no-store"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    store.settings.request_max_bytes = 1024

    def stream():
        yield b"x" * 600
        yield b"x" * 600

    response = client.post("/api/v1/targets/resolve", content=stream())
    assert response.status_code == 413
    assert client.get("/health", headers={"Host": "evil.test"}).status_code == 400


def test_database_failure_does_not_bypass_authentication(public_app):
    client, store = public_app
    store.path.unlink()
    response = client.post("/api/v1/assessments", json={})
    assert response.status_code == 503
    assert response.json()["error_code"] == "SECURITY_UNAVAILABLE"


def test_assessment_resource_isolation_and_legacy_default_deny(public_app, monkeypatch):
    from researchops.services.human_review import InMemoryAssessmentReviewStore
    from tests.test_assessment_jobs import completed_assessment

    client, store = public_app
    service = api.readiness_workflow_service
    review = service.human_review_service
    monkeypatch.setattr(review, "store", InMemoryAssessmentReviewStore())
    assessment = completed_assessment()
    monkeypatch.setattr(
        service, "create_assessment", lambda request: review.register({"assessment": assessment})
    )
    principal, csrf = login(client, store)
    request = {
        "target_type": "repository",
        "target_entry": "https://github.com/example/project",
        "environment_mode": "later",
    }
    response = client.post(
        "/api/v1/assessments", json=request, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}
    )
    assert response.status_code == 201, response.text
    assessment_id = response.json()["assessment_id"]
    assert client.get(f"/api/v1/assessments/{assessment_id}").status_code == 200
    pending = store.reserve(principal)
    for path, body in [
        ("/api/v1/assessments", request),
        ("/api/v1/assessment-jobs", request),
        (
            f"/api/v1/assessments/{assessment_id}/feedback",
            {"target_type": "finding", "target_id": "anything", "action": "accept"},
        ),
    ]:
        assert (
            client.post(
                path, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}
            ).status_code
            == 429
        )
    store.finish(pending, "failed")
    client.cookies.clear()
    _, other_csrf = login(client, store, "bob")
    for method, suffix, body in [
        ("GET", "", None),
        ("GET", "/revisions", None),
        (
            "POST",
            "/feedback",
            {"target_type": "finding", "target_id": "anything", "action": "accept"},
        ),
        ("POST", "/final-decision", {"decision": "decline", "rationale": "private"}),
    ]:
        response = client.request(
            method,
            f"/api/v1/assessments/{assessment_id}{suffix}",
            json=body,
            headers={"Origin": ORIGIN, "X-CSRF-Token": other_csrf},
        )
        assert response.status_code == 404, response.text
    assert (
        client.post(
            "/api/v1/environment-authorizations",
            json={},
            headers={"Origin": ORIGIN, "X-CSRF-Token": other_csrf},
        ).status_code
        == 403
    )

    request["environment_mode"] = "readonly"
    assert (
        client.post(
            "/api/v1/assessments",
            json=request,
            headers={"Origin": ORIGIN, "X-CSRF-Token": other_csrf},
        ).status_code
        == 403
    )


@pytest.mark.parametrize("failure_target", ["review", "owner"])
def test_partial_result_write_is_not_published(public_app, monkeypatch, failure_target):
    from tests.test_assessment_jobs import completed_assessment

    client, store = public_app
    review = api.readiness_workflow_service.human_review_service
    assessment = completed_assessment()

    def fail(*args, **kwargs):
        raise OSError("synthetic storage failure")

    if failure_target == "review":
        monkeypatch.setattr(review.store, "save", fail)
    else:
        monkeypatch.setattr(store, "bind", fail)
    monkeypatch.setattr(
        api.readiness_workflow_service,
        "create_assessment",
        lambda request: review.register({"assessment": assessment}),
    )
    principal, csrf = login(client, store)
    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": "https://github.com/example/project",
            "environment_mode": "later",
        },
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )
    assert response.status_code == 500
    assert client.get(f"/api/v1/assessments/{assessment.assessment_id}").status_code == 404


def test_real_public_workflow_accounts_parallel_models_feedback_and_isolation(
    public_app, monkeypatch, tmp_path
):
    from researchops.services.assessment_jobs import AssessmentJobService
    from researchops.testing.public_workflow import controlled_workflow

    client, store = public_app
    store.settings.assessment_review_store_dir = tmp_path / "reviews"
    workflow, provider = controlled_workflow(store.settings)
    monkeypatch.setattr(api, "readiness_workflow_service", workflow)
    monkeypatch.setattr(api, "assessment_job_service", AssessmentJobService(workflow))
    alice, csrf = login(client, store)
    alice_cookie = client.cookies.get(COOKIE_NAME)
    headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
    response = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "target_type": "repository",
            "target_entry": "https://github.com/example/project",
            "environment_mode": "later",
        },
    )
    assert response.status_code == 201, response.text
    assessment = response.json()
    assert assessment["status"] == "completed" and assessment["gate_available"]
    assert len(provider.calls) == 10  # Context & Gap + nine condition drafts.
    initial_operation = provider.calls[0][2]
    assert {call[1] for call in provider.calls} == {alice}
    assert {call[2] for call in provider.calls} == {initial_operation}
    assert len({call[3] for call in provider.calls}) >= 2  # Includes local Draft pool.
    assert store.operation(initial_operation)["attempts"] == 10
    assessment_id = assessment["assessment_id"]
    finding = assessment["dimensions"][0]["findings"][0]
    response = client.post(
        f"/api/v1/assessments/{assessment_id}/feedback",
        headers=headers,
        json={
            "target_type": "finding",
            "target_id": finding["finding_id"],
            "action": "supplement",
            "comment": "Add a controlled source for the selected condition.",
            "source_submission": {
                "material_type": "Other",
                "title": "User clarification",
                "source_path": "user/clarification.txt",
                "content": "Access still needs confirmation.",
            },
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["reassessment_performed"] is True
    assert len(provider.calls) == 12
    assert store.operation(provider.calls[-1][2])["attempts"] == 2
    response = client.post(
        f"/api/v1/assessments/{assessment_id}/final-decision",
        headers=headers,
        json={"decision": "decline", "rationale": "Controlled acceptance."},
    )
    assert response.status_code == 201, response.text
    assert response.json()["rule_gate_at_decision"] == assessment["overall_gate"]
    assert (
        len(client.get(f"/api/v1/assessments/{assessment_id}/revisions").json()["revisions"]) == 2
    )
    client.cookies.clear()
    _, bob_csrf = login(client, store, "bob")
    for method, suffix, body in [
        ("GET", "", None),
        ("GET", "/revisions", None),
        (
            "POST",
            "/feedback",
            {"target_type": "finding", "target_id": finding["finding_id"], "action": "accept"},
        ),
        ("POST", "/final-decision", {"decision": "decline", "rationale": "Forbidden."}),
    ]:
        response = client.request(
            method,
            f"/api/v1/assessments/{assessment_id}{suffix}",
            json=body,
            headers={"Origin": ORIGIN, "X-CSRF-Token": bob_csrf},
        )
        assert response.status_code == 404
    assert len(provider.calls) == 12
    # A new operation with only two HTTP attempts must stop the condition pool.
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, alice_cookie)
    store.settings.operation_model_attempts = 2
    response = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "target_type": "repository",
            "target_entry": "https://github.com/example/project",
            "environment_mode": "later",
        },
    )
    assert response.status_code == 429, response.text
    assert response.json()["error_code"] == "BUDGET_EXHAUSTED"
    assert len(provider.calls) == 14
    assert store.operation(provider.calls[-1][2])["attempts"] == 2
