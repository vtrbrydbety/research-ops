"""Step 8 model-backed LangGraph routing and failure-state tests."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from researchops.schemas import (
    AIConflictFindingInvocation,
    AIConflictFindingResult,
    AIContextGapInvocation,
    AIContextGapResult,
    AIEvidenceFindingDraftInvocation,
    AIEvidenceFindingDraftResult,
    AIFeedbackReassessmentInvocation,
    AIFeedbackReassessmentResult,
    AIModelTrace,
    AIResearchPlanInvocation,
    AIResearchPlanResult,
    AssessmentFeedbackRequest,
    AssessmentRequest,
    EvidenceFindingHandoff,
    FeedbackReassessmentScope,
    FinalInvestmentDecisionRequest,
    FindingCandidate,
    HumanSourceSubmission,
    InformationGap,
    MaterialBundle,
    MaterialSource,
    ResearchLoopHandoff,
    ResearchLoopResult,
    ResearchLoopRound,
    ResearchToolExecutionResult,
    ToolRequest,
    ToolRequestExecutionResult,
    UnresolvedQuestion,
)
from researchops.services import (
    AIModelConfigurationError,
    AIModelResponseError,
    AIModelTransportError,
    DurableAssessmentReviewStore,
    ModelBackedReadinessWorkflowService,
    ReadinessAssessmentService,
    RepositoryCollectionError,
    RepositoryMaterials,
    RepositoryTextFile,
)

REPOSITORY_URL = "https://github.com/example/model-backed-project"


class StaticRepositoryCollector:
    def __init__(self) -> None:
        self.calls = 0

    def collect(self, _target: object) -> RepositoryMaterials:
        self.calls += 1
        text = "Repeated evidence.\nProject material.\nRepeated evidence."
        return RepositoryMaterials(
            repository_url=REPOSITORY_URL,
            default_branch="main",
            readme=RepositoryTextFile(
                path="README.md",
                text=text,
                html_url=f"{REPOSITORY_URL}/blob/main/README.md",
                size=len(text.encode()),
            ),
            dependency_files=(),
            relevant_paths=("README.md",),
            fetched_at=datetime.now(UTC),
        )


class FailingRepositoryCollector:
    def collect(self, _target: object) -> RepositoryMaterials:
        raise RepositoryCollectionError("synthetic acquisition failure", status_code=503)


def _trace(request_id: str) -> AIModelTrace:
    now = datetime.now(UTC)
    return AIModelTrace(
        trace_id=uuid4(),
        model="fake-model",
        request_id=request_id,
        started_at=now,
        completed_at=now,
        duration_ms=0,
        attempts=1,
        status="success",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )


class FeedbackReassessmentStub:
    """Controlled provider for the mandatory feedback-scoping stage."""

    def __init__(self, *, handoff: str = "evidence_finding") -> None:
        self.handoff = handoff
        self.calls = 0

    def reassess_feedback(self, bundle) -> AIFeedbackReassessmentInvocation:
        self.calls += 1
        context = bundle.human_review_context
        assert context is not None
        finding_refs = [context.original_finding.finding_id] if context.original_finding else []
        evidence_refs = [context.original_evidence.evidence_id] if context.original_evidence else []
        dimension_refs = (
            ["RD-01"]
            if context.original_finding and context.original_finding.condition.startswith("rd01.")
            else ["RD-02"]
            if context.original_finding and context.original_finding.condition.startswith("rd02.")
            else ["RD-03"]
            if context.original_finding and context.original_finding.condition.startswith("rd03.")
            else []
        )

        gaps = (
            [
                InformationGap(
                    gap_id="gap-feedback-checkpoint",
                    area="rd03_weights_configuration",
                    criterion_id="rd03.checkpoint_access",
                    state="missing",
                    description="Check whether the feedback affects checkpoint access.",
                    why_needed="The scoped feedback requested a bounded checkpoint check.",
                    inspected_source_ids=[source.source_id for source in bundle.sources],
                )
            ]
            if self.handoff == "tool_acquisition"
            else []
        )
        return AIFeedbackReassessmentInvocation(
            result=AIFeedbackReassessmentResult(
                reassessment_id=uuid4(),
                bundle_id=bundle.bundle_id,
                reassessment_required=True,
                affected_scope=FeedbackReassessmentScope(
                    finding_refs=finding_refs,
                    evidence_refs=evidence_refs,
                    dimension_refs=dimension_refs,
                ),
                change_summary="The user feedback affects the submitted target only.",
                information_gaps=gaps,
                handoff=self.handoff,
            ),
            trace=_trace("fake-feedback-reassessment"),
        )


class InvalidFeedbackReassessmentStub:
    """Simulates a provider that fails only the optional scope handoff."""

    def reassess_feedback(self, _bundle) -> AIFeedbackReassessmentInvocation:
        raise AIModelResponseError("synthetic malformed feedback scope")


class DependentFeedbackReassessmentStub(FeedbackReassessmentStub):
    """Scopes a target fact to one dependent Dimension and Evaluation Signal."""

    def reassess_feedback(self, bundle) -> AIFeedbackReassessmentInvocation:
        invocation = super().reassess_feedback(bundle)
        return invocation.model_copy(
            update={
                "result": invocation.result.model_copy(
                    update={
                        "affected_scope": invocation.result.affected_scope.model_copy(
                            update={
                                "dimension_refs": ["RD-01", "RD-02"],
                                "signal_refs": ["evaluation_conditions"],
                            }
                        )
                    }
                )
            }
        )


def _questions(source_ids: list[str]) -> list[UnresolvedQuestion]:
    specifications = (
        ("q-rd01", "rd01_data_access", "rd01.dataset_access", "RD-01"),
        (
            "q-rd02",
            "rd02_environment_dependency",
            "rd02.environment_compatibility",
            "RD-02",
        ),
        (
            "q-rd03",
            "rd03_weights_configuration",
            "rd03.checkpoint_access",
            "RD-03",
        ),
        (
            "q-resource",
            "resource_constraint",
            "resource.minimum_requirements",
            "RD-02",
        ),
        (
            "q-evaluation",
            "evaluation_conditions",
            "evaluation.protocol",
            "RD-03",
        ),
    )
    return [
        UnresolvedQuestion(
            question_id=question_id,
            condition_key=criterion_id,
            criterion_id=criterion_id,
            dimension_id=dimension_id,
            question=f"What source establishes {criterion_id}?",
            missing_information="The supplied material does not establish this condition.",
            inspected_source_ids=source_ids,
        )
        for question_id, _area, criterion_id, dimension_id in specifications
    ]


class QuestionOnlyEvidenceModel:
    """Current local Draft fixture; absent facts stay Unknown."""

    def __init__(self) -> None:
        self.calls = 0
        self.local_inputs = []
        self.source_scopes = []
        self.source_paths = []
        self.review_contexts = []

    def analyze_context_gaps(self, _bundle):
        raise AssertionError("the injected research loop owns Context & Gap")

    def plan_tool_acquisition(self, _context):
        raise AssertionError("the injected research loop owns Tool Acquisition")

    def draft_evidence_findings(self, context):
        self.calls += 1
        self.local_inputs.append(context)
        self.source_scopes.append([item.access_scope for item in context.bundle.sources])
        self.source_paths.append([item.source_path for item in context.bundle.sources])
        self.review_contexts.append(context.bundle.human_review_context)
        return AIEvidenceFindingDraftInvocation(
            result=AIEvidenceFindingDraftResult(
                handoff=EvidenceFindingHandoff(needs_more_information=False, ready_for_rule=True)
            ),
            trace=_trace("fake-local-empty-draft"),
        )


class InitialLocalEvidenceFindingModel(QuestionOnlyEvidenceModel):
    """Full phased boundary stub: first pass must not call legacy extraction."""

    def __init__(self) -> None:
        super().__init__()
        self.local_inputs = []

    def analyze_context_gaps(self, _bundle):
        raise AssertionError("injected research loop owns the Context & Gap test fixture")

    def plan_tool_acquisition(self, _context):
        raise AssertionError("injected research loop owns the Tool Acquisition test fixture")

    def draft_evidence_findings(self, context) -> AIEvidenceFindingDraftInvocation:
        self.local_inputs.append(context)
        source = next(item for item in context.bundle.sources if item.source_path == "README.md")
        evidence_drafts = []
        finding_drafts = []
        for index, condition in enumerate(context.condition_contexts, start=1):
            evidence_id = f"local-{condition.condition_ref}-{index}"
            evidence_drafts.append(
                {
                    "local_evidence_id": evidence_id,
                    "condition_refs": [condition.condition_ref],
                    "source_ref": source.source_id,
                    "source_type": "Material",
                    "evidence_type": "Unknown",
                    "location": "README.md:lines 1-1",
                    "line_start": 1,
                    "line_end": 1,
                    "material_type": "README",
                    "quote": "Repeated evidence.",
                    "claim": f"The current material does not establish {condition.condition_ref}.",
                    "verification_status": "Located Only",
                    "conflict_note": "The supplied text does not establish the required condition.",
                }
            )
            finding_drafts.append(
                {
                    "local_finding_id": f"finding-{condition.condition_ref}-{index}",
                    "operation": "create",
                    "condition": condition.condition_ref,
                    "summary": f"The condition {condition.condition_ref} remains unestablished.",
                    "finding_type": "Unknown",
                    "primary_dimension": condition.primary_dimension,
                    "related_dimensions": condition.related_dimensions,
                    "evidence_refs_local": [evidence_id],
                }
            )
        return AIEvidenceFindingDraftInvocation(
            result=AIEvidenceFindingDraftResult(
                evidence_drafts=evidence_drafts,
                finding_drafts=finding_drafts,
                handoff=EvidenceFindingHandoff(needs_more_information=False, ready_for_rule=True),
            ),
            trace=_trace("fake-initial-local-draft"),
        )


class FailAfterFirstLocalConditionModel(InitialLocalEvidenceFindingModel):
    """Retains a successful Condition before a later provider contract failure."""

    def draft_evidence_findings(self, context) -> AIEvidenceFindingDraftInvocation:
        if context.condition_contexts[0].condition_ref == "rd01.dataset_access":
            now = datetime.now(UTC)
            raise AIModelResponseError(
                "safe synthetic contract failure",
                trace=AIModelTrace(
                    trace_id=uuid4(),
                    model="fake-model",
                    started_at=now,
                    completed_at=now,
                    duration_ms=1,
                    attempts=2,
                    status="failed",
                    error_type="ValidationError",
                    error_detail="schema[handoff:value_error]",
                    api_mode="responses",
                ),
            )
        return super().draft_evidence_findings(context)


class AmbiguousEvidenceModel(InitialLocalEvidenceFindingModel):
    def draft_evidence_findings(self, context):
        invocation = super().draft_evidence_findings(context)
        draft = invocation.result.evidence_drafts[0]
        # Two equal occurrences: without line bounds this cannot establish a Fact.
        draft.line_start = None
        draft.line_end = None
        draft.location = "README.md"
        draft.evidence_type = "Fact"
        draft.claim = "Repeated evidence."
        invocation.result.finding_drafts[0].finding_type = "Fact"
        return invocation


class EmptyConflictFindingModel:
    def __init__(self) -> None:
        self.calls = 0

    def analyze_conflicts_findings(self, context) -> AIConflictFindingInvocation:
        self.calls += 1
        return AIConflictFindingInvocation(
            result=AIConflictFindingResult(
                interpretation_id=uuid4(),
                bundle_id=context.bundle_id,
                evidence_extraction_id=context.evidence_extraction_id,
                summary="No admissible Conflict or Finding candidate was established.",
                considered_evidence_candidate_ids=[
                    item.candidate.candidate_id for item in context.evidence
                ],
            ),
            trace=_trace("fake-conflict-request"),
        )


class RetainedFactEvidenceModel(QuestionOnlyEvidenceModel):
    def __init__(self, *, replace_on_feedback=False, finding=True):
        super().__init__()
        self.replace_on_feedback = replace_on_feedback
        self.finding = finding

    def draft_evidence_findings(self, context):
        invocation = super().draft_evidence_findings(context)
        if context.condition_contexts[0].condition_ref != "rd01.dataset_identity":
            return invocation
        feedback = context.bundle.human_review_context
        if feedback and not self.replace_on_feedback:
            return invocation  # Rule must preserve retained evidence when Draft omits it.
        source = next(
            item
            for item in context.bundle.sources
            if (
                item.access_scope == "user_provided"
                if feedback
                else item.source_path == "README.md"
            )
        )
        quote = source.content if feedback else "Project material."
        line = 1 if feedback else 2
        invocation.result = AIEvidenceFindingDraftResult(
            evidence_drafts=[
                {
                    "local_evidence_id": "local-fact",
                    "condition_refs": ["rd01.dataset_identity"],
                    "source_ref": source.source_id,
                    "source_type": "User Context" if feedback else "Material",
                    "evidence_type": "Fact",
                    "location": f"{source.source_path}:line {line}",
                    "line_start": line,
                    "line_end": line,
                    "material_type": source.material_type,
                    "quote": quote,
                    "claim": quote,
                    "verification_status": "Located Only",
                }
            ],
            finding_drafts=[
                {
                    "local_finding_id": "local-finding",
                    "operation": "update_existing" if feedback else "create",
                    "existing_finding_ref": feedback.original_finding.finding_id
                    if feedback
                    else None,
                    "condition": "rd01.dataset_identity",
                    "summary": quote,
                    "finding_type": "Fact",
                    "primary_dimension": "RD-01",
                    "evidence_refs_local": ["local-fact"],
                }
            ]
            if self.finding
            else [],
            handoff=EvidenceFindingHandoff(needs_more_information=False, ready_for_rule=True),
        )
        return invocation


class LocalFeedbackEvidenceModel(RetainedFactEvidenceModel):
    """Uses the PA-04 local Draft boundary after the first full assessment."""

    def __init__(self) -> None:
        super().__init__()
        self.local_inputs = []

    def analyze_context_gaps(self, _bundle):
        raise AssertionError("the injected pass-through research loop owns this test stage")

    def plan_tool_acquisition(self, _context):
        raise AssertionError("the injected pass-through research loop owns this test stage")

    def draft_evidence_findings(self, context) -> AIEvidenceFindingDraftInvocation:
        user_sources = [
            source for source in context.bundle.sources if source.access_scope == "user_provided"
        ]
        if not user_sources:
            source = next(
                item for item in context.bundle.sources if item.source_path == "README.md"
            )
            if not any(
                item.condition_ref == "rd01.dataset_identity" for item in context.condition_contexts
            ):
                return AIEvidenceFindingDraftInvocation(
                    result=AIEvidenceFindingDraftResult(
                        handoff=EvidenceFindingHandoff(
                            needs_more_information=False,
                            ready_for_rule=True,
                        )
                    ),
                    trace=_trace("fake-initial-empty-local-draft"),
                )
            return AIEvidenceFindingDraftInvocation(
                result=AIEvidenceFindingDraftResult(
                    evidence_drafts=[
                        {
                            "local_evidence_id": "e-retained",
                            "condition_refs": ["rd01.dataset_identity"],
                            "source_ref": source.source_id,
                            "source_type": "Material",
                            "evidence_type": "Fact",
                            "location": "README.md:lines 2-2",
                            "line_start": 2,
                            "line_end": 2,
                            "material_type": "README",
                            "quote": "Project material.",
                            "claim": "The project material establishes the scoped dataset fact.",
                            "verification_status": "Located Only",
                        }
                    ],
                    finding_drafts=[
                        {
                            "local_finding_id": "f-retained",
                            "operation": "update_existing",
                            "existing_finding_ref": "f-retained",
                            "condition": "rd01.dataset_identity",
                            "summary": "The initial source-backed Fact remains relevant.",
                            "finding_type": "Fact",
                            "primary_dimension": "RD-01",
                            "related_dimensions": [],
                            "evidence_refs_local": ["e-retained"],
                        }
                    ],
                    handoff=EvidenceFindingHandoff(
                        needs_more_information=False,
                        ready_for_rule=True,
                    ),
                ),
                trace=_trace("fake-initial-retained-local-draft"),
            )

        self.local_inputs.append(context)
        user_source = user_sources[0]
        retained_evidence_ref = context.related_evidence[0].local_evidence_id

        return AIEvidenceFindingDraftInvocation(
            result=AIEvidenceFindingDraftResult(
                evidence_drafts=[
                    {
                        "local_evidence_id": "EVD-user-feedback",
                        "condition_refs": ["rd01.dataset_identity"],
                        "source_ref": user_source.source_id,
                        "source_type": "User Context",
                        "evidence_type": "Fact",
                        "location": f"{user_source.source_path}:lines 1-1",
                        "line_start": 1,
                        "line_end": 1,
                        "material_type": user_source.material_type,
                        "quote": user_source.content,
                        "claim": "The customer confirms the dataset fact.",
                        "verification_status": "Located Only",
                    }
                ],
                finding_drafts=[
                    {
                        "local_finding_id": "FD-feedback-update",
                        "operation": "update_existing",
                        "existing_finding_ref": "f-retained",
                        "condition": "rd01.dataset_identity",
                        "summary": "The retained fact and customer clarification are both relevant.",
                        "finding_type": "Fact",
                        "primary_dimension": "RD-01",
                        "related_dimensions": ["RD-02"],
                        "evidence_refs_local": [retained_evidence_ref, "EVD-user-feedback"],
                    }
                ],
                handoff=EvidenceFindingHandoff(
                    needs_more_information=False,
                    ready_for_rule=True,
                ),
            ),
            trace=_trace("fake-local-feedback-draft"),
        )


class FailingLocalFeedbackEvidenceModel(RetainedFactEvidenceModel):
    def draft_evidence_findings(self, context):
        if context.bundle.human_review_context:
            raise AIModelResponseError("synthetic local Draft failure")
        return super().draft_evidence_findings(context)


class ObserveRetainedEvidenceModel:
    """Returns one initial Finding and records each reassessment input."""

    def __init__(self, *, replace_on_feedback: bool = False) -> None:
        self.calls = 0
        self.considered_evidence_by_call: list[list[str]] = []
        self.review_contexts = []
        self.replace_on_feedback = replace_on_feedback

    def analyze_conflicts_findings(self, context) -> AIConflictFindingInvocation:
        self.calls += 1
        considered = [item.candidate.candidate_id for item in context.evidence]
        self.considered_evidence_by_call.append(considered)
        self.review_contexts.append(context.human_review_context)
        findings = []
        if self.calls == 1:
            findings = [
                FindingCandidate(
                    candidate_id="f-retained",
                    root_cause_key="rd01-dataset-identity",
                    condition_key="rd01.dataset_identity",
                    criterion_id="rd01.dataset_identity",
                    readiness_effect="condition_supported",
                    primary_dimension_id="RD-01",
                    title="Dataset access source retained",
                    summary="The initial source-backed Fact remains relevant.",
                    finding_type="Fact",
                    evidence_candidate_ids=["e-retained"],
                )
            ]
        elif self.replace_on_feedback and "e-user-replacement" in considered:
            findings = [
                FindingCandidate(
                    candidate_id="f-revised",
                    root_cause_key="rd01-dataset-identity",
                    condition_key="rd01.dataset_identity",
                    criterion_id="rd01.dataset_identity",
                    readiness_effect="condition_supported",
                    primary_dimension_id="RD-01",
                    title="Dataset identity confirmed by customer feedback",
                    summary="The customer correction resolves the original Finding.",
                    finding_type="Fact",
                    evidence_candidate_ids=["e-user-replacement"],
                )
            ]
        return AIConflictFindingInvocation(
            result=AIConflictFindingResult(
                interpretation_id=uuid4(),
                bundle_id=context.bundle_id,
                evidence_extraction_id=context.evidence_extraction_id,
                summary="Interpretation pass completed.",
                considered_evidence_candidate_ids=considered,
                finding_candidates=findings,
            ),
            trace=_trace("retain-then-omit-finding"),
        )


class RaisingEvidenceModel:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def extract_evidence(self, _bundle):
        self.calls += 1
        raise self.error

    def analyze_context_gaps(self, _bundle):
        raise AssertionError("the injected pass-through research loop owns this test stage")

    def plan_tool_acquisition(self, _context):
        raise AssertionError("the injected pass-through research loop owns this test stage")

    def draft_evidence_findings(self, _context):
        self.calls += 1
        raise self.error


class RaisingConflictFindingModel:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def analyze_conflicts_findings(self, _context):
        self.calls += 1
        raise self.error


class EnrichingResearchLoop:
    def __init__(self) -> None:
        self.calls = 0
        self.local_environment_authorized: bool | None = None
        self.review_contexts = []

    def run(self, bundle, *, local_environment_authorized=False) -> ResearchLoopResult:
        self.calls += 1
        self.local_environment_authorized = local_environment_authorized
        self.review_contexts.append(bundle.human_review_context)
        gap = InformationGap(
            gap_id="gap-checkpoint",
            area="rd03_weights_configuration",
            criterion_id="rd03.checkpoint_access",
            state="missing",
            description="Checkpoint access has not been verified.",
            why_needed="The Evidence stage needs the deterministic probe result.",
            inspected_source_ids=[source.source_id for source in bundle.sources],
        )
        request = ToolRequest(
            request_id="request-checkpoint",
            tool_name="search_github",
            gap_ids=[gap.gap_id],
            purpose="Locate a bounded checkpoint reference.",
            query="example checkpoint",
        )
        plan = AIResearchPlanResult(
            plan_id=uuid4(),
            bundle_id=bundle.bundle_id,
            summary="One allowlisted deterministic read is needed.",
            examined_source_ids=[source.source_id for source in bundle.sources],
            state="needs_tool_calls",
            information_gaps=[gap],
            tool_requests=[request],
        )
        content = "Deterministically collected checkpoint reference."
        source = MaterialSource(
            source_id=f"src-research-checkpoint-{self.calls}",
            material_type="Checkpoint-Release",
            title="Checkpoint search result",
            source_path=".researchops/checkpoint-search.json",
            content=content,
            content_sha256=sha256(content.encode()).hexdigest(),
            access_scope="public",
        )
        final_bundle = MaterialBundle(
            bundle_id=uuid4(),
            target=bundle.target,
            assembled_at=datetime.now(UTC),
            sources=[*bundle.sources, source],
        )
        now = datetime.now(UTC)
        planning = AIResearchPlanInvocation(
            result=plan,
            trace=AIModelTrace(
                trace_id=uuid4(),
                model="fake-research-planner",
                request_id="fake-research-request",
                started_at=now,
                completed_at=now,
                duration_ms=0,
                attempts=1,
                status="success",
            ),
        )
        execution = ResearchToolExecutionResult(
            plan_id=plan.plan_id,
            input_bundle_id=bundle.bundle_id,
            output_bundle=final_bundle,
            input_source_ids=[item.source_id for item in bundle.sources],
            new_source_ids=[source.source_id],
            request_results=[
                ToolRequestExecutionResult(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status="succeeded",
                    source_ids=[source.source_id],
                    detail="Synthetic deterministic read completed.",
                    started_at=now,
                    completed_at=now,
                )
            ],
        )
        return ResearchLoopResult(
            run_id=uuid4(),
            initial_bundle_id=bundle.bundle_id,
            final_bundle=final_bundle,
            stop_reason="round_limit_reached",
            tool_requests_used=1,
            rounds=[
                ResearchLoopRound(
                    round_number=1,
                    planning=planning,
                    context_gap=AIContextGapInvocation(
                        result=AIContextGapResult(
                            analysis_mode="reassessment"
                            if bundle.human_review_context
                            else "initial",
                            focus={"scope_refs": ["RD-03"]},
                            supported_facts=[
                                {
                                    "statement": item.content,
                                    "source_ref": item.source_id,
                                    "verification_status": "Located Only",
                                }
                                for item in bundle.sources
                                if item.access_scope == "user_provided"
                            ],
                            information_gaps=[
                                {
                                    "gap_id": gap.gap_id,
                                    "question": gap.description,
                                    "scope_ref": "RD-03",
                                    "needed_source_type": "Material",
                                    "reason": gap.why_needed,
                                }
                            ],
                            control={
                                "target_confirmation_needed": False,
                                "more_information_needed": True,
                            },
                        ),
                        trace=_trace("fake-context-gap"),
                    ),
                    execution=execution,
                )
            ],
        )


class PartialFailureResearchLoop(EnrichingResearchLoop):
    """Acquire useful material, then retain a later bounded timeout."""

    def run(self, bundle, *, local_environment_authorized=False) -> ResearchLoopResult:
        acquired = super().run(
            bundle,
            local_environment_authorized=local_environment_authorized,
        )
        now = datetime.now(UTC)
        request = ToolRequest(
            request_id="request-secondary-page",
            tool_name="search_web",
            gap_ids=["gap-secondary-page"],
            purpose="Read one bounded secondary page.",
            query="example secondary source",
        )
        gap = InformationGap(
            gap_id="gap-secondary-page",
            area="evaluation_conditions",
            state="missing",
            description="A secondary evaluation page was not yet read.",
            why_needed="It may add supporting evaluation context.",
            inspected_source_ids=[source.source_id for source in acquired.final_bundle.sources],
        )
        plan = AIResearchPlanResult(
            plan_id=uuid4(),
            bundle_id=acquired.final_bundle.bundle_id,
            summary="One optional secondary read remains.",
            examined_source_ids=[source.source_id for source in acquired.final_bundle.sources],
            state="needs_tool_calls",
            information_gaps=[gap],
            tool_requests=[request],
        )
        planning = AIResearchPlanInvocation(
            result=plan,
            trace=AIModelTrace(
                trace_id=uuid4(),
                model="fake-research-planner",
                request_id="fake-secondary-request",
                started_at=now,
                completed_at=now,
                duration_ms=0,
                attempts=1,
                status="success",
            ),
        )
        failed_execution = ResearchToolExecutionResult(
            plan_id=plan.plan_id,
            input_bundle_id=acquired.final_bundle.bundle_id,
            output_bundle=acquired.final_bundle,
            input_source_ids=[source.source_id for source in acquired.final_bundle.sources],
            new_source_ids=[],
            request_results=[
                ToolRequestExecutionResult(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status="failed",
                    failure_code="transport_timeout",
                    detail="Synthetic bounded transport timeout.",
                    started_at=now,
                    completed_at=now,
                )
            ],
        )
        return ResearchLoopResult(
            run_id=acquired.run_id,
            initial_bundle_id=acquired.initial_bundle_id,
            final_bundle=acquired.final_bundle,
            stop_reason="partial_material_acquisition",
            tool_requests_used=2,
            rounds=[
                *acquired.rounds,
                ResearchLoopRound(
                    round_number=2,
                    planning=planning,
                    execution=failed_execution,
                ),
            ],
            handoff=ResearchLoopHandoff(
                state="analysis_ready",
                reason="partial_material_acquisition",
            ),
        )


class PassthroughResearchLoop:
    """A complete no-tool phase fixture for tests focused on later boundaries."""

    def run(self, bundle, *, local_environment_authorized=False) -> ResearchLoopResult:
        return ResearchLoopResult(
            run_id=uuid4(),
            initial_bundle_id=bundle.bundle_id,
            final_bundle=bundle,
            stop_reason="ready_for_analysis",
            tool_requests_used=0,
            rounds=[ResearchLoopRound(round_number=1)],
        )


class NoReliableNextSourceResearchLoop:
    """Safe search exhaustion must hand collected material to Evidence/Rule."""

    def run(self, bundle, *, local_environment_authorized=False) -> ResearchLoopResult:
        return ResearchLoopResult(
            run_id=uuid4(),
            initial_bundle_id=bundle.bundle_id,
            final_bundle=bundle,
            stop_reason="no_reliable_next_source",
            tool_requests_used=0,
            rounds=[ResearchLoopRound(round_number=1)],
            handoff=ResearchLoopHandoff(
                state="stopped",
                reason="no_reliable_next_source",
            ),
        )


class RaisingResearchLoop:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def run(self, _bundle, *, local_environment_authorized=False):
        self.calls += 1
        raise self.error


def _request() -> AssessmentRequest:
    return AssessmentRequest(
        target_type="repository",
        target_entry=REPOSITORY_URL,
        environment_mode="later",
    )


def _workflow(
    collector,
    evidence_model,
    _conflict_model,
    *,
    research_loop=None,
    feedback_model=None,
    review_store=None,
):
    service = ReadinessAssessmentService(repository_material_collector=collector)
    return ModelBackedReadinessWorkflowService(
        service,
        evidence_model=evidence_model,
        feedback_model=feedback_model or FeedbackReassessmentStub(),
        research_loop=research_loop or PassthroughResearchLoop(),
        review_store=review_store,
    )


def test_model_backed_main_chain_runs_local_drafts_and_rule_adjudication() -> None:
    collector = StaticRepositoryCollector()
    model = InitialLocalEvidenceFindingModel()
    legacy = EmptyConflictFindingModel()
    assessment = _workflow(collector, model, legacy).create_assessment(_request())
    assert collector.calls == 1
    assert len(model.local_inputs) == 9
    assert legacy.calls == 0
    assert assessment.status == "completed"
    assert assessment.analysis_state is None
    assert assessment.gate_available is True
    assert assessment.overall_gate == "CONDITIONAL PROCEED"
    assert {item.status for item in assessment.dimensions} == {"Unknown"}
    stages = [event.stage for event in assessment.audit_trail]
    assert "ai_local_evidence_finding" in stages
    assert stages.index("ai_local_evidence_finding") < stages.index("rule_adjudication")
    assert assessment.trace_summary[-1].startswith("validate_output: success")
    assert all(event.model_trace_id for event in assessment.audit_trail if event.actor == "ai")


def test_first_assessment_uses_local_evidence_finding_then_rule_when_full_phase_boundary_exists() -> (
    None
):
    evidence_model = InitialLocalEvidenceFindingModel()
    conflict_model = EmptyConflictFindingModel()
    assessment = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        conflict_model,
        research_loop=EnrichingResearchLoop(),
    ).create_assessment(_request())

    assert evidence_model.calls == 0
    assert len(evidence_model.local_inputs) == 9
    assert sorted(item.focus.scope_refs for item in evidence_model.local_inputs) == [
        ["RD-01"],
        ["RD-01"],
        ["RD-01"],
        ["RD-02"],
        ["RD-02"],
        ["RD-02"],
        ["RD-03"],
        ["RD-03"],
        ["RD-03"],
    ]
    assert all(len(item.condition_contexts) == 1 for item in evidence_model.local_inputs)
    assert conflict_model.calls == 0
    assert any("ai_local_evidence_finding: completed" in item for item in assessment.trace_summary)
    assert any("rule_local_evidence_finding: success" in item for item in assessment.trace_summary)
    assert "ai_local_evidence_finding" in [event.stage for event in assessment.audit_trail]
    assert assessment.overall_gate is not None


def test_later_condition_contract_failure_retains_earlier_local_result() -> None:
    evidence_model = FailAfterFirstLocalConditionModel()
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        EmptyConflictFindingModel(),
        research_loop=EnrichingResearchLoop(),
    )

    assessment = workflow.create_assessment(_request())
    session = workflow.human_review_service.store.get(assessment.assessment_id)

    assert assessment.analysis_state == "invalid_model_response"
    assert "schema[handoff:value_error]" in assessment.main_risk
    assert session is not None
    assert "rd01.dataset_identity" in session.state["local_completed_condition_refs"]
    assert "rd01.dataset_access" not in session.state["local_completed_condition_refs"]
    assert session.state["local_analysis"].evidence_candidates
    assert any("completed=8/9" in item for item in session.state["workflow_trace"])


def test_partial_tool_failure_with_prior_material_continues_to_rule() -> None:
    assessment = _workflow(
        StaticRepositoryCollector(),
        InitialLocalEvidenceFindingModel(),
        EmptyConflictFindingModel(),
        research_loop=PartialFailureResearchLoop(),
    ).create_assessment(_request())

    assert assessment.status == "partial"
    assert assessment.analysis_state == "partial_result"
    assert assessment.gate_available is True
    assert assessment.overall_gate is not None
    assert any("stop=partial_material_acquisition" in item for item in assessment.trace_summary)


def test_no_reliable_next_source_continues_with_collected_material() -> None:
    assessment = _workflow(
        StaticRepositoryCollector(),
        InitialLocalEvidenceFindingModel(),
        EmptyConflictFindingModel(),
        research_loop=NoReliableNextSourceResearchLoop(),
    ).create_assessment(_request())

    assert assessment.status == "completed"
    assert assessment.analysis_state is None
    assert assessment.gate_available is True
    assert assessment.overall_gate is not None
    assert any(
        "continuing_with_collected_material=true" in item for item in assessment.trace_summary
    )


def test_rule_generated_missing_finding_retains_verified_context_evidence() -> None:
    """An Unknown must retain real, insufficient material for the Evidence drawer.

    The admitted Evidence below has a verified locator but no admitted Finding.
    Rule must keep it as context on its generated missing-Fact Finding, without
    treating it as proof or changing the Unknown decision.
    """

    assessment = _workflow(
        StaticRepositoryCollector(),
        RetainedFactEvidenceModel(finding=False),
        EmptyConflictFindingModel(),
    ).create_assessment(_request())

    rd01 = next(item for item in assessment.dimensions if item.dimension_id == "RD-01")
    finding = next(
        item for item in rd01.findings if item.finding_id == "rule-missing-rd01.dataset_identity"
    )

    assert rd01.status == "Unknown"
    assert len(finding.evidence) == 1
    assert finding.evidence[0].excerpt == "Project material."
    assert finding.evidence[0].source == "README.md"
    assert finding.evidence[0].line_start == finding.evidence[0].line_end == 2


def test_research_loop_enriches_formal_evidence_input_and_is_audited() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    research_loop = EnrichingResearchLoop()

    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        EmptyConflictFindingModel(),
        research_loop=research_loop,
    )
    assessment = workflow.create_assessment(_request())

    assert research_loop.calls == 1
    assert research_loop.local_environment_authorized is False
    assert ".researchops/checkpoint-search.json" in evidence_model.source_paths[0]
    stages = [event.stage for event in assessment.audit_trail]
    assert stages.index("ai_context_gap") < stages.index("ai_local_evidence_finding")
    assert stages.index("research_tool_execution") < stages.index("ai_local_evidence_finding")
    assert "material_bundle_enriched" in stages
    planning_event = next(
        event for event in assessment.audit_trail if event.stage == "ai_context_gap"
    )
    assert planning_event.provider_request_id == "fake-context-gap"
    session = workflow.human_review_service.store.get(assessment.assessment_id)
    assert session is not None
    context_gap = session.state["research_loop"].rounds[0].context_gap.result
    assert context_gap.analysis_mode == "initial"
    assert session.state["research_loop"].stop_reason == "round_limit_reached"
    assert context_gap.information_gaps
    assert ".researchops/checkpoint-search.json" not in str(context_gap.model_dump())


def test_research_planning_outage_stops_before_evidence_without_business_unknown() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    research_loop = RaisingResearchLoop(AIModelTransportError("synthetic planning outage"))

    assessment = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        EmptyConflictFindingModel(),
        research_loop=research_loop,
    ).create_assessment(_request())

    assert research_loop.calls == 1
    assert evidence_model.calls == 0
    assert assessment.status == "partial"
    assert assessment.analysis_state == "model_unavailable"
    assert assessment.gate_available is False
    assert {dimension.status for dimension in assessment.dimensions} == {None}


def test_model_unavailable_is_technical_partial_not_business_unknown() -> None:
    evidence_model = RaisingEvidenceModel(AIModelTransportError("synthetic outage"))
    conflict_model = EmptyConflictFindingModel()

    assessment = _workflow(
        StaticRepositoryCollector(), evidence_model, conflict_model
    ).create_assessment(_request())

    assert 1 <= evidence_model.calls <= 9
    assert conflict_model.calls == 0
    assert assessment.status == "partial"
    assert assessment.analysis_state == "model_unavailable"
    assert assessment.gate_available is False
    assert assessment.overall_gate is None
    assert {dimension.status for dimension in assessment.dimensions} == {None}
    assert {dimension.analysis_state for dimension in assessment.dimensions} == {
        "model_unavailable"
    }


def test_invalid_model_output_has_its_own_failure_state() -> None:
    secret = "sk-provider-error-secret123456"
    assessment = _workflow(
        StaticRepositoryCollector(),
        RaisingEvidenceModel(AIModelResponseError(f"synthetic invalid JSON api_key={secret}")),
        EmptyConflictFindingModel(),
        research_loop=PassthroughResearchLoop(),
    ).create_assessment(_request())

    assert assessment.status == "partial"
    assert assessment.analysis_state == "invalid_model_response"
    assert assessment.gate_available is False
    assert secret not in assessment.model_dump_json()


def test_missing_model_configuration_has_its_own_failure_state() -> None:
    assessment = _workflow(
        StaticRepositoryCollector(),
        RaisingEvidenceModel(AIModelConfigurationError("synthetic missing key")),
        EmptyConflictFindingModel(),
    ).create_assessment(_request())

    assert assessment.status == "partial"
    assert assessment.analysis_state == "configuration_required"
    assert assessment.gate_available is False


def test_insufficient_model_balance_is_actionable_configuration_state() -> None:
    error = AIModelConfigurationError(
        "safe provider rejection",
        trace=AIModelTrace(
            trace_id=uuid4(),
            model="deepseek-flash",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_ms=1,
            attempts=1,
            status="failed",
            error_type="http_402",
        ),
    )
    assessment = _workflow(
        StaticRepositoryCollector(),
        RaisingEvidenceModel(error),
        EmptyConflictFindingModel(),
    ).create_assessment(_request())

    assert assessment.analysis_state == "configuration_required"
    assert "insufficient balance" in assessment.main_risk
    assert assessment.overall_gate is None


def test_later_local_model_failure_does_not_fabricate_a_gate() -> None:
    class LaterOutage(InitialLocalEvidenceFindingModel):
        def draft_evidence_findings(self, context):
            if context.condition_contexts[0].condition_ref == "rd01.dataset_access":
                raise AIModelTransportError("synthetic later condition outage")
            return super().draft_evidence_findings(context)

    assessment = _workflow(
        StaticRepositoryCollector(), LaterOutage(), EmptyConflictFindingModel()
    ).create_assessment(_request())
    assert assessment.status == "partial"
    assert assessment.analysis_state == "model_unavailable"
    assert assessment.gate_available is False
    assert assessment.overall_gate is None


def test_ambiguous_evidence_becomes_unknown_without_blocking_gate_formation() -> None:
    assessment = _workflow(
        StaticRepositoryCollector(),
        AmbiguousEvidenceModel(),
        EmptyConflictFindingModel(),
    ).create_assessment(_request())

    assert assessment.status == "completed"
    assert assessment.analysis_state is None
    assert assessment.gate_available is True
    assert assessment.overall_gate == "CONDITIONAL PROCEED"
    assert {dimension.status for dimension in assessment.dimensions} == {"Unknown"}


def test_material_acquisition_failure_stops_before_either_model_stage() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    conflict_model = EmptyConflictFindingModel()

    assessment = _workflow(
        FailingRepositoryCollector(), evidence_model, conflict_model
    ).create_assessment(_request())

    assert evidence_model.calls == conflict_model.calls == 0
    assert assessment.status == "partial"
    assert assessment.analysis_state == "acquisition_failure"
    assert assessment.gate_available is False


def test_supplemental_material_is_sent_back_to_ai_as_user_provided_data() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    workflow = _workflow(StaticRepositoryCollector(), evidence_model, EmptyConflictFindingModel())
    initial = workflow.create_assessment(_request())
    finding_id = initial.dimensions[0].findings[0].finding_id

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding_id,
            action="supplement",
            comment="Add the maintainer-provided checkpoint note.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Maintainer clarification",
                source_path="user/maintainer-clarification.txt",
                content="The public checkpoint must be used with the base configuration.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert evidence_model.calls == 10
    assert "user_provided" not in evidence_model.source_scopes[0]
    assert "user_provided" in evidence_model.source_scopes[-1]
    assert response.feedback.requires_reassessment is True


def test_targeted_evidence_reassessment_can_reuse_existing_material_when_user_points_to_it() -> (
    None
):
    evidence_model = RetainedFactEvidenceModel()
    interpretation_model = ObserveRetainedEvidenceModel()
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        interpretation_model,
    )
    initial = workflow.create_assessment(_request())
    initial_finding = next(
        finding
        for finding in initial.dimensions[0].findings
        if finding.condition == "rd01.dataset_identity"
    )
    assert initial_finding.evidence
    initial_evidence = initial_finding.evidence[0]

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="evidence",
            target_id=initial_evidence.evidence_id,
            action="supplement",
            comment="Add a first-party clarification.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer clarification",
                source_path="user/access.txt",
                content="The customer can access the dataset.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert response.reassessment_state == "completed"
    assert initial_evidence.evidence_id in {
        item.local_evidence_id for item in evidence_model.local_inputs[-1].related_evidence
    }
    assert evidence_model.review_contexts[-1].target_id == initial_evidence.evidence_id
    assert (
        evidence_model.review_contexts[-1].original_finding.finding_id == initial_finding.finding_id
    )
    assert (
        evidence_model.review_contexts[-1].original_evidence.evidence_id
        == initial_evidence.evidence_id
    )
    assert interpretation_model.calls == 0
    assert initial_evidence.evidence_id in {
        evidence.evidence_id
        for dimension in response.assessment.dimensions
        for finding in dimension.findings
        for evidence in finding.evidence
    }


def test_targeted_evidence_reassessment_replaces_finding_with_user_feedback_evidence() -> None:
    evidence_model = RetainedFactEvidenceModel(replace_on_feedback=True)
    interpretation_model = ObserveRetainedEvidenceModel(replace_on_feedback=True)
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        interpretation_model,
    )
    initial = workflow.create_assessment(_request())
    initial_finding = next(
        finding
        for dimension in initial.dimensions
        for finding in dimension.findings
        if finding.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="evidence",
            target_id=initial_finding.evidence[0].evidence_id,
            action="supplement",
            comment="The customer confirms the corrected dataset identity.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer dataset correction",
                source_path="user/dataset-correction.txt",
                content="The required dataset identity is customer-confirmed.",
            ),
        ),
    )

    revised = next(
        finding
        for dimension in response.assessment.dimensions
        for finding in dimension.findings
        if finding.condition == "rd01.dataset_identity"
    )
    assert response.reassessment_performed is True
    assert response.reassessment_state == "completed"
    assert revised.finding_id == initial_finding.finding_id
    assert any(
        item.excerpt == "The required dataset identity is customer-confirmed."
        and item.source_type == "User Context"
        for item in revised.evidence
    )
    assert any(
        item.evidence_id == initial_finding.evidence[0].evidence_id for item in revised.evidence
    )


def test_feedback_reassessment_survives_api_process_restart(tmp_path) -> None:
    store = DurableAssessmentReviewStore(directory=tmp_path, ttl_seconds=60)
    initial_workflow = _workflow(
        StaticRepositoryCollector(),
        LocalFeedbackEvidenceModel(),
        ObserveRetainedEvidenceModel(),
        research_loop=PassthroughResearchLoop(),
        feedback_model=DependentFeedbackReassessmentStub(),
        review_store=store,
    )
    initial = initial_workflow.create_assessment(_request())
    initial_finding = next(
        finding
        for dimension in initial.dimensions
        for finding in dimension.findings
        if finding.condition == "rd01.dataset_identity"
    )

    restarted_workflow = _workflow(
        StaticRepositoryCollector(),
        LocalFeedbackEvidenceModel(),
        ObserveRetainedEvidenceModel(),
        research_loop=PassthroughResearchLoop(),
        feedback_model=DependentFeedbackReassessmentStub(),
        review_store=DurableAssessmentReviewStore(directory=tmp_path, ttl_seconds=60),
    )
    recovered = restarted_workflow.get_assessment(initial.assessment_id)
    response = restarted_workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=initial_finding.finding_id,
            action="supplement",
            comment="The customer confirms the corrected dataset identity.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer dataset correction",
                source_path="user/dataset-correction.txt",
                content="The required dataset identity is customer-confirmed.",
            ),
        ),
    )

    assert recovered.assessment_id == initial.assessment_id
    assert response.reassessment_performed is True
    assert response.reassessment_state == "completed"


def test_local_feedback_reassesses_only_declared_dependency_scope_and_retains_evidence() -> None:
    evidence_model = LocalFeedbackEvidenceModel()
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        ObserveRetainedEvidenceModel(),
        research_loop=PassthroughResearchLoop(),
        feedback_model=DependentFeedbackReassessmentStub(),
    )
    initial = workflow.create_assessment(_request())
    finding = next(
        item
        for dimension in initial.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding.finding_id,
            action="supplement",
            comment="Customer confirms the related operational fact.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer confirmation",
                source_path="user/customer-confirmation.txt",
                content="The customer confirms the dataset fact.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert len(evidence_model.local_inputs) == 1
    context = evidence_model.local_inputs[0]
    assert context.focus.scope_refs == ["RD-01"]
    assert context.condition_contexts[0].related_dimensions == ["RD-02"]
    initial_evidence_ids = {
        evidence.evidence_id
        for dimension in initial.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
        for evidence in item.evidence
    }
    assert {item.local_evidence_id for item in context.related_evidence} == initial_evidence_ids
    revised = next(
        item
        for dimension in response.assessment.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
    )
    assert initial_evidence_ids <= {item.evidence_id for item in revised.evidence}
    assert any(item.source_type == "User Context" for item in revised.evidence)
    assert next(
        item for item in response.assessment.dimensions if item.dimension_id == "RD-03"
    ) == next(item for item in initial.dimensions if item.dimension_id == "RD-03")
    assert response.assessment.overall_gate is not None
    assert any("human_local_rule" in item for item in response.assessment.trace_summary)


def test_failed_local_feedback_keeps_the_prior_assessment_revision() -> None:
    workflow = _workflow(
        StaticRepositoryCollector(),
        FailingLocalFeedbackEvidenceModel(),
        ObserveRetainedEvidenceModel(),
    )
    initial = workflow.create_assessment(_request())
    finding = next(
        item
        for dimension in initial.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding.finding_id,
            action="supplement",
            comment="Customer provides a correction.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer confirmation",
                source_path="user/customer-confirmation.txt",
                content="The customer confirms the dataset fact.",
            ),
        ),
    )

    assert response.reassessment_performed is False
    assert response.reassessment_state == "invalid_model_response"
    assert response.assessment == initial


def test_user_source_reassessment_continues_when_feedback_scope_model_is_invalid() -> None:
    """A malformed triage response cannot strand an explicit user supplement."""

    workflow = _workflow(
        StaticRepositoryCollector(),
        RetainedFactEvidenceModel(replace_on_feedback=True),
        ObserveRetainedEvidenceModel(replace_on_feedback=True),
        feedback_model=InvalidFeedbackReassessmentStub(),
    )
    initial = workflow.create_assessment(_request())
    initial_finding = next(
        finding
        for dimension in initial.dimensions
        for finding in dimension.findings
        if finding.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="evidence",
            target_id=initial_finding.evidence[0].evidence_id,
            action="supplement",
            comment="The customer confirms the corrected dataset identity.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer dataset correction",
                source_path="user/dataset-correction.txt",
                content="The required dataset identity is customer-confirmed.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert response.reassessment_state == "completed"
    assert any(
        "continued with the user-selected target" in item
        for item in response.assessment.trace_summary
    )


def test_feedback_reassessment_runs_bounded_research_before_reextracting_evidence() -> None:
    evidence_model = RetainedFactEvidenceModel(replace_on_feedback=True)
    interpretation_model = ObserveRetainedEvidenceModel(replace_on_feedback=True)
    research_loop = EnrichingResearchLoop()
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        interpretation_model,
        research_loop=research_loop,
        feedback_model=FeedbackReassessmentStub(handoff="tool_acquisition"),
    )
    initial = workflow.create_assessment(_request())
    finding = next(
        item
        for dimension in initial.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="evidence",
            target_id=finding.evidence[0].evidence_id,
            action="supplement",
            comment="The customer confirms access and asks ResearchOps to check the checkpoint.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer access clarification",
                source_path="user/access-clarification.txt",
                content="The customer can access the required dataset.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert research_loop.calls == 2
    assert research_loop.review_contexts[1] is not None
    assert research_loop.review_contexts[1].target_id == finding.evidence[0].evidence_id
    assert ".researchops/checkpoint-search.json" in evidence_model.source_paths[-1]
    assert any(
        "human_research_materials: completed" in item for item in response.assessment.trace_summary
    )
    session = workflow.human_review_service.store.get(initial.assessment_id)
    assert session is not None
    context_gap = session.state["research_loop"].rounds[0].context_gap.result
    assert context_gap.analysis_mode == "reassessment"
    assert session.state["research_loop"].stop_reason == "round_limit_reached"
    assert any(
        item.statement == "The customer can access the required dataset."
        for item in context_gap.supported_facts
    )


def test_question_with_new_user_material_reassesses_but_plain_question_does_not() -> None:
    evidence_model = RetainedFactEvidenceModel(replace_on_feedback=True)
    workflow = _workflow(
        StaticRepositoryCollector(),
        evidence_model,
        ObserveRetainedEvidenceModel(replace_on_feedback=True),
    )
    initial = workflow.create_assessment(_request())
    finding = next(
        item
        for dimension in initial.dimensions
        for item in dimension.findings
        if item.condition == "rd01.dataset_identity"
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding.finding_id,
            action="question",
            comment="Does the customer-provided access fact resolve this condition?",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Customer access fact",
                source_path="user/access-fact.txt",
                content="The customer can access the required dataset.",
            ),
        ),
    )

    assert response.feedback.requires_reassessment is True
    assert response.reassessment_performed is True
    assert evidence_model.calls == 10


def test_rule_generated_question_accepts_first_feedback_and_reassesses() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    workflow = _workflow(StaticRepositoryCollector(), evidence_model, EmptyConflictFindingModel())
    initial = workflow.create_assessment(_request())
    question_finding = next(
        finding
        for dimension in initial.dimensions
        for finding in dimension.findings
        if finding.finding_id.startswith("rule-missing-")
    )

    response = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=question_finding.finding_id,
            action="supplement",
            comment="Add user-provided dataset access context.",
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="Dataset access statement",
                source_path="user/dataset-access.txt",
                content="The user reports access to the dataset for this assessment.",
            ),
        ),
    )

    assert response.reassessment_performed is True
    assert response.feedback.target_type == "finding"
    assert response.feedback.target_id == question_finding.finding_id
    assert evidence_model.calls == 10


def test_displayed_finding_accepts_repeated_confirm_and_question_feedback() -> None:
    evidence_model = QuestionOnlyEvidenceModel()
    workflow = _workflow(StaticRepositoryCollector(), evidence_model, EmptyConflictFindingModel())
    initial = workflow.create_assessment(_request())
    finding_id = initial.dimensions[0].findings[0].finding_id

    confirmed = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding_id,
            action="accept",
        ),
    )
    questioned = workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding_id,
            action="question",
            comment="Please review whether this missing fact is still relevant.",
        ),
    )

    assert confirmed.revision == 1
    assert questioned.revision == 2
    assert confirmed.reassessment_performed is False
    assert questioned.reassessment_performed is False
    assert evidence_model.calls == 9


def test_assessment_revision_history_retains_prior_assessments_and_feedback_diffs() -> None:
    workflow = _workflow(
        StaticRepositoryCollector(), QuestionOnlyEvidenceModel(), EmptyConflictFindingModel()
    )
    initial = workflow.create_assessment(_request())
    finding_id = initial.dimensions[0].findings[0].finding_id

    workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding_id,
            action="accept",
        ),
    )
    workflow.submit_feedback(
        initial.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=finding_id,
            action="question",
            comment="Please retain this question for review.",
        ),
    )

    history = workflow.get_assessment_revision_history(initial.assessment_id)

    assert [item.revision for item in history.revisions] == [0, 1, 2]
    assert history.revisions[0].feedback is None
    assert history.revisions[1].feedback.action == "accept"
    assert history.revisions[2].feedback.action == "question"
    assert [(item.from_revision, item.to_revision) for item in history.changes] == [
        (0, 1),
        (1, 2),
    ]
    assert all(change.overall_gate_changed is False for change in history.changes)


def test_final_human_decision_is_recorded_without_overwriting_rule_gate() -> None:
    workflow = _workflow(
        StaticRepositoryCollector(), QuestionOnlyEvidenceModel(), EmptyConflictFindingModel()
    )
    assessment = workflow.create_assessment(_request())

    decision = workflow.record_final_decision(
        assessment.assessment_id,
        FinalInvestmentDecisionRequest(
            decision="decline",
            rationale="The unresolved setup cost is outside the current budget.",
        ),
    )
    retained = workflow.human_review_service.store.get(assessment.assessment_id)

    assert decision.decision == "decline"
    assert decision.rule_gate_at_decision == assessment.overall_gate
    assert decision.gate_available_at_decision is True
    assert retained.state["assessment"].overall_gate == assessment.overall_gate
    assert retained.final_decisions == [decision]
    latest = workflow.get_assessment(assessment.assessment_id)
    final_event = latest.audit_trail[-1]
    assert final_event.actor == "human"
    assert final_event.stage == "final_investment_decision"
    assert "outside the current budget" not in final_event.model_dump_json()
