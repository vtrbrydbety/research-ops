"""FastAPI 与 Readiness LangGraph 之间的应用服务。"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from langgraph.graph.state import CompiledStateGraph

from researchops.core.access_context import check_operation
from researchops.graphs.model_readiness_graph import (
    build_model_readiness_graph,
)
from researchops.schemas import (
    AssessmentFeedbackRequest,
    AssessmentFeedbackResponse,
    AssessmentRequest,
    AssessmentRevisionHistory,
    FinalInvestmentDecisionRecord,
    FinalInvestmentDecisionRequest,
    ReadinessAssessment,
)
from researchops.services.analysis_boundaries import (
    EvidenceFindingDraftModel,
    ResearchLoopRunner,
)
from researchops.services.assessment_review_store import AssessmentReviewStore
from researchops.services.deepseek_analysis import DeepSeekAnalysisModel
from researchops.services.human_review import (
    HumanReviewService,
)
from researchops.services.phased_research_loop import PhasedResearchLoopService
from researchops.services.readiness_assessment import ReadinessAssessmentService
from researchops.services.research_tool_execution import DeterministicResearchToolExecutor


class ModelBackedReadinessWorkflowService:
    """Compile and reuse the real AI → Rule Assessment graph."""

    def __init__(
        self,
        assessment_service: ReadinessAssessmentService | None = None,
        *,
        evidence_model: EvidenceFindingDraftModel | None = None,
        feedback_model: object | None = None,
        research_loop: ResearchLoopRunner | None = None,
        review_store: AssessmentReviewStore | None = None,
        graph: CompiledStateGraph | None = None,
    ) -> None:
        self.assessment_service = assessment_service or ReadinessAssessmentService()
        shared_model = None
        if evidence_model is None:
            shared_model = DeepSeekAnalysisModel()
        self.evidence_model = evidence_model or shared_model
        if self.evidence_model is None:
            raise ValueError("模型化 Readiness 工作流缺少 AI boundary 实现")
        self.feedback_model = feedback_model or self.evidence_model
        self.research_loop = research_loop
        context_gap = getattr(self.evidence_model, "analyze_context_gaps", None)
        tool_acquisition = getattr(self.evidence_model, "plan_tool_acquisition", None)
        if (
            self.research_loop is None
            and callable(context_gap)
            and callable(tool_acquisition)
            and callable(getattr(self.evidence_model, "draft_evidence_findings", None))
        ):
            executor = DeterministicResearchToolExecutor(
                repository_collector=(self.assessment_service.repository_material_collector),
                paper_collector=self.assessment_service.paper_material_collector,
                dataset_probe=self.assessment_service.data_access_service.probe,
                checkpoint_probe=self.assessment_service.external_asset_probe,
                environment_service=self.assessment_service.environment_fact_service,
            )
            self.research_loop = PhasedResearchLoopService(self.evidence_model, executor)
        self.graph = graph or build_model_readiness_graph(
            assessment_service=self.assessment_service,
            evidence_model=self.evidence_model,
            research_loop=self.research_loop,
        )
        self.human_review_service = HumanReviewService(
            assessment_service=self.assessment_service,
            evidence_model=self.evidence_model,
            feedback_model=self.feedback_model,
            research_loop=self.research_loop,
            store=review_store,
        )

    def create_assessment(self, request: AssessmentRequest) -> ReadinessAssessment:
        return self.create_assessment_with_progress(request)

    def create_assessment_with_progress(
        self,
        request: AssessmentRequest,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ReadinessAssessment:
        check_operation()
        state: dict[str, Any] | None = None
        for snapshot in self.graph.stream(
            {"request": request, "workflow_trace": []},
            stream_mode="values",
        ):
            check_operation()
            state = snapshot
            if callback is not None:
                callback(snapshot)
        if state is None or "assessment" not in state:
            raise RuntimeError("Model-backed Assessment graph produced no final state")
        return self.human_review_service.register(state)

    def submit_feedback(
        self,
        assessment_id: UUID,
        request: AssessmentFeedbackRequest,
    ) -> AssessmentFeedbackResponse:
        return self.human_review_service.submit_feedback(assessment_id, request)

    def get_assessment(self, assessment_id: UUID) -> ReadinessAssessment:
        return self.human_review_service.get_assessment(assessment_id)

    def get_assessment_revision_history(
        self,
        assessment_id: UUID,
    ) -> AssessmentRevisionHistory:
        return self.human_review_service.get_revision_history(assessment_id)

    def record_final_decision(
        self,
        assessment_id: UUID,
        request: FinalInvestmentDecisionRequest,
    ) -> FinalInvestmentDecisionRecord:
        return self.human_review_service.record_final_decision(assessment_id, request)
