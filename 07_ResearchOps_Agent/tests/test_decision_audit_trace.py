"""Safe API trace coverage for model and connector diagnostics."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from researchops.schemas import AIModelTrace
from researchops.services.decision_audit import build_assessment_audit


def test_failed_provider_trace_keeps_request_id_and_duration_without_raw_error() -> None:
    started_at = datetime.now(UTC)
    trace = AIModelTrace(
        trace_id=uuid4(),
        model="deepseek-flash",
        request_id="provider-request-123",
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=42),
        duration_ms=42,
        attempts=2,
        status="failed",
        error_type="ReadTimeout",
    )

    events = build_assessment_audit(
        {
            "failure_state": "model_unavailable",
            "failure_trace": trace,
        }
    )

    event = next(item for item in events if item.stage == "analysis_failure")
    assert event.actor == "ai"
    assert event.provider_request_id == "provider-request-123"
    assert event.model_trace_id == trace.trace_id
    assert event.duration_ms == 42
    assert "ReadTimeout" not in event.detail
