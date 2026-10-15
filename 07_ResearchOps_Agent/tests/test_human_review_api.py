"""HTTP contract tests for the Step 9/10 Human review and progress endpoints."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api import main as api_main
from researchops.schemas import AssessmentJobResponse
from researchops.services import DurableAssessmentReviewStore

client = TestClient(api_main.app)


def test_api_uses_recoverable_review_store() -> None:
    store = api_main.readiness_workflow_service.human_review_service.store

    assert isinstance(store, DurableAssessmentReviewStore)
    assert store.ttl_seconds == 86_400.0


class StubAssessmentJobService:
    def __init__(self) -> None:
        self.snapshot = AssessmentJobResponse(
            job_id=uuid4(),
            state="queued",
            phase="queued",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.request = None

    def start(self, request):
        self.request = request
        return self.snapshot

    def get(self, job_id):
        assert job_id == self.snapshot.job_id
        return self.snapshot


def test_feedback_for_missing_or_expired_assessment_returns_404() -> None:
    response = client.post(
        f"/api/v1/assessments/{uuid4()}/feedback",
        json={
            "target_type": "evidence",
            "target_id": "e-missing",
            "action": "accept",
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "ASSESSMENT_REVIEW_NOT_FOUND"


def test_read_latest_missing_or_expired_assessment_returns_404() -> None:
    response = client.get(f"/api/v1/assessments/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "ASSESSMENT_REVIEW_NOT_FOUND"


def test_supplement_requires_source_material_and_explanation() -> None:
    response = client.post(
        f"/api/v1/assessments/{uuid4()}/feedback",
        json={
            "target_type": "evidence",
            "target_id": "e-missing",
            "action": "supplement",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_question_requires_an_explanation() -> None:
    response = client.post(
        f"/api/v1/assessments/{uuid4()}/feedback",
        json={
            "target_type": "finding",
            "target_id": "f-missing",
            "action": "question",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_assessment_job_endpoints_start_and_return_the_same_job(monkeypatch) -> None:
    service = StubAssessmentJobService()
    monkeypatch.setattr(api_main, "assessment_job_service", service)

    started = client.post(
        "/api/v1/assessment-jobs",
        json={
            "target_type": "repository",
            "target_entry": "https://github.com/example/project",
            "environment_mode": "later",
        },
    )
    fetched = client.get(f"/api/v1/assessment-jobs/{service.snapshot.job_id}")

    assert started.status_code == 202
    assert fetched.status_code == 200
    assert started.json()["job_id"] == fetched.json()["job_id"]
    assert service.request.target_entry == "https://github.com/example/project"


def test_final_decision_for_missing_or_expired_assessment_returns_404() -> None:
    response = client.post(
        f"/api/v1/assessments/{uuid4()}/final-decision",
        json={"decision": "pause", "rationale": "Awaiting verified evidence."},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "ASSESSMENT_REVIEW_NOT_FOUND"
