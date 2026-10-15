"""Targeted tests for the Step 10 asynchronous Assessment progress facade."""

import time
from datetime import UTC, datetime
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest

from researchops.schemas import AssessmentRequest, ReadinessAssessment
from researchops.services.assessment_jobs import AssessmentJobService


def completed_assessment() -> ReadinessAssessment:
    finding = {
        "finding_id": "finding-ready",
        "condition": "Validated condition",
        "title": "Validated material",
        "summary": "The retained Evidence supports this bounded conclusion.",
        "finding_type": "Fact",
        "gate_critical": False,
        "readiness_impact": "The current validation path can continue.",
        "evidence": [],
    }
    dimensions = [
        {
            "dimension_id": dimension_id,
            "name": name,
            "status": "Ready",
            "summary": "Validated positive Evidence is available.",
            "gate_impact": "No Gate-critical issue was retained.",
            "findings": [{**finding, "finding_id": f"finding-{dimension_id.lower()}"}],
        }
        for dimension_id, name in (
            ("RD-01", "Data & Access Readiness"),
            ("RD-02", "Environment & Dependency Readiness"),
            ("RD-03", "Weights & Configuration Readiness"),
        )
    ]
    return ReadinessAssessment.model_validate(
        {
            "assessment_id": uuid4(),
            "status": "completed",
            "data_mode": "live_repository",
            "target_type": "repository",
            "target_entry": "https://github.com/example/project",
            "resolved_target": {
                "target_type": "repository",
                "source_entry": "https://github.com/example/project",
                "display_name": "example/project",
                "canonical_id": "github:example/project",
                "canonical_url": "https://github.com/example/project",
                "resolution_method": "direct_url",
            },
            "generated_at": datetime.now(UTC),
            "dimensions": dimensions,
            "gate_available": True,
            "overall_gate": "PROCEED",
            "trigger_refs": ["finding-rd-01"],
            "main_risk": "No Gate-critical risk was retained.",
            "first_next_action": {
                "action_id": "action-validate",
                "title": "Run minimum validation",
                "description": "Validate the selected reproduction path.",
                "action_type": "Minimum Validation",
                "reason_refs": ["finding-rd-01"],
            },
        }
    )


class BlockingWorkflow:
    def __init__(self) -> None:
        self.progress_emitted = Event()
        self.release = Event()

    def create_assessment_with_progress(self, _request, callback=None):
        if callback is not None:
            callback(
                {
                    "material_bundle": SimpleNamespace(
                        sources=[SimpleNamespace(title="README.md")]
                    ),
                    "local_analysis": SimpleNamespace(evidence_candidates=[object(), object()]),
                }
            )
        self.progress_emitted.set()
        self.release.wait(timeout=2)
        return completed_assessment()


class FailingWorkflow:
    def create_assessment_with_progress(self, _request, callback=None):
        raise RuntimeError("secret provider detail")


def service_for(workflow) -> AssessmentJobService:
    settings = SimpleNamespace(
        llm_analysis_run_ttl_seconds=30.0,
        llm_analysis_run_max_entries=10,
    )
    return AssessmentJobService(workflow, settings=settings)


def request() -> AssessmentRequest:
    return AssessmentRequest(
        target_type="repository",
        target_entry="https://github.com/example/project",
        environment_mode="later",
    )


def wait_for_terminal(service: AssessmentJobService, job_id):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        snapshot = service.get(job_id)
        if snapshot.state in {"completed", "failed"}:
            return snapshot
        time.sleep(0.01)
    pytest.fail("Assessment job did not reach a terminal state")


def test_job_reports_workflow_derived_scope_before_completion() -> None:
    workflow = BlockingWorkflow()
    service = service_for(workflow)

    queued = service.start(request())
    assert queued.state == "queued"
    assert workflow.progress_emitted.wait(timeout=1)

    running = service.get(queued.job_id)
    assert running.state == "running"
    assert running.phase == "validating_evidence"
    assert running.material_source_count == 1
    assert running.material_titles == ["README.md"]
    assert running.evidence_candidate_count == 2
    assert running.assessment is None

    workflow.release.set()
    completed = wait_for_terminal(service, queued.job_id)
    assert completed.state == "completed"
    assert completed.phase == "completed"
    assert completed.assessment is not None
    assert completed.assessment.overall_gate == "PROCEED"


def test_job_failure_is_technical_and_does_not_fabricate_assessment() -> None:
    service = service_for(FailingWorkflow())

    terminal = wait_for_terminal(service, service.start(request()).job_id)

    assert terminal.state == "failed"
    assert terminal.phase == "failed"
    assert terminal.assessment is None
    assert terminal.error_message is not None
    assert "secret provider detail" not in terminal.error_message
