"""Application service orchestrating model analysis without deterministic adjudication."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

from researchops.core.config import Settings, get_settings
from researchops.schemas.ai_analysis import (
    AIAnalysisInvocation,
    AIAnalysisRun,
    AIAnalysisRunErrorCode,
    AIAnalysisRunState,
    AIModelTrace,
    MaterialBundle,
)
from researchops.services.analysis_boundaries import AIAnalysisRunStore, MaterialAnalysisModel
from researchops.services.deepseek_analysis import (
    AIModelConfigurationError,
    AIModelError,
    AIModelResponseError,
)


class InMemoryAIAnalysisRunStore:
    """Bounded, TTL-based process-local run store behind a replaceable port."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        ttl_seconds: float | None = None,
        max_entries: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        config = settings or get_settings()
        self.ttl_seconds = (
            ttl_seconds if ttl_seconds is not None else config.llm_analysis_run_ttl_seconds
        )
        self.max_entries = (
            max_entries if max_entries is not None else config.llm_analysis_run_max_entries
        )
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds 必须大于 0")
        if self.max_entries <= 0:
            raise ValueError("max_entries 必须大于 0")
        self._clock = clock
        self._lock = RLock()
        self._runs: OrderedDict[UUID, tuple[float, AIAnalysisRun]] = OrderedDict()

    def save(self, run: AIAnalysisRun) -> None:
        """Retain one run and evict expired or oldest entries deterministically."""
        with self._lock:
            now = self._clock()
            self._prune(now)
            self._runs.pop(run.run_id, None)
            while len(self._runs) >= self.max_entries:
                self._runs.popitem(last=False)
            self._runs[run.run_id] = (now + self.ttl_seconds, run.model_copy(deep=True))

    def get(self, run_id: UUID) -> AIAnalysisRun | None:
        """Return a retained run, extending neither its TTL nor its source scope."""
        with self._lock:
            self._prune(self._clock())
            stored = self._runs.get(run_id)
            return stored[1].model_copy(deep=True) if stored is not None else None

    def _prune(self, now: float) -> None:
        expired = [run_id for run_id, (expires_at, _) in self._runs.items() if expires_at <= now]
        for run_id in expired:
            self._runs.pop(run_id, None)


class AIAnalysisService:
    """Invoke the model, map safe failure states, and store the resulting run."""

    def __init__(
        self,
        model: MaterialAnalysisModel,
        run_store: AIAnalysisRunStore | None = None,
    ) -> None:
        self._model = model
        self._run_store = run_store if run_store is not None else InMemoryAIAnalysisRunStore()

    def analyze(self, bundle: MaterialBundle) -> AIAnalysisRun:
        """Create one auditable run without computing Readiness status or Gate."""
        run_id = uuid4()
        created_at = datetime.now(UTC)
        try:
            invocation = self._model.analyze(bundle)
        except AIModelConfigurationError:
            run = self._failure_run(
                run_id=run_id,
                bundle_id=bundle.bundle_id,
                created_at=created_at,
                state="configuration_required",
                error_code="llm_configuration_required",
                error_message="模型 API Key 或配置尚未就绪；模型分析未发起。",
            )
        except AIModelResponseError as exc:
            run = self._failure_run(
                run_id=run_id,
                bundle_id=bundle.bundle_id,
                created_at=created_at,
                state="invalid_model_response",
                error_code="llm_response_invalid",
                error_message="模型响应未通过结构化契约校验；未进入规则判定。",
                failure_trace=self._failure_trace(exc, created_at, "invalid_model_response"),
            )
        except AIModelError as exc:
            run = self._failure_run(
                run_id=run_id,
                bundle_id=bundle.bundle_id,
                created_at=created_at,
                state="model_unavailable",
                error_code="llm_provider_unavailable",
                error_message="模型服务本次不可用；未生成分析候选。",
                failure_trace=self._failure_trace(exc, created_at, "model_unavailable"),
            )
        else:
            run = self._completed_or_invalid_identity(
                run_id=run_id,
                bundle=bundle,
                created_at=created_at,
                invocation=invocation,
            )

        self._run_store.save(run)
        return run

    def get_run(self, run_id: UUID) -> AIAnalysisRun | None:
        """Read a stored analysis outcome without exposing source material."""
        return self._run_store.get(run_id)

    def _completed_or_invalid_identity(
        self,
        *,
        run_id: UUID,
        bundle: MaterialBundle,
        created_at: datetime,
        invocation: AIAnalysisInvocation,
    ) -> AIAnalysisRun:
        if invocation.result.bundle_id == bundle.bundle_id:
            return AIAnalysisRun(
                run_id=run_id,
                bundle_id=bundle.bundle_id,
                state="completed",
                created_at=created_at,
                completed_at=datetime.now(UTC),
                invocation=invocation,
            )

        trace_payload = invocation.trace.model_dump()
        trace_payload.update(status="failed", error_type="bundle_identity_mismatch")
        failure_trace = AIModelTrace.model_validate(trace_payload)
        return self._failure_run(
            run_id=run_id,
            bundle_id=bundle.bundle_id,
            created_at=created_at,
            state="invalid_model_response",
            error_code="llm_response_invalid",
            error_message="模型响应引用了错误的材料 Bundle；未进入规则判定。",
            failure_trace=failure_trace,
        )

    @staticmethod
    def _failure_trace(
        error: AIModelError,
        created_at: datetime,
        error_type: str,
    ) -> AIModelTrace:
        if error.trace is not None:
            if error.trace.status == "failed":
                return error.trace
            trace_payload = error.trace.model_dump()
            trace_payload.update(status="failed", error_type=error_type)
            return AIModelTrace.model_validate(trace_payload)
        completed_at = datetime.now(UTC)
        return AIModelTrace(
            trace_id=uuid4(),
            model="unavailable",
            started_at=created_at,
            completed_at=completed_at,
            duration_ms=max(0, round((completed_at - created_at).total_seconds() * 1000)),
            attempts=1,
            status="failed",
            error_type=error_type,
        )

    @staticmethod
    def _failure_run(
        *,
        run_id: UUID,
        bundle_id: UUID,
        created_at: datetime,
        state: AIAnalysisRunState,
        error_code: AIAnalysisRunErrorCode,
        error_message: str,
        failure_trace: AIModelTrace | None = None,
    ) -> AIAnalysisRun:
        return AIAnalysisRun(
            run_id=run_id,
            bundle_id=bundle_id,
            state=state,
            created_at=created_at,
            completed_at=datetime.now(UTC),
            failure_trace=failure_trace,
            error_code=error_code,
            error_message=error_message,
        )
