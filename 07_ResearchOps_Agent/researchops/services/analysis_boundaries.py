"""Ports separating model interpretation from Rule validation and Human review."""

from typing import Protocol
from uuid import UUID

from researchops.schemas.ai_analysis import (
    AIAnalysisInvocation,
    AIAnalysisResult,
    AIAnalysisRun,
    AIAnalysisValidationResult,
    AIContextGapInvocation,
    AIEvidenceExtractionResult,
    AIEvidenceFindingDraftInvocation,
    AIFeedbackReassessmentInvocation,
    AIToolAcquisitionInvocation,
    EvidenceFindingInput,
    HumanFeedback,
    MaterialBundle,
    ResearchLoopResult,
    ResearchToolExecutionResult,
    ToolAcquisitionInput,
    ToolRequest,
)


class MaterialAnalysisModel(Protocol):
    """AI boundary: understand material and propose candidates, never final statuses."""

    def analyze(self, bundle: MaterialBundle) -> AIAnalysisInvocation:
        """Return untrusted structured candidates for deterministic validation."""
        ...


class ContextGapModel(Protocol):
    """AI boundary that identifies facts and minimum gaps without selecting tools."""

    def analyze_context_gaps(self, bundle: MaterialBundle) -> AIContextGapInvocation:
        """Return Context & Gap only; acquisition selection is a separate phase."""
        ...


class ToolAcquisitionModel(Protocol):
    """AI boundary that plans only allowlisted, read-only acquisition."""

    def plan_tool_acquisition(
        self,
        context: ToolAcquisitionInput,
    ) -> AIToolAcquisitionInvocation:
        """Return a minimum plan; this method never executes tools."""
        ...


class EvidenceFindingDraftModel(Protocol):
    """AI boundary for local Evidence, Conflict, and Finding drafting only."""

    def draft_evidence_findings(
        self,
        context: EvidenceFindingInput,
    ) -> AIEvidenceFindingDraftInvocation:
        """Return source-bound local drafts; never make a formal decision."""
        ...


class FeedbackReassessmentModel(Protocol):
    """AI boundary that scopes feedback before any tool or evidence work."""

    def reassess_feedback(self, bundle: MaterialBundle) -> AIFeedbackReassessmentInvocation:
        ...


class AsyncContextGapModel(Protocol):
    """Cancellable asynchronous boundary for Context & Gap analysis."""

    async def analyze_context_gaps_async(self, bundle: MaterialBundle) -> AIContextGapInvocation:
        ...


class AsyncToolAcquisitionModel(Protocol):
    """Cancellable boundary for minimum safe Tool Acquisition planning."""

    async def plan_tool_acquisition_async(
        self,
        context: ToolAcquisitionInput,
    ) -> AIToolAcquisitionInvocation:
        ...


class AsyncEvidenceFindingDraftModel(Protocol):
    """Cancellable boundary for locally scoped Evidence/Finding drafting."""

    async def draft_evidence_findings_async(
        self,
        context: EvidenceFindingInput,
    ) -> AIEvidenceFindingDraftInvocation:
        ...


class ResearchToolExecutor(Protocol):
    """Rule boundary that authorizes and runs allowlisted deterministic reads."""

    def execute(
        self,
        requests: list[ToolRequest],
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchToolExecutionResult:
        """Return audited connector results and an enriched material bundle."""
        ...


class ResearchLoopRunner(Protocol):
    """Workflow boundary for bounded AI planning plus deterministic reads."""

    def run(
        self,
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchLoopResult:
        """Return the audited loop result and the enriched final bundle."""
        ...


class AsyncMaterialAnalysisModel(Protocol):
    """Cancellable asynchronous AI boundary for request-driven workflows."""

    async def analyze_async(self, bundle: MaterialBundle) -> AIAnalysisInvocation:
        """Return candidates while allowing the caller to cancel the in-flight request."""
        ...

class AIAnalysisRunStore(Protocol):
    """Storage boundary for model candidates and content-free execution metadata."""

    def save(self, run: AIAnalysisRun) -> None:
        """Store or replace one immutable analysis outcome."""
        ...

    def get(self, run_id: UUID) -> AIAnalysisRun | None:
        """Return one retained run without loading its source material."""
        ...


class EvidenceRuleValidator(Protocol):
    """Rule boundary: validate model candidates without inventing source facts."""

    def validate(
        self,
        bundle: MaterialBundle,
        analysis: AIAnalysisResult | AIEvidenceExtractionResult,
    ) -> AIAnalysisValidationResult:
        """Validate source identity, quote fidelity, location, and claim scope."""
        ...


class HumanFeedbackSink(Protocol):
    """Human boundary: record correction intent without silently rewriting evidence."""

    def submit(self, feedback: HumanFeedback) -> None:
        """Persist or queue a human review action for a later controlled revision."""
        ...
