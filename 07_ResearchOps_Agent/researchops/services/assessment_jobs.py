"""Asynchronous, read-only progress facade for the synchronous LangGraph workflow."""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock, Thread
from typing import Any, Protocol
from uuid import UUID, uuid4

from researchops.core.access_context import (
    authorize_resource,
    bind_resource,
    check_operation,
    current_access,
)
from researchops.core.config import Settings, get_settings
from researchops.schemas import AssessmentJobPhase, AssessmentJobResponse, AssessmentRequest
from researchops.services.access_store import AccessError
from researchops.services.execution_control import controller


class AssessmentJobNotFoundError(LookupError):
    """The progress job is absent or expired."""


class ProgressAssessmentWorkflow(Protocol):
    def create_assessment_with_progress(self, request, callback=None): ...


class AssessmentJobService:
    """Run one Assessment in a daemon thread and expose content-free progress snapshots."""

    def __init__(
        self,
        workflow: ProgressAssessmentWorkflow,
        settings: Settings | None = None,
    ) -> None:
        config = settings or get_settings()
        self.workflow = workflow
        self.ttl_seconds = config.llm_analysis_run_ttl_seconds
        self.max_entries = config.llm_analysis_run_max_entries
        self._lock = RLock()
        self._jobs: OrderedDict[UUID, tuple[float, AssessmentJobResponse]] = OrderedDict()

    def start(self, request: AssessmentRequest) -> AssessmentJobResponse:
        now = datetime.now(UTC)
        job = AssessmentJobResponse(
            job_id=uuid4(),
            state="queued",
            phase="queued",
            created_at=now,
            updated_at=now,
        )
        executor = controller()
        if executor:
            context = current_access.get()

            def prepare(operation):
                nonlocal job
                job = job.model_copy(update={"job_id": UUID(operation)})
                bind_resource("job", job.job_id)
                self._save(job)

            _, future = executor.submit(
                lambda: self._run(job.job_id, request.model_copy(deep=True)), prepare=prepare
            )

            def completed(result):
                exc = result.exception()
                if exc:
                    failed = job.model_copy(
                        update={
                            "state": "failed",
                            "phase": "failed",
                            "updated_at": datetime.now(UTC),
                            "error_message": str(exc)
                            if isinstance(exc, AccessError)
                            else "任务未能完成，请重试。",
                        }
                    )
                    context.store.save_snapshot(str(job.job_id), failed.model_dump(mode="json"))
                    with self._lock:
                        self._jobs[job.job_id] = (time.monotonic() + self.ttl_seconds, failed)

            future.add_done_callback(completed)
            return job.model_copy(deep=True)
        self._save(job)
        Thread(
            target=self._run,
            args=(job.job_id, request.model_copy(deep=True)),
            name=f"researchops-assessment-{str(job.job_id)[:8]}",
            daemon=True,
        ).start()
        return job.model_copy(deep=True)

    def get(self, job_id: UUID) -> AssessmentJobResponse:
        authorize_resource("job", job_id)
        context = current_access.get()
        if context:
            operation = context.store.operation(str(job_id))
            if operation and operation["snapshot"]:
                job = AssessmentJobResponse.model_validate(json.loads(operation["snapshot"]))
                if operation["state"] == "interrupted":
                    return job.model_copy(
                        update={
                            "state": "failed",
                            "phase": "failed",
                            "assessment": None,
                            "error_message": "服务重启，任务已中断；未自动重新执行。",
                        }
                    )
                if operation["state"] in {"queued", "running"} and job.state == "completed":
                    return job.model_copy(
                        update={
                            "state": "running",
                            "phase": "validating_output",
                            "assessment": None,
                        }
                    )
                return job
        with self._lock:
            self._prune(time.monotonic())
            stored = self._jobs.get(job_id)
            if stored is None:
                raise AssessmentJobNotFoundError(
                    "Assessment job is missing or expired; start a new assessment."
                )
            return stored[1].model_copy(deep=True)

    def _run(self, job_id: UUID, request: AssessmentRequest) -> None:
        initial = self.get(job_id)
        self._save(
            initial.model_copy(
                update={
                    "state": "running",
                    "phase": "resolving_target",
                    "updated_at": datetime.now(UTC),
                }
            )
        )

        def progress(state: dict[str, Any]) -> None:
            check_operation()
            current = self.get(job_id)
            bundle = state.get("material_bundle")
            analysis = state.get("local_analysis")
            validation = state.get("evidence_validation")
            self._save(
                current.model_copy(
                    update={
                        "phase": self._phase(state),
                        "updated_at": datetime.now(UTC),
                        "material_source_count": len(bundle.sources) if bundle else None,
                        "material_titles": (
                            [source.title for source in bundle.sources] if bundle else []
                        ),
                        "evidence_candidate_count": (
                            len(analysis.evidence_candidates) if analysis else None
                        ),
                        "validated_evidence_count": (
                            len(validation.evidence_results) if validation else None
                        ),
                    }
                )
            )

        try:
            assessment = self.workflow.create_assessment_with_progress(request, progress)
        except AccessError:
            raise
        except Exception:
            current = self.get(job_id)
            self._save(
                current.model_copy(
                    update={
                        "state": "failed",
                        "phase": "failed",
                        "updated_at": datetime.now(UTC),
                        "error_message": (
                            "The Assessment job failed before a validated result was available."
                        ),
                    }
                )
            )
            return

        current = self.get(job_id)
        self._save(
            current.model_copy(
                update={
                    "state": "completed",
                    "phase": "completed",
                    "updated_at": datetime.now(UTC),
                    "assessment": assessment,
                }
            )
        )

    def _save(self, job: AssessmentJobResponse) -> None:
        validated = AssessmentJobResponse.model_validate(job.model_dump())
        context = current_access.get()
        if context:
            context.store.save_snapshot(str(job.job_id), validated.model_dump(mode="json"))
        with self._lock:
            now = time.monotonic()
            self._prune(now)
            self._jobs.pop(job.job_id, None)
            while len(self._jobs) >= self.max_entries:
                victim = next(
                    (
                        key
                        for key, (_, value) in self._jobs.items()
                        if value.state in {"completed", "failed"}
                    ),
                    None,
                )
                if victim is None:
                    break
                self._jobs.pop(victim)
            self._jobs[job.job_id] = (now + self.ttl_seconds, deepcopy(validated))

    def _prune(self, now: float) -> None:
        for job_id in [key for key, (expires_at, _) in self._jobs.items() if expires_at <= now]:
            self._jobs.pop(job_id, None)

    @staticmethod
    def _phase(state: dict[str, Any]) -> AssessmentJobPhase:
        if "assessment" in state:
            return "validating_output"
        if "readiness" in state:
            return "validating_output"
        if "projection" in state:
            return "rule_adjudication"
        if "evidence_validation" in state:
            return "rule_adjudication"
        if "local_analysis" in state:
            return "validating_evidence"
        if "research_loop" in state:
            return "ai_evidence_analysis"
        if "material_bundle" in state:
            return "ai_research_planning"
        if "repository_materials" in state or "paper_materials" in state:
            return "building_material_bundle"
        trace = state.get("workflow_trace", [])
        if trace and trace[-1].startswith("acquire_environment:"):
            return "collecting_materials"
        if "resolved_target" in state:
            return "acquiring_context"
        return "resolving_target"
