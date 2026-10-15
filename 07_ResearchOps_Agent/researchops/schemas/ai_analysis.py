"""AI material understanding contracts separated from deterministic adjudication.

The models in this module intentionally stop before final Readiness statuses and
Overall Gate values. Model output is an untrusted set of candidates; deterministic
validation and adjudication remain separate responsibilities.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from researchops.schemas.readiness import (
    DimensionId,
    Evidence,
    EvidenceConflict,
    EvidenceSourceType,
    EvidenceVerificationStatus,
    Finding,
    FindingType,
    MaterialType,
    OverallGate,
    ReadinessAssessment,
    ResolvedTarget,
)
from researchops.schemas.task import StrictModel

MaterialAccessScope = Literal["public", "authorized_local", "user_provided"]
ResearchToolName = Literal[
    "search_web",
    "fetch_web_page",
    "search_github",
    "read_github_repository",
    "read_github_file",
    "read_huggingface_card",
    "fetch_paper",
    "probe_dataset_access",
    "probe_checkpoint_access",
    "inspect_local_environment",
]
InformationGapState = Literal["missing", "ambiguous", "needs_fresh_verification"]
ResearchPlanState = Literal["needs_tool_calls", "ready_for_analysis", "needs_user_input"]
ResearchToolExecutionStatus = Literal[
    "succeeded", "denied", "not_configured", "failed", "skipped"
]
ResearchToolFailureCode = Literal[
    "policy_denied",
    "provider_not_configured",
    "invalid_tool_argument",
    "transport_timeout",
    "remote_access_failed",
    "target_not_found",
    "bounded_capacity_exhausted",
    "connector_failure",
    "not_needed",
]
ResearchLoopStopReason = Literal[
    "ready_for_analysis",
    "needs_user_input",
    "authorization_required",
    "round_limit_reached",
    "tool_request_limit_reached",
    "no_new_material",
    "repeated_information_gaps",
    "no_reliable_next_source",
    "tool_acquisition_failed",
    "partial_material_acquisition",
]
MaterialOmissionReason = Literal[
    "empty",
    "duplicate",
    "binary",
    "oversized",
    "source_limit",
    "total_limit",
]
EvidenceCandidateType = Literal["Fact", "Inference", "Unknown"]
EvidenceAnalysisArea = Literal[
    "rd01_data_access",
    "rd02_environment_dependency",
    "rd03_weights_configuration",
    "resource_constraint",
    "evaluation_conditions",
]
EvidenceCoverageState = Literal["evidence_found", "uncertain", "not_found"]
AnalysisScopeRef = Literal[
    "RD-01",
    "RD-02",
    "RD-03",
    "resource_constraint",
    "evaluation_conditions",
]
AcquisitionAlternativeInput = Literal["snapshot", "manual"]
AcquisitionStopReason = Literal[
    "round_limit",
    "request_budget_exhausted",
    "no_available_tool",
    "confirmation_required",
    "authorization_required",
    "no_reliable_next_source",
    "acquisition_failed",
]
ReadinessCriterionId = Literal[
    "rd01.dataset_identity",
    "rd01.dataset_access",
    "rd01.input_contract",
    "rd02.software_requirements",
    "rd02.dependency_requirements",
    "rd02.environment_compatibility",
    "rd03.checkpoint_access",
    "rd03.configuration_mapping",
    "rd03.execution_contract",
    "resource.minimum_requirements",
    "resource.current_capacity",
    "evaluation.dataset_split",
    "evaluation.metric_definition",
    "evaluation.aggregation",
    "evaluation.paper_code_setting",
    "evaluation.protocol",
]
ReadinessEffectCandidate = Literal[
    "condition_supported",
    "non_blocking_risk",
    "condition_not_met",
    "insufficient_or_conflicting",
]
ConflictDispositionCandidate = Literal[
    "known_difference",
    "authoritative_value_unresolved",
]
AIModelTraceStatus = Literal["success", "failed"]
AIAnalysisRunState = Literal[
    "completed",
    "configuration_required",
    "model_unavailable",
    "invalid_model_response",
]
AIAnalysisRunErrorCode = Literal[
    "llm_configuration_required",
    "llm_provider_unavailable",
    "llm_response_invalid",
]
EvidenceValidationDecision = Literal[
    "accepted",
    "downgraded",
    "rejected",
    "needs_human_confirmation",
]
EvidenceValidationIssueCode = Literal[
    "source_missing",
    "source_not_examined",
    "source_truncated",
    "quote_missing",
    "quote_mismatch",
    "location_mismatch",
    "ambiguous_location",
    "claim_exceeds_source",
    "unsupported_inference",
    "ambiguous_relationship",
    "url_not_in_collected_sources",
    "external_probe_unsupported",
    "external_access_unconfirmed",
    "external_access_inaccessible",
    "external_acquisition_failure",
    "human_rejected",
    "other",
]
ExternalEvidenceKind = Literal["dataset_access", "checkpoint_access"]
ExternalEvidenceVerificationState = Literal[
    "verified_public",
    "public_page_only",
    "account_required",
    "approval_required",
    "verified_inaccessible",
    "acquisition_failure",
    "unsupported",
]
HumanFeedbackAction = Literal["accept", "question", "correct", "supplement"]
HumanFeedbackTarget = Literal["evidence", "finding"]
HumanReassessmentState = Literal[
    "not_required",
    "completed",
    "configuration_required",
    "model_unavailable",
    "invalid_model_response",
    "evidence_validation_failure",
]
FinalInvestmentDecisionValue = Literal[
    "proceed",
    "proceed_with_conditions",
    "pause",
    "decline",
]
CandidateAdjudicationDecision = Literal[
    "accepted",
    "downgraded",
    "rejected",
    "needs_human_confirmation",
]
CandidateGraphIssueCode = Literal[
    "evidence_not_accepted",
    "evidence_needs_human_confirmation",
    "evidence_not_fact",
    "condition_mismatch",
    "criterion_mismatch",
    "dimension_mismatch",
    "insufficient_distinct_sources",
    "non_conflicting_evidence",
    "finding_strength_downgraded",
    "unknown_evidence_cannot_support_conclusion",
]

MAX_AI_EVIDENCE_CANDIDATES = 32
MAX_AI_UNRESOLVED_QUESTIONS = 16
MAX_AI_CONFLICT_CANDIDATES = 16
MAX_AI_FINDING_CANDIDATES = 24
# The production first pass runs one bounded local model call per core
# Dimension. The merged Rule handoff must retain all three bounded batches;
# these are aggregate limits, not larger per-call model allowances.
MAX_MERGED_EVIDENCE_CANDIDATES = MAX_AI_EVIDENCE_CANDIDATES * 3
MAX_MERGED_UNRESOLVED_QUESTIONS = MAX_AI_UNRESOLVED_QUESTIONS * 3
MAX_MERGED_CONFLICT_CANDIDATES = MAX_AI_CONFLICT_CANDIDATES * 3
MAX_MERGED_FINDING_CANDIDATES = MAX_AI_FINDING_CANDIDATES * 3


class MaterialSource(StrictModel):
    """One bounded, addressable source supplied to the model as untrusted data."""

    source_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    material_type: MaterialType
    title: str = Field(min_length=1, max_length=500)
    source_path: str = Field(min_length=1, max_length=1000)
    source_url: HttpUrl | None = None
    content: str = Field(min_length=1, max_length=100_000)
    content_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    original_content_sha256: str | None = Field(
        default=None,
        pattern=r"^[A-Fa-f0-9]{64}$",
    )
    original_char_count: int | None = Field(default=None, ge=1)
    is_truncated: bool = False
    is_redacted: bool = False
    redaction_count: int = Field(default=0, ge=0)
    chunk_index: int = Field(default=1, ge=1)
    chunk_count: int = Field(default=1, ge=1)
    line_start: int = Field(default=1, ge=1)
    line_end: int = Field(default=1, ge=1)
    trust_boundary: Literal["untrusted_data"] = "untrusted_data"
    access_scope: MaterialAccessScope

    @model_validator(mode="after")
    def validate_truncation_metadata(self) -> "MaterialSource":
        actual_hash = sha256(self.content.encode("utf-8")).hexdigest()
        if self.content_sha256.casefold() != actual_hash:
            raise ValueError("content_sha256 必须匹配 MaterialSource 实际内容")
        if self.line_end < self.line_start:
            raise ValueError("MaterialSource line_end 不得小于 line_start")
        if self.chunk_index > self.chunk_count:
            raise ValueError("MaterialSource chunk_index 不得大于 chunk_count")
        if self.is_redacted != (self.redaction_count > 0):
            raise ValueError("MaterialSource 脱敏状态必须与 redaction_count 一致")
        if self.is_truncated or self.is_redacted:
            if self.original_content_sha256 is None or self.original_char_count is None:
                raise ValueError("截断或脱敏的 MaterialSource 必须保留原始哈希和字符数")
        if self.is_truncated and self.original_char_count is not None:
            if self.original_char_count <= len(self.content) and not self.is_redacted:
                raise ValueError("截断材料的 original_char_count 必须大于当前内容长度")
        elif self.original_char_count is not None and self.original_char_count != len(self.content):
            if not self.is_redacted:
                raise ValueError("未截断且未脱敏材料的 original_char_count 必须等于当前内容长度")
        if (
            not self.is_truncated
            and not self.is_redacted
            and self.original_content_sha256 is not None
            and self.original_content_sha256.casefold() != actual_hash
        ):
            raise ValueError("未截断且未脱敏材料的原始哈希必须匹配当前内容")
        return self


class CollectedMaterial(StrictModel):
    """One normalized input from a deterministic connector or user submission."""

    material_type: MaterialType
    title: str = Field(min_length=1, max_length=500)
    source_path: str = Field(min_length=1, max_length=1000)
    source_url: HttpUrl | None = None
    content: str = Field(max_length=2_000_000)
    access_scope: MaterialAccessScope
    priority: int = Field(default=50, ge=0, le=100)


class MaterialBuildOmission(StrictModel):
    """A source excluded from a bounded bundle for one explicit reason."""

    source_path: str = Field(min_length=1, max_length=1000)
    reason: MaterialOmissionReason


class MaterialBundleBuildReport(StrictModel):
    """Deterministic accounting for context selection and truncation."""

    candidate_source_count: int = Field(ge=0)
    included_source_count: int = Field(ge=1, le=64)
    included_material_count: int = Field(ge=1)
    generated_chunk_count: int = Field(ge=1)
    omitted_chunk_count: int = Field(default=0, ge=0)
    included_char_count: int = Field(ge=1, le=500_000)
    truncated_source_ids: list[str] = Field(default_factory=list)
    redacted_source_ids: list[str] = Field(default_factory=list)
    omissions: list[MaterialBuildOmission] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_build_accounting(self) -> "MaterialBundleBuildReport":
        if self.candidate_source_count != self.included_material_count + len(self.omissions):
            raise ValueError("候选材料数必须等于已纳入原始材料数与省略记录数之和")
        if self.included_source_count + self.omitted_chunk_count > self.generated_chunk_count:
            raise ValueError("纳入与省略的分块数不得超过已生成分块数")
        if len(self.truncated_source_ids) != len(set(self.truncated_source_ids)):
            raise ValueError("truncated_source_ids 不得重复")
        if len(self.redacted_source_ids) != len(set(self.redacted_source_ids)):
            raise ValueError("redacted_source_ids 不得重复")
        return self


class MaterialBundleBuildResult(StrictModel):
    """A bounded model input plus the accounting needed for audit and UI."""

    bundle: "MaterialBundle"
    report: MaterialBundleBuildReport

    @model_validator(mode="after")
    def validate_bundle_accounting(self) -> "MaterialBundleBuildResult":
        if self.report.included_source_count != len(self.bundle.sources):
            raise ValueError("BuildReport 的材料数必须匹配 Bundle")
        if self.report.included_char_count != sum(
            len(source.content) for source in self.bundle.sources
        ):
            raise ValueError("BuildReport 的字符数必须匹配 Bundle")
        expected_truncated = {
            source.source_id for source in self.bundle.sources if source.is_truncated
        }
        if set(self.report.truncated_source_ids) != expected_truncated:
            raise ValueError("BuildReport 的截断记录必须匹配 Bundle")
        expected_redacted = {
            source.source_id for source in self.bundle.sources if source.is_redacted
        }
        if set(self.report.redacted_source_ids) != expected_redacted:
            raise ValueError("BuildReport 的脱敏记录必须匹配 Bundle")
        return self


class HumanReviewContext(StrictModel):
    """The exact prior result and user instruction for a targeted reassessment."""

    target_type: HumanFeedbackTarget
    target_id: str = Field(min_length=1, max_length=100)
    action: HumanFeedbackAction
    comment: str | None = Field(default=None, min_length=1, max_length=4000)
    original_finding: Finding | None = None
    original_evidence: Evidence | None = None

    @model_validator(mode="after")
    def validate_target_snapshot(self) -> "HumanReviewContext":
        if self.target_type == "finding" and self.original_finding is None:
            raise ValueError("Finding 定向重判必须携带原始 Finding")
        if self.target_type == "evidence" and self.original_evidence is None:
            raise ValueError("Evidence 定向重判必须携带原始 Evidence")
        if (
            self.original_finding is not None
            and self.original_evidence is not None
            and self.original_evidence.evidence_id
            not in {item.evidence_id for item in self.original_finding.evidence}
        ):
            raise ValueError("原始 Evidence 必须属于随附的原始 Finding")
        return self


class FeedbackReassessmentScope(StrictModel):
    """AI-proposed impact scope; Rule still owns final adjudication."""

    finding_refs: list[str] = Field(default_factory=list, max_length=18)
    evidence_refs: list[str] = Field(default_factory=list, max_length=32)
    dimension_refs: list[DimensionId] = Field(default_factory=list, max_length=3)
    signal_refs: list[Literal["resource_constraint", "evaluation_conditions"]] = Field(
        default_factory=list, max_length=2
    )


class AIFeedbackReassessmentResult(StrictModel):
    """Independent AI feedback triage before acquisition or Evidence analysis."""

    reassessment_id: UUID
    bundle_id: UUID
    contract_version: Literal["1.0"] = "1.0"
    reassessment_required: bool
    affected_scope: FeedbackReassessmentScope
    change_summary: str = Field(min_length=1, max_length=2000)
    information_gaps: list[InformationGap] = Field(default_factory=list, max_length=16)
    handoff: Literal["no_change", "tool_acquisition", "evidence_finding"]

    @model_validator(mode="after")
    def validate_handoff(self) -> "AIFeedbackReassessmentResult":
        scope_is_empty = not any(
            (
                self.affected_scope.finding_refs,
                self.affected_scope.evidence_refs,
                self.affected_scope.dimension_refs,
                self.affected_scope.signal_refs,
            )
        )
        if self.reassessment_required and scope_is_empty:
            raise ValueError("需要重判时必须标明至少一个受影响范围")
        if not self.reassessment_required and (
            self.information_gaps or self.handoff != "no_change"
        ):
            raise ValueError("无需重判时不得生成 Gap 或后续 handoff")
        if self.handoff == "tool_acquisition" and not self.information_gaps:
            raise ValueError("工具获取 handoff 必须包含至少一个 InformationGap")
        if self.handoff == "no_change" and self.reassessment_required:
            raise ValueError("需要重判时不得返回 no_change")
        return self


class MaterialBundle(StrictModel):
    """Bounded source collection passed across the collector-to-AI boundary."""

    bundle_id: UUID
    target: ResolvedTarget
    assembled_at: datetime
    sources: list[MaterialSource] = Field(min_length=1, max_length=64)
    human_review_context: HumanReviewContext | None = None

    @model_validator(mode="after")
    def validate_source_identity_and_size(self) -> "MaterialBundle":
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("MaterialBundle source_id 必须唯一")
        if sum(len(source.content) for source in self.sources) > 500_000:
            raise ValueError("MaterialBundle 总文本长度不得超过 500000 字符")
        return self


class InformationGap(StrictModel):
    """One bounded information gap identified by AI before evidence analysis."""

    gap_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    area: EvidenceAnalysisArea
    criterion_id: ReadinessCriterionId | None = None
    state: InformationGapState
    description: str = Field(min_length=1, max_length=1000)
    why_needed: str = Field(min_length=1, max_length=1000)
    inspected_source_ids: list[str] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_inspected_sources(self) -> "InformationGap":
        if len(self.inspected_source_ids) != len(set(self.inspected_source_ids)):
            raise ValueError("InformationGap inspected_source_ids 不得重复")
        return self


class ToolRequest(StrictModel):
    """AI-requested capability call; a policy executor must authorize and run it."""

    request_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    tool_name: ResearchToolName
    gap_ids: list[str] = Field(min_length=1, max_length=16)
    purpose: str = Field(min_length=1, max_length=1000)
    query: str | None = Field(default=None, min_length=1, max_length=1000)
    url: HttpUrl | None = None
    identifier: str | None = Field(default=None, min_length=1, max_length=500)
    requires_user_authorization: bool = False

    @model_validator(mode="after")
    def validate_tool_arguments(self) -> "ToolRequest":
        if len(self.gap_ids) != len(set(self.gap_ids)):
            raise ValueError("ToolRequest gap_ids 不得重复")

        search_tools = {"search_web", "search_github"}
        url_tools = {
            "fetch_web_page",
            "read_github_repository",
            "read_github_file",
            "read_huggingface_card",
            "probe_dataset_access",
            "probe_checkpoint_access",
        }
        if self.tool_name in search_tools:
            valid = self.query is not None and self.url is None and self.identifier is None
        elif self.tool_name in url_tools:
            valid = self.url is not None and self.query is None and self.identifier is None
        elif self.tool_name == "fetch_paper":
            valid = self.identifier is not None and self.query is None and self.url is None
        else:
            valid = self.query is None and self.url is None and self.identifier is None
            if not self.requires_user_authorization:
                raise ValueError("inspect_local_environment 必须声明需要用户授权")
        if not valid:
            raise ValueError("ToolRequest 参数与 tool_name 不匹配")
        if self.tool_name != "inspect_local_environment" and self.requires_user_authorization:
            raise ValueError("只有本机环境检查可以在规划阶段声明用户授权")
        return self


class AIResearchPlanResult(StrictModel):
    """AI gap analysis and bounded tool requests before evidence extraction."""

    plan_id: UUID
    bundle_id: UUID
    contract_version: Literal["1.0"] = "1.0"
    summary: str = Field(min_length=1, max_length=2000)
    examined_source_ids: list[str] = Field(min_length=1, max_length=64)
    state: ResearchPlanState
    information_gaps: list[InformationGap] = Field(default_factory=list, max_length=16)
    tool_requests: list[ToolRequest] = Field(default_factory=list, max_length=12)
    user_question: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_plan_graph(self) -> "AIResearchPlanResult":
        if len(self.examined_source_ids) != len(set(self.examined_source_ids)):
            raise ValueError("Research Plan examined_source_ids 不得重复")
        gap_ids = [gap.gap_id for gap in self.information_gaps]
        request_ids = [request.request_id for request in self.tool_requests]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("Research Plan gap_id 不得重复")
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("Research Plan request_id 不得重复")
        known_gap_ids = set(gap_ids)
        if any(not set(request.gap_ids) <= known_gap_ids for request in self.tool_requests):
            raise ValueError("ToolRequest 引用了不存在的 InformationGap")
        if any(
            not set(gap.inspected_source_ids) <= set(self.examined_source_ids)
            for gap in self.information_gaps
        ):
            raise ValueError("InformationGap 引用了未检查的 MaterialSource")
        if self.state == "needs_tool_calls":
            if not self.tool_requests:
                raise ValueError("needs_tool_calls 必须包含 ToolRequest")
            if self.user_question is not None:
                raise ValueError("needs_tool_calls 不得同时要求用户回答")
        elif self.state == "ready_for_analysis":
            if self.information_gaps or self.tool_requests or self.user_question is not None:
                raise ValueError(
                    "ready_for_analysis 不得包含 InformationGap、ToolRequest 或用户问题"
                )
        else:
            if not self.information_gaps:
                raise ValueError("needs_user_input 必须包含 InformationGap")
            if not self.user_question:
                raise ValueError("needs_user_input 必须提供 user_question")
            if self.tool_requests:
                raise ValueError("needs_user_input 不得同时包含 ToolRequest")
        return self


class ToolAcquisitionPlan(StrictModel):
    """Rule-bound handoff from known gaps to minimum deterministic reads.

    This artifact contains no Tool Result and introduces no new InformationGap.
    """

    acquisition_id: UUID
    bundle_id: UUID
    source_plan_id: UUID
    gap_ids: list[str] = Field(default_factory=list, max_length=16)
    state: Literal[
        "tool_request",
        "human_confirmation",
        "authorization_required",
        "stop_acquisition",
    ]
    requests: list[ToolRequest] = Field(default_factory=list, max_length=12)
    stop_reason: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_acquisition_plan(self) -> "ToolAcquisitionPlan":
        if len(self.gap_ids) != len(set(self.gap_ids)):
            raise ValueError("ToolAcquisitionPlan gap_ids 不得重复")
        if self.state == "tool_request":
            if not self.requests or self.stop_reason is not None:
                raise ValueError("tool_request 必须有请求且不得携带停止原因")
        elif self.requests:
            raise ValueError("非 tool_request 的获取计划不得携带工具请求")
        elif self.stop_reason is None:
            raise ValueError("非 tool_request 的获取计划必须说明停止或替代原因")
        if any(not set(request.gap_ids) <= set(self.gap_ids) for request in self.requests):
            raise ValueError("ToolAcquisitionPlan 请求只能引用已交接的 gap_id")
        return self


class ToolRequestExecutionResult(StrictModel):
    """Auditable outcome of one policy-controlled deterministic tool request."""

    request_id: str = Field(min_length=1, max_length=100)
    tool_name: ResearchToolName
    status: ResearchToolExecutionStatus
    failure_code: ResearchToolFailureCode | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=64)
    detail: str = Field(min_length=1, max_length=1000)
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def validate_execution_shape(self) -> "ToolRequestExecutionResult":
        if self.completed_at < self.started_at:
            raise ValueError("ToolRequest completed_at 不得早于 started_at")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("ToolRequest source_ids 不得重复")
        if self.status != "succeeded" and self.source_ids:
            raise ValueError("未成功的 ToolRequest 不得声称产生 MaterialSource")
        if self.status == "succeeded" and self.failure_code is not None:
            raise ValueError("成功的 ToolRequest 不得携带 failure_code")
        return self


class ResearchToolExecutionResult(StrictModel):
    """A plan execution audit plus the deterministically enriched material bundle."""

    plan_id: UUID
    input_bundle_id: UUID
    output_bundle: MaterialBundle
    input_source_ids: list[str] = Field(min_length=1, max_length=64)
    new_source_ids: list[str] = Field(default_factory=list, max_length=64)
    request_results: list[ToolRequestExecutionResult] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_execution_graph(self) -> "ResearchToolExecutionResult":
        output_ids = [source.source_id for source in self.output_bundle.sources]
        if len(self.input_source_ids) != len(set(self.input_source_ids)):
            raise ValueError("input_source_ids 不得重复")
        if len(self.new_source_ids) != len(set(self.new_source_ids)):
            raise ValueError("new_source_ids 不得重复")
        if not set(self.input_source_ids) <= set(output_ids):
            raise ValueError("输出 MaterialBundle 必须保留全部输入来源")
        if set(self.input_source_ids) & set(self.new_source_ids):
            raise ValueError("新旧 MaterialSource ID 不得重叠")
        if set(output_ids) != set(self.input_source_ids) | set(self.new_source_ids):
            raise ValueError("输出 MaterialBundle 来源必须等于输入来源与新增来源之和")
        result_source_ids = {
            source_id for result in self.request_results for source_id in result.source_ids
        }
        if result_source_ids != set(self.new_source_ids):
            raise ValueError("执行结果引用的来源必须匹配全部新增 MaterialSource")
        request_ids = [result.request_id for result in self.request_results]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("ToolRequest 执行结果不得重复")
        return self


class SourceLocator(StrictModel):
    """Model-proposed location that a deterministic validator can check."""

    source_id: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=500)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_line_range(self) -> "SourceLocator":
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("line_start 与 line_end 必须同时提供或同时省略")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("line_end 不得小于 line_start")
        return self


class EvidenceCandidate(StrictModel):
    """Untrusted evidence interpretation proposed by the model."""

    candidate_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    condition_key: str = Field(min_length=1, max_length=300)
    criterion_id: ReadinessCriterionId | None = None
    dimension_ids: list[DimensionId] = Field(min_length=1, max_length=3)
    evidence_type: EvidenceCandidateType
    claim: str = Field(min_length=1, max_length=2000)
    locator: SourceLocator
    quote: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=2000)
    uncertainty_reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_candidate_semantics(self) -> "EvidenceCandidate":
        if len(self.dimension_ids) != len(set(self.dimension_ids)):
            raise ValueError("EvidenceCandidate dimension_ids 不得重复")
        if self.evidence_type == "Unknown" and self.uncertainty_reason is None:
            raise ValueError("Unknown EvidenceCandidate 必须说明 uncertainty_reason")
        return self


class ConflictCandidate(StrictModel):
    """Untrusted cross-source conflict proposed by the model."""

    candidate_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    conflict_key: str | None = Field(default=None, min_length=1, max_length=300)
    condition_key: str = Field(min_length=1, max_length=300)
    criterion_id: ReadinessCriterionId | None = None
    disposition: ConflictDispositionCandidate | None = None
    dimension_ids: list[DimensionId] = Field(min_length=1, max_length=3)
    summary: str = Field(min_length=1, max_length=2000)
    evidence_candidate_ids: list[str] = Field(min_length=2)
    confidence: float = Field(ge=0, le=1)
    uncertainty_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_conflict_references(self) -> "ConflictCandidate":
        if len(self.dimension_ids) != len(set(self.dimension_ids)):
            raise ValueError("ConflictCandidate dimension_ids 不得重复")
        if len(set(self.evidence_candidate_ids)) < 2:
            raise ValueError("ConflictCandidate 必须引用至少两个不同 EvidenceCandidate")
        if (self.criterion_id is None) != (self.disposition is None):
            raise ValueError("ConflictCandidate 的 criterion_id 与 disposition 必须同时提供")
        return self


class FindingCandidate(StrictModel):
    """Untrusted Finding draft; it cannot carry a final status or Gate."""

    candidate_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    root_cause_key: str | None = Field(default=None, min_length=1, max_length=300)
    condition_key: str = Field(min_length=1, max_length=300)
    criterion_id: ReadinessCriterionId | None = None
    readiness_effect: ReadinessEffectCandidate | None = None
    primary_dimension_id: DimensionId
    related_dimension_ids: list[DimensionId] = Field(default_factory=list, max_length=2)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    finding_type: FindingType
    evidence_candidate_ids: list[str] = Field(default_factory=list)
    uncertainty_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    suggested_validation: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_finding_semantics(self) -> "FindingCandidate":
        if self.primary_dimension_id in self.related_dimension_ids:
            raise ValueError("primary_dimension_id 不得在 related_dimension_ids 中重复")
        if len(self.related_dimension_ids) != len(set(self.related_dimension_ids)):
            raise ValueError("related_dimension_ids 不得重复")
        if self.finding_type in {"Fact", "Inference"} and not self.evidence_candidate_ids:
            raise ValueError("Fact/Inference FindingCandidate 必须引用 EvidenceCandidate")
        if self.finding_type == "Unknown" and self.uncertainty_reason is None:
            raise ValueError("Unknown FindingCandidate 必须说明 uncertainty_reason")
        if len(self.evidence_candidate_ids) != len(set(self.evidence_candidate_ids)):
            raise ValueError("evidence_candidate_ids 不得重复")
        return self


class ContextGapFocus(StrictModel):
    """Minimum business scope for one Context & Gap analysis phase."""

    scope_refs: list[AnalysisScopeRef] = Field(min_length=1, max_length=5)
    finding_refs: list[str] = Field(default_factory=list, max_length=18)

    @model_validator(mode="after")
    def validate_unique_refs(self) -> "ContextGapFocus":
        if len(self.scope_refs) != len(set(self.scope_refs)):
            raise ValueError("Context & Gap scope_refs 不得重复")
        if len(self.finding_refs) != len(set(self.finding_refs)):
            raise ValueError("Context & Gap finding_refs 不得重复")
        return self


class SupportedFactDraft(StrictModel):
    """One source-bound fact retained by the Context & Gap phase."""

    statement: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=100)
    verification_status: EvidenceVerificationStatus


class PhaseInformationGap(StrictModel):
    """A minimum missing fact handed between prompt phases."""

    gap_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    question: str = Field(min_length=1, max_length=1000)
    scope_ref: AnalysisScopeRef
    needed_source_type: EvidenceSourceType
    reason: str = Field(min_length=1, max_length=1000)


class ContextGapControl(StrictModel):
    """Control-only handoff; it cannot express a business status or Gate."""

    target_confirmation_needed: bool
    more_information_needed: bool
    stop_reason: Literal[
        "target_confirmation_required",
        "no_reliable_next_source",
    ] | None = None


class AIContextGapResult(StrictModel):
    """Phase-native Context & Gap output with no tool selection."""

    analysis_mode: Literal["initial", "reassessment"]
    focus: ContextGapFocus
    supported_facts: list[SupportedFactDraft] = Field(default_factory=list, max_length=64)
    information_gaps: list[PhaseInformationGap] = Field(default_factory=list, max_length=16)
    control: ContextGapControl

    @model_validator(mode="after")
    def validate_context_gap_handoff(self) -> "AIContextGapResult":
        gap_ids = [gap.gap_id for gap in self.information_gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("Context & Gap gap_id 不得重复")
        fact_keys = {
            (fact.source_ref, fact.statement, fact.verification_status)
            for fact in self.supported_facts
        }
        if len(fact_keys) != len(self.supported_facts):
            raise ValueError("Context & Gap supported_facts 不得重复")
        if self.information_gaps and not self.control.more_information_needed:
            raise ValueError("存在 InformationGap 时必须声明需要更多信息")
        if self.control.more_information_needed and not (
            self.information_gaps or self.control.target_confirmation_needed
        ):
            raise ValueError("需要更多信息时必须提供 Gap 或要求目标确认")
        if self.control.target_confirmation_needed:
            if self.control.stop_reason != "target_confirmation_required":
                raise ValueError("目标确认路径必须使用 target_confirmation_required")
            if not self.control.more_information_needed:
                raise ValueError("目标确认路径必须声明需要更多信息")
        return self


class AcquisitionRequestDraft(StrictModel):
    """One minimum, non-executing acquisition request tied to an existing Gap."""

    gap_ref: str = Field(min_length=1, max_length=100)
    requested_fact: str = Field(min_length=1, max_length=1000)
    source_type: EvidenceSourceType
    material_type_hint: MaterialType | None = None
    tool_ref: ResearchToolName | None = None
    read_scope: str | None = Field(default=None, min_length=1, max_length=1000)
    query: str | None = Field(default=None, min_length=1, max_length=1000)
    url: HttpUrl | None = None
    identifier: str | None = Field(default=None, min_length=1, max_length=500)
    expected_evidence: str = Field(min_length=1, max_length=1000)
    authorization_required: bool = False
    alternative_input: AcquisitionAlternativeInput | None = None

    @model_validator(mode="after")
    def validate_request_route(self) -> "AcquisitionRequestDraft":
        if self.tool_ref is not None and self.read_scope is None:
            raise ValueError("工具获取请求必须声明最小 read_scope")
        if self.tool_ref is not None and self.alternative_input is not None:
            raise ValueError("同一获取请求不能同时选择 Tool 与替代输入")
        if self.authorization_required and self.tool_ref != "inspect_local_environment":
            raise ValueError("仅本机环境读取可以要求运行时授权")
        if self.tool_ref is None and self.alternative_input is None:
            raise ValueError("获取请求必须选择 Tool 或替代输入")
        if self.tool_ref is not None:
            search_tools = {"search_web", "search_github"}
            url_tools = {
                "fetch_web_page",
                "read_github_repository",
                "read_github_file",
                "read_huggingface_card",
                "probe_dataset_access",
                "probe_checkpoint_access",
            }
            if self.tool_ref in search_tools:
                valid_arguments = self.query is not None and self.url is None and self.identifier is None
            elif self.tool_ref in url_tools:
                valid_arguments = self.url is not None and self.query is None and self.identifier is None
            elif self.tool_ref == "fetch_paper":
                valid_arguments = self.identifier is not None and self.query is None and self.url is None
            else:
                valid_arguments = self.query is None and self.url is None and self.identifier is None
            if not valid_arguments:
                raise ValueError("Tool Acquisition 请求参数必须匹配 tool_ref")
        elif any(value is not None for value in (self.query, self.url, self.identifier)):
            raise ValueError("替代输入请求不得携带 Tool 参数")
        return self


class AcquisitionLoopControl(StrictModel):
    """Bounded loop state supplied by runtime rather than inferred as readiness."""

    current_round: int = Field(ge=0, le=5)
    configured_max_rounds: int = Field(ge=1, le=5)
    continue_after_result: bool
    stop_reason: AcquisitionStopReason | None = None

    @model_validator(mode="after")
    def validate_round_state(self) -> "AcquisitionLoopControl":
        if self.current_round > self.configured_max_rounds:
            raise ValueError("current_round 不得超过 configured_max_rounds")
        if self.continue_after_result and self.stop_reason is not None:
            raise ValueError("继续获取时不得同时声明 stop_reason")
        if not self.continue_after_result and self.stop_reason is None:
            raise ValueError("停止获取时必须说明 stop_reason")
        return self


class AIToolAcquisitionResult(StrictModel):
    """Phase-native minimum acquisition plan; it never contains Tool Results."""

    acquisition_state: Literal[
        "tool_request",
        "human_confirmation",
        "authorization_required",
        "alternative_input",
        "stop_acquisition",
    ]
    requests: list[AcquisitionRequestDraft] = Field(default_factory=list, max_length=12)
    loop_control: AcquisitionLoopControl

    @model_validator(mode="after")
    def validate_acquisition_handoff(self) -> "AIToolAcquisitionResult":
        request_keys = [
            (request.gap_ref, request.tool_ref, request.read_scope, request.alternative_input)
            for request in self.requests
        ]
        if len(request_keys) != len(set(request_keys)):
            raise ValueError("Tool Acquisition 请求不得重复")
        if self.acquisition_state == "tool_request":
            if not self.requests or any(request.tool_ref is None for request in self.requests):
                raise ValueError("tool_request 必须包含至少一个具体 Tool 请求")
            if not self.loop_control.continue_after_result:
                raise ValueError("tool_request 必须允许处理 Tool Result 后继续")
        elif self.acquisition_state == "alternative_input":
            if not self.requests or any(
                request.alternative_input is None for request in self.requests
            ):
                raise ValueError("alternative_input 必须声明 Snapshot 或 Manual Input")
        elif self.acquisition_state == "stop_acquisition" and self.requests:
            raise ValueError("stop_acquisition 不得携带新的获取请求")
        if self.acquisition_state != "tool_request" and self.loop_control.continue_after_result:
            raise ValueError("非 Tool 请求状态不得继续自动获取")
        expected_stop_reason = {
            "human_confirmation": "confirmation_required",
            "authorization_required": "authorization_required",
        }.get(self.acquisition_state)
        if expected_stop_reason and self.loop_control.stop_reason != expected_stop_reason:
            raise ValueError("获取状态与 stop_reason 不一致")
        return self


class ToolAcquisitionInput(StrictModel):
    """Trusted runtime envelope for the Tool Acquisition phase.

    The model receives Context & Gap output plus the capabilities and authority
    actually supplied by the runtime.  It can plan a minimum read only; it can
    never extend the allowlist or execute a request from this object.
    """

    bundle: MaterialBundle
    context_gap: AIContextGapResult
    available_tools: list[ResearchToolName] = Field(default_factory=list, max_length=12)
    local_environment_authorized: bool = False
    current_round: int = Field(ge=0, le=5)
    configured_max_rounds: int = Field(ge=1, le=5)
    remaining_tool_requests: int = Field(default=12, ge=0, le=12)

    @model_validator(mode="after")
    def validate_runtime_boundary(self) -> "ToolAcquisitionInput":
        if len(self.available_tools) != len(set(self.available_tools)):
            raise ValueError("Tool Acquisition available_tools 不得重复")
        if self.current_round > self.configured_max_rounds:
            raise ValueError("Tool Acquisition current_round 不得超过 configured_max_rounds")
        if not self.context_gap.information_gaps and self.context_gap.control.more_information_needed:
            if not self.context_gap.control.target_confirmation_needed:
                raise ValueError("无 Gap 的更多信息路径必须要求目标确认")
        return self


class EvidenceFindingConditionContext(StrictModel):
    """One current condition supplied by workflow, never inferred as a Gate."""

    condition_ref: str = Field(min_length=1, max_length=300)
    primary_dimension: DimensionId
    related_dimensions: list[DimensionId] = Field(default_factory=list, max_length=2)
    existing_finding_ref: str | None = Field(default=None, min_length=1, max_length=100)
    gate_critical: bool | None = None

    @model_validator(mode="after")
    def validate_condition_context(self) -> "EvidenceFindingConditionContext":
        if self.primary_dimension in self.related_dimensions:
            raise ValueError("Condition Context primary_dimension 不得重复出现在 related_dimensions")
        if len(self.related_dimensions) != len(set(self.related_dimensions)):
            raise ValueError("Condition Context related_dimensions 不得重复")
        return self


class EvidenceDraft(StrictModel):
    """Source-bound Evidence proposed for one current Condition."""

    local_evidence_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    condition_refs: list[str] = Field(min_length=1, max_length=1)
    source_ref: str = Field(min_length=1, max_length=100)
    source_type: EvidenceSourceType
    evidence_type: EvidenceCandidateType = "Unknown"
    location: str = Field(min_length=1, max_length=1000)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    material_type: MaterialType | None = None
    quote: str = Field(min_length=1, max_length=4000)
    claim: str = Field(min_length=1, max_length=2000)
    verification_status: EvidenceVerificationStatus
    conflict_note: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_precise_location(self) -> "EvidenceDraft":
        if len(self.condition_refs) != len(set(self.condition_refs)):
            raise ValueError("Evidence Draft condition_refs 不得重复")
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("Evidence Draft 行号范围必须同时提供起止行")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("Evidence Draft line_end 不得小于 line_start")
        return self


class FindingDraft(StrictModel):
    """Finding proposal without any formal status, Gate, or final action."""

    local_finding_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    operation: Literal["create", "update_existing"]
    existing_finding_ref: str | None = Field(default=None, min_length=1, max_length=100)
    condition: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    finding_type: FindingType
    primary_dimension: DimensionId
    related_dimensions: list[DimensionId] = Field(default_factory=list, max_length=2)
    evidence_refs_local: list[str] = Field(default_factory=list, max_length=32)
    source_gap_refs: list[str] = Field(default_factory=list, max_length=16)
    gate_critical: bool | None = None
    gate_critical_basis: Literal[
        "supplied_condition_context",
        "needs_rule_enrichment",
    ] = "needs_rule_enrichment"

    @model_validator(mode="after")
    def validate_finding_draft(self) -> "FindingDraft":
        if self.operation == "update_existing" and self.existing_finding_ref is None:
            raise ValueError("update_existing 必须提供 existing_finding_ref")
        if self.operation == "create" and self.existing_finding_ref is not None:
            raise ValueError("create 不得携带 existing_finding_ref")
        if self.primary_dimension in self.related_dimensions:
            raise ValueError("primary_dimension 不得重复出现在 related_dimensions")
        if len(self.related_dimensions) != len(set(self.related_dimensions)):
            raise ValueError("related_dimensions 不得重复")
        if len(self.evidence_refs_local) != len(set(self.evidence_refs_local)):
            raise ValueError("evidence_refs_local 不得重复")
        if len(self.source_gap_refs) != len(set(self.source_gap_refs)):
            raise ValueError("source_gap_refs 不得重复")
        if self.finding_type in {"Fact", "Inference"} and not self.evidence_refs_local:
            raise ValueError("Fact/Inference Finding Draft 必须引用 Evidence Draft")
        if self.gate_critical is not None and self.gate_critical_basis != "supplied_condition_context":
            raise ValueError("AI 只能复制由 Condition Context 明确提供的 gate_critical")
        return self


class ConflictDraft(StrictModel):
    """A locally scoped conflict that retains both sides without adjudicating it."""

    local_conflict_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    condition_ref: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    local_evidence_refs: list[str] = Field(default_factory=list, max_length=32)
    related_existing_evidence_refs: list[str] = Field(default_factory=list, max_length=32)
    primary_dimension: DimensionId
    related_dimensions: list[DimensionId] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def validate_conflict_draft(self) -> "ConflictDraft":
        if self.primary_dimension in self.related_dimensions:
            raise ValueError("Conflict Draft primary_dimension 不得重复出现在 related_dimensions")
        if len(self.related_dimensions) != len(set(self.related_dimensions)):
            raise ValueError("Conflict Draft related_dimensions 不得重复")
        if len(self.local_evidence_refs) != len(set(self.local_evidence_refs)):
            raise ValueError("Conflict Draft local_evidence_refs 不得重复")
        if len(self.related_existing_evidence_refs) != len(
            set(self.related_existing_evidence_refs)
        ):
            raise ValueError("Conflict Draft related_existing_evidence_refs 不得重复")
        if len(self.local_evidence_refs) + len(self.related_existing_evidence_refs) < 2:
            raise ValueError("Conflict Draft 必须保留至少两项冲突双方 Evidence")
        return self


class RemainingInformationGap(StrictModel):
    """Existing Gap that remains unresolved after Evidence/Finding analysis."""

    gap_ref: str = Field(min_length=1, max_length=100)
    still_unresolved: Literal[True] = True
    reason: str = Field(min_length=1, max_length=1000)


class EvidenceFindingHandoff(StrictModel):
    """Minimal routing signal after Evidence/Finding drafting."""

    needs_more_information: bool
    ready_for_rule: bool

    @model_validator(mode="after")
    def validate_handoff(self) -> "EvidenceFindingHandoff":
        if not self.needs_more_information and not self.ready_for_rule:
            raise ValueError("Evidence/Finding handoff 必须选择后续路径")
        return self


class AIEvidenceFindingDraftResult(StrictModel):
    """Phase-native, locally scoped Evidence and Finding draft result."""

    evidence_drafts: list[EvidenceDraft] = Field(default_factory=list, max_length=8)
    finding_drafts: list[FindingDraft] = Field(default_factory=list, max_length=2)
    conflict_drafts: list[ConflictDraft] = Field(default_factory=list, max_length=4)
    remaining_information_gaps: list[RemainingInformationGap] = Field(
        default_factory=list,
        max_length=16,
    )
    handoff: EvidenceFindingHandoff

    @model_validator(mode="after")
    def validate_draft_graph(self) -> "AIEvidenceFindingDraftResult":
        gap_refs = [item.gap_ref for item in self.remaining_information_gaps]
        if len(gap_refs) != len(set(gap_refs)):
            raise ValueError("Remaining Gap 引用不得重复")
        if self.handoff.needs_more_information and not self.remaining_information_gaps:
            raise ValueError("需要更多信息时必须保留至少一个未解决 Gap")
        if self.remaining_information_gaps and not self.handoff.needs_more_information:
            raise ValueError("存在未解决 Gap 时 handoff 必须声明需要更多信息")
        return self


class EvidenceFindingInput(StrictModel):
    """Explicit local context handed from Context/Gap and Tool Acquisition.

    ``relevant_source_ids`` is an allowlist: sources outside it are deliberately
    withheld from this model phase so a local reassessment cannot turn into an
    unrelated full-project reread.
    """

    bundle: MaterialBundle
    focus: ContextGapFocus
    condition_contexts: list[EvidenceFindingConditionContext] = Field(
        min_length=1,
        max_length=5,
    )
    current_information_gaps: list[PhaseInformationGap] = Field(
        default_factory=list,
        max_length=16,
    )
    relevant_source_ids: list[str] = Field(min_length=1, max_length=64)
    related_evidence: list[EvidenceDraft] = Field(default_factory=list, max_length=32)
    related_findings: list[FindingDraft] = Field(default_factory=list, max_length=18)

    @model_validator(mode="after")
    def validate_local_evidence_finding_input(self) -> "EvidenceFindingInput":
        if len(self.relevant_source_ids) != len(set(self.relevant_source_ids)):
            raise ValueError("Evidence/Finding relevant_source_ids 不得重复")
        known_source_ids = {source.source_id for source in self.bundle.sources}
        if not set(self.relevant_source_ids) <= known_source_ids:
            raise ValueError("Evidence/Finding 引用了不在 MaterialBundle 的来源")
        if any(
            item.source_ref not in known_source_ids for item in self.related_evidence
        ):
            raise ValueError("Evidence/Finding 关联 Evidence 引用了未知来源")
        gap_ids = [gap.gap_id for gap in self.current_information_gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("Evidence/Finding current_information_gaps 不得重复")
        condition_refs = [item.condition_ref for item in self.condition_contexts]
        if len(condition_refs) != len(set(condition_refs)):
            raise ValueError("Evidence/Finding condition_contexts 不得重复")
        return self


class FeedbackAffectedRefs(StrictModel):
    """Minimum dependency scope selected before a feedback reassessment."""

    finding_refs: list[str] = Field(default_factory=list, max_length=18)
    evidence_refs: list[str] = Field(default_factory=list, max_length=32)
    dimension_refs: list[DimensionId] = Field(default_factory=list, max_length=3)
    signal_refs: list[Literal["resource_constraint", "evaluation_conditions"]] = Field(
        default_factory=list,
        max_length=2,
    )

    @model_validator(mode="after")
    def validate_unique_refs(self) -> "FeedbackAffectedRefs":
        for name in ("finding_refs", "evidence_refs", "dimension_refs", "signal_refs"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"Feedback {name} 不得重复")
        return self


class AIFeedbackScopeResult(StrictModel):
    """Scope-only feedback decision; later phases perform collection and rewriting."""

    reassessment_required: bool
    affected_refs: FeedbackAffectedRefs
    change_summary: str = Field(min_length=1, max_length=2000)
    new_information_gaps: list[PhaseInformationGap] = Field(default_factory=list, max_length=16)
    handoff: Literal["no_change", "tool_acquisition", "evidence_finding"]

    @model_validator(mode="after")
    def validate_feedback_scope(self) -> "AIFeedbackScopeResult":
        gap_ids = [gap.gap_id for gap in self.new_information_gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("Feedback 新增 gap_id 不得重复")
        has_target_ref = bool(
            self.affected_refs.finding_refs or self.affected_refs.evidence_refs
        )
        has_business_scope = bool(
            self.affected_refs.dimension_refs or self.affected_refs.signal_refs
        )
        if not self.reassessment_required:
            if has_target_ref or has_business_scope or self.new_information_gaps:
                raise ValueError("无需重判时不得声明受影响范围或新增 Gap")
            if self.handoff != "no_change":
                raise ValueError("无需重判时 handoff 必须为 no_change")
            return self
        if not has_target_ref or not has_business_scope:
            raise ValueError("需要重判时必须包含目标引用和受影响维度或 Signal")
        if self.handoff == "no_change":
            raise ValueError("需要重判时不得返回 no_change")
        if self.handoff == "tool_acquisition" and not self.new_information_gaps:
            raise ValueError("Tool Acquisition handoff 必须包含新增 Gap")
        if self.new_information_gaps and self.handoff != "tool_acquisition":
            raise ValueError("存在新增 Gap 时必须交接给 Tool Acquisition")
        return self


class UnresolvedQuestion(StrictModel):
    """Missing information the model cannot support with a direct evidence quote."""

    question_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    condition_key: str = Field(min_length=1, max_length=300)
    criterion_id: ReadinessCriterionId | None = None
    dimension_id: DimensionId
    question: str = Field(min_length=1, max_length=1000)
    missing_information: str = Field(min_length=1, max_length=1000)
    inspected_source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_inspected_sources(self) -> "UnresolvedQuestion":
        if len(self.inspected_source_ids) != len(set(self.inspected_source_ids)):
            raise ValueError("UnresolvedQuestion inspected_source_ids 不得重复")
        return self


class EvidenceAreaCoverage(StrictModel):
    """Explicit accounting proving that one required evidence area was inspected."""

    area: EvidenceAnalysisArea
    state: EvidenceCoverageState
    summary: str = Field(min_length=1, max_length=1000)
    evidence_candidate_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_AI_EVIDENCE_CANDIDATES,
    )
    unresolved_question_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_AI_UNRESOLVED_QUESTIONS,
    )

    @model_validator(mode="after")
    def validate_coverage_state(self) -> "EvidenceAreaCoverage":
        if len(self.evidence_candidate_ids) != len(set(self.evidence_candidate_ids)):
            raise ValueError("EvidenceAreaCoverage evidence_candidate_ids 不得重复")
        if len(self.unresolved_question_ids) != len(set(self.unresolved_question_ids)):
            raise ValueError("EvidenceAreaCoverage unresolved_question_ids 不得重复")
        if self.state == "evidence_found" and not self.evidence_candidate_ids:
            raise ValueError("evidence_found coverage 必须引用 EvidenceCandidate")
        if self.state == "not_found" and not self.unresolved_question_ids:
            raise ValueError("not_found coverage 必须引用 UnresolvedQuestion")
        if self.state == "not_found" and self.evidence_candidate_ids:
            raise ValueError("not_found coverage 不得同时声明已找到 Evidence")
        if self.state == "uncertain" and not (
            self.evidence_candidate_ids or self.unresolved_question_ids
        ):
            raise ValueError("uncertain coverage 必须引用不确定 Evidence 或未决问题")
        return self


class AIEvidenceExtractionResult(StrictModel):
    """Evidence-only AI output; Conflict, Finding, status, and Gate are impossible here."""

    extraction_id: UUID
    bundle_id: UUID
    contract_version: Literal["1.0"] = "1.0"
    summary: str = Field(min_length=1, max_length=2000)
    examined_source_ids: list[str] = Field(min_length=1, max_length=64)
    evidence_candidates: list[EvidenceCandidate] = Field(
        default_factory=list,
        max_length=MAX_AI_EVIDENCE_CANDIDATES,
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        max_length=MAX_AI_UNRESOLVED_QUESTIONS,
    )
    coverage: list[EvidenceAreaCoverage] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_extraction_graph(self) -> "AIEvidenceExtractionResult":
        if len(self.examined_source_ids) != len(set(self.examined_source_ids)):
            raise ValueError("examined_source_ids 不得重复")

        evidence_ids = [candidate.candidate_id for candidate in self.evidence_candidates]
        question_ids = [question.question_id for question in self.unresolved_questions]
        if len([*evidence_ids, *question_ids]) != len(set([*evidence_ids, *question_ids])):
            raise ValueError("Evidence extraction 中 candidate/question ID 必须全局唯一")

        required_areas = {
            "rd01_data_access",
            "rd02_environment_dependency",
            "rd03_weights_configuration",
            "resource_constraint",
            "evaluation_conditions",
        }
        areas = [item.area for item in self.coverage]
        if len(areas) != len(set(areas)) or set(areas) != required_areas:
            raise ValueError("Evidence extraction 必须且只能覆盖五个规定分析区域")

        covered_evidence_ids = {
            candidate_id for item in self.coverage for candidate_id in item.evidence_candidate_ids
        }
        covered_question_ids = {
            question_id for item in self.coverage for question_id in item.unresolved_question_ids
        }
        if covered_evidence_ids != set(evidence_ids):
            raise ValueError("所有 EvidenceCandidate 必须且只能引用到 coverage 中的已知 ID")
        if covered_question_ids != set(question_ids):
            raise ValueError("所有 UnresolvedQuestion 必须且只能引用到 coverage 中的已知 ID")

        examined_ids = set(self.examined_source_ids)
        if any(item.locator.source_id not in examined_ids for item in self.evidence_candidates):
            raise ValueError("EvidenceCandidate 来源必须属于 examined_source_ids")
        if any(
            not set(question.inspected_source_ids) <= examined_ids
            for question in self.unresolved_questions
        ):
            raise ValueError("UnresolvedQuestion 来源必须属于 examined_source_ids")
        return self

    def to_analysis_result(self) -> "AIAnalysisResult":
        """Convert evidence-only output into the complete candidate envelope for Rule validation."""
        return AIAnalysisResult(
            analysis_id=self.extraction_id,
            bundle_id=self.bundle_id,
            contract_version=self.contract_version,
            summary=self.summary,
            examined_source_ids=list(self.examined_source_ids),
            evidence_candidates=[item.model_copy(deep=True) for item in self.evidence_candidates],
            unresolved_questions=[item.model_copy(deep=True) for item in self.unresolved_questions],
        )


class ValidatedEvidenceItem(StrictModel):
    """One Evidence candidate plus its deterministic validation and source metadata."""

    candidate: EvidenceCandidate
    validation: "EvidenceValidationResult"
    source_path: str = Field(min_length=1, max_length=1000)
    material_type: MaterialType
    access_scope: MaterialAccessScope

    @model_validator(mode="after")
    def validate_item_identity(self) -> "ValidatedEvidenceItem":
        if self.candidate.candidate_id != self.validation.evidence_candidate_id:
            raise ValueError("ValidatedEvidenceItem candidate 与 validation 身份不匹配")
        if self.validation.decision not in {"accepted", "downgraded"}:
            raise ValueError("Conflict/Finding AI 只能接收 accepted 或 downgraded Evidence")
        if self.validation.resulting_type is None or self.validation.verified_locator is None:
            raise ValueError("送入 Conflict/Finding AI 的 Evidence 必须具有类型和已验证位置")
        if self.validation.verified_locator.source_id != self.candidate.locator.source_id:
            raise ValueError("ValidatedEvidenceItem 的来源身份不匹配")
        return self


class ConflictFindingAnalysisInput(StrictModel):
    """Validated, content-minimal input for the independent Conflict/Finding AI stage."""

    bundle_id: UUID
    evidence_extraction_id: UUID
    examined_source_ids: list[str] = Field(min_length=1, max_length=64)
    evidence: list[ValidatedEvidenceItem] = Field(
        default_factory=list,
        max_length=MAX_AI_EVIDENCE_CANDIDATES,
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        max_length=MAX_AI_UNRESOLVED_QUESTIONS,
    )
    excluded_evidence_candidate_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_AI_EVIDENCE_CANDIDATES,
    )
    human_review_context: HumanReviewContext | None = None

    @model_validator(mode="after")
    def validate_input_graph(self) -> "ConflictFindingAnalysisInput":
        evidence_ids = [item.candidate.candidate_id for item in self.evidence]
        if len(self.examined_source_ids) != len(set(self.examined_source_ids)):
            raise ValueError("Conflict/Finding input examined source ID 不得重复")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Conflict/Finding input Evidence ID 不得重复")
        if len(self.excluded_evidence_candidate_ids) != len(
            set(self.excluded_evidence_candidate_ids)
        ):
            raise ValueError("excluded Evidence ID 不得重复")
        if set(evidence_ids) & set(self.excluded_evidence_candidate_ids):
            raise ValueError("同一 Evidence 不得同时进入和排除 Conflict/Finding AI")
        return self


class AIConflictFindingResult(StrictModel):
    """Untrusted Conflict/Finding-only output over already validated Evidence."""

    interpretation_id: UUID
    bundle_id: UUID
    evidence_extraction_id: UUID
    contract_version: Literal["1.0"] = "1.0"
    summary: str = Field(min_length=1, max_length=2000)
    considered_evidence_candidate_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_AI_EVIDENCE_CANDIDATES,
    )
    conflict_candidates: list[ConflictCandidate] = Field(
        default_factory=list,
        max_length=MAX_AI_CONFLICT_CANDIDATES,
    )
    finding_candidates: list[FindingCandidate] = Field(
        default_factory=list,
        max_length=MAX_AI_FINDING_CANDIDATES,
    )

    @model_validator(mode="after")
    def validate_candidate_graph(self) -> "AIConflictFindingResult":
        considered = set(self.considered_evidence_candidate_ids)
        if len(considered) != len(self.considered_evidence_candidate_ids):
            raise ValueError("considered Evidence ID 不得重复")
        candidate_ids = [
            *(item.candidate_id for item in self.conflict_candidates),
            *(item.candidate_id for item in self.finding_candidates),
        ]
        if len(candidate_ids) != len(set(candidate_ids)) or considered & set(candidate_ids):
            raise ValueError("Conflict/Finding 与 Evidence candidate ID 必须全局唯一")
        for conflict in self.conflict_candidates:
            if conflict.conflict_key is None:
                raise ValueError("AI ConflictCandidate 必须提供 conflict_key")
            if not set(conflict.evidence_candidate_ids) <= considered:
                raise ValueError("ConflictCandidate 引用了未考虑的 Evidence")
        for finding in self.finding_candidates:
            if finding.root_cause_key is None:
                raise ValueError("AI FindingCandidate 必须提供 root_cause_key")
            if not set(finding.evidence_candidate_ids) <= considered:
                raise ValueError("FindingCandidate 引用了未考虑的 Evidence")
        return self


class CandidateMerge(StrictModel):
    """Deterministic audit record for duplicate AI candidate consolidation."""

    candidate_kind: Literal["conflict", "finding"]
    canonical_candidate_id: str = Field(min_length=1, max_length=100)
    merged_candidate_ids: list[str] = Field(min_length=2)
    merge_key: str = Field(min_length=1, max_length=300)


class ConflictFindingNormalizationResult(StrictModel):
    """Candidate graph after deterministic de-duplication, before admission rules."""

    interpretation_id: UUID
    analysis: "AIAnalysisResult"
    evidence_validation: "AIAnalysisValidationResult"
    merges: list[CandidateMerge] = Field(default_factory=list)


class AIAnalysisResult(StrictModel):
    """Complete untrusted model output before Rule validation and adjudication."""

    analysis_id: UUID
    bundle_id: UUID
    contract_version: Literal["1.0"] = "1.0"
    summary: str = Field(min_length=1, max_length=2000)
    examined_source_ids: list[str] = Field(min_length=1, max_length=64)
    evidence_candidates: list[EvidenceCandidate] = Field(
        default_factory=list,
        max_length=MAX_MERGED_EVIDENCE_CANDIDATES,
    )
    conflict_candidates: list[ConflictCandidate] = Field(
        default_factory=list,
        max_length=MAX_MERGED_CONFLICT_CANDIDATES,
    )
    finding_candidates: list[FindingCandidate] = Field(
        default_factory=list,
        max_length=MAX_MERGED_FINDING_CANDIDATES,
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        max_length=MAX_MERGED_UNRESOLVED_QUESTIONS,
    )

    @model_validator(mode="after")
    def validate_candidate_graph(self) -> "AIAnalysisResult":
        if len(self.examined_source_ids) != len(set(self.examined_source_ids)):
            raise ValueError("examined_source_ids 不得重复")

        evidence_ids = [candidate.candidate_id for candidate in self.evidence_candidates]
        conflict_ids = [candidate.candidate_id for candidate in self.conflict_candidates]
        finding_ids = [candidate.candidate_id for candidate in self.finding_candidates]
        question_ids = [question.question_id for question in self.unresolved_questions]
        all_ids = [*evidence_ids, *conflict_ids, *finding_ids, *question_ids]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("AIAnalysisResult 中所有 candidate/question ID 必须全局唯一")

        known_evidence_ids = set(evidence_ids)
        for conflict in self.conflict_candidates:
            if not set(conflict.evidence_candidate_ids) <= known_evidence_ids:
                raise ValueError("ConflictCandidate 引用了不存在的 EvidenceCandidate")
        for finding in self.finding_candidates:
            if not set(finding.evidence_candidate_ids) <= known_evidence_ids:
                raise ValueError("FindingCandidate 引用了不存在的 EvidenceCandidate")
        return self


class AIModelTrace(StrictModel):
    """Privacy-bounded metadata for one model invocation.

    Raw prompts, source contents, authorization headers, and API keys are
    intentionally excluded from this contract.
    """

    trace_id: UUID
    provider: Literal["deepseek"] = "deepseek"
    model: str = Field(min_length=1, max_length=200)
    request_id: str | None = Field(default=None, min_length=1, max_length=300)
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)
    attempts: int = Field(ge=1, le=6)
    status: AIModelTraceStatus
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    error_type: str | None = Field(default=None, min_length=1, max_length=200)
    error_detail: str | None = Field(default=None, min_length=1, max_length=1000)
    api_mode: Literal["strict_tools", "responses", "chat_completions"] | None = None

    @model_validator(mode="after")
    def validate_trace_status(self) -> "AIModelTrace":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at 不得早于 started_at")
        if self.status == "success" and self.error_type is not None:
            raise ValueError("成功 Trace 不得包含 error_type")
        if self.status == "success" and self.error_detail is not None:
            raise ValueError("成功 Trace 不得包含 error_detail")
        if self.status == "failed" and self.error_type is None:
            raise ValueError("失败 Trace 必须包含 error_type")
        return self


class AIEvidenceExtractionInvocation(StrictModel):
    """Evidence-only candidates paired with privacy-bounded execution metadata."""

    result: AIEvidenceExtractionResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIEvidenceExtractionInvocation":
        if self.trace.status != "success":
            raise ValueError("AIEvidenceExtractionInvocation 只能包含成功 Trace")
        return self


class AIContextGapInvocation(StrictModel):
    """Context & Gap output paired with privacy-bounded model metadata."""

    result: AIContextGapResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIContextGapInvocation":
        if self.trace.status != "success":
            raise ValueError("AIContextGapInvocation 只能包含成功 Trace")
        return self


class AIToolAcquisitionInvocation(StrictModel):
    """Tool Acquisition plan paired with content-free model metadata."""

    result: AIToolAcquisitionResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIToolAcquisitionInvocation":
        if self.trace.status != "success":
            raise ValueError("AIToolAcquisitionInvocation 只能包含成功 Trace")
        return self


class AIEvidenceFindingDraftInvocation(StrictModel):
    """Local Evidence/Finding draft result paired with model trace metadata."""

    result: AIEvidenceFindingDraftResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIEvidenceFindingDraftInvocation":
        if self.trace.status != "success":
            raise ValueError("AIEvidenceFindingDraftInvocation 只能包含成功 Trace")
        return self


class AIResearchPlanInvocation(StrictModel):
    """Research-planning output paired with privacy-bounded model metadata."""

    result: AIResearchPlanResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIResearchPlanInvocation":
        if self.trace.status != "success":
            raise ValueError("AIResearchPlanInvocation 只能包含成功 Trace")
        return self


class AIFeedbackReassessmentInvocation(StrictModel):
    result: AIFeedbackReassessmentResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIFeedbackReassessmentInvocation":
        if self.trace.status != "success":
            raise ValueError("AIFeedbackReassessmentInvocation 只能包含成功 Trace")
        return self


class ResearchLoopRound(StrictModel):
    """One Context/Gap + Tool Acquisition and optional execution cycle.

    The provider-owned phase artifacts are recorded separately so audit never
    mislabels Context/Gap and Tool Acquisition as one combined AI planning step.
    """

    round_number: int = Field(ge=1, le=5)
    planning: AIResearchPlanInvocation | None = None
    context_gap: AIContextGapInvocation | None = None
    tool_acquisition: AIToolAcquisitionInvocation | None = None
    acquisition_plan: ToolAcquisitionPlan | None = None
    execution: ResearchToolExecutionResult | None = None

    @model_validator(mode="after")
    def validate_round_links(self) -> "ResearchLoopRound":
        if self.tool_acquisition is not None and self.context_gap is None:
            raise ValueError("Tool Acquisition 必须引用同轮的 Context & Gap")
        if self.execution is not None and self.planning is not None:
            if self.execution.plan_id != self.planning.result.plan_id:
                raise ValueError("研究轮次的计划与执行记录不匹配")
            if self.execution.input_bundle_id != self.planning.result.bundle_id:
                raise ValueError("研究轮次的输入 Bundle 不匹配")
        if self.execution is not None and self.planning is None and self.tool_acquisition is None:
            raise ValueError("执行记录必须关联 Tool Acquisition 或兼容计划")
        return self


class ResearchLoopResult(StrictModel):
    """Bounded multi-round research outcome before Evidence extraction."""

    run_id: UUID
    initial_bundle_id: UUID
    final_bundle: MaterialBundle
    stop_reason: ResearchLoopStopReason
    tool_requests_used: int = Field(ge=0, le=12)
    rounds: list[ResearchLoopRound] = Field(min_length=1, max_length=5)
    handoff: "ResearchLoopHandoff | None" = None

    @model_validator(mode="after")
    def validate_loop_accounting(self) -> "ResearchLoopResult":
        if [item.round_number for item in self.rounds] != list(range(1, len(self.rounds) + 1)):
            raise ValueError("研究轮次编号必须从 1 连续递增")
        executed_request_count = sum(
            len(item.execution.request_results)
            for item in self.rounds
            if item.execution is not None
        )
        if self.tool_requests_used != executed_request_count:
            raise ValueError("tool_requests_used 必须匹配实际执行请求数")
        latest_execution = next(
            (item.execution for item in reversed(self.rounds) if item.execution is not None),
            None,
        )
        expected_final_bundle_id = (
            latest_execution.output_bundle.bundle_id
            if latest_execution is not None
            else self.initial_bundle_id
        )
        if self.final_bundle.bundle_id != expected_final_bundle_id:
            raise ValueError("final_bundle 必须匹配最后一次确定性执行结果")
        return self


class ResearchLoopHandoff(StrictModel):
    """Acquisition-only next step; it is never a Readiness status or Gate."""

    state: Literal[
        "analysis_ready",
        "confirmation_required",
        "authorization_required",
        "acquisition_failure",
        "stopped",
    ]
    reason: ResearchLoopStopReason
    user_question: str | None = Field(default=None, min_length=1, max_length=1000)
    alternative_inputs: list[Literal["snapshot", "manual"]] = Field(default_factory=list)
    retry_allowed: bool = False

    @model_validator(mode="after")
    def validate_handoff_shape(self) -> "ResearchLoopHandoff":
        if self.state == "confirmation_required" and not self.user_question:
            raise ValueError("confirmation_required 必须包含用户确认问题")
        if self.state != "confirmation_required" and self.user_question is not None:
            raise ValueError("只有 confirmation_required 可以携带用户确认问题")
        if self.alternative_inputs and self.state not in {
            "authorization_required",
            "acquisition_failure",
        }:
            raise ValueError("Snapshot / Manual Input 仅能作为授权或获取失败的替代路径")
        if len(self.alternative_inputs) != len(set(self.alternative_inputs)):
            raise ValueError("alternative_inputs 不得重复")
        return self


class ContextGapSupportedFact(StrictModel):
    """One Rule-validated fact retained for the Context & Gap handoff."""

    statement: str = Field(min_length=1, max_length=2000)
    source_id: str = Field(min_length=1, max_length=100)
    source_type: Literal["Material", "User Context"]
    verification: Literal["accepted", "downgraded"]
    location: str | None = Field(default=None, min_length=1, max_length=1000)


class ContextGapSnapshot(StrictModel):
    """Explicit Context & Gap record kept separate from tool execution results.

    This is a workflow artifact, not an AI-owned Status or Gate decision.  It
    records the current factual basis and the smallest outstanding information
    gaps so a later acquisition audit cannot be mistaken for a business result.
    """

    analysis_mode: Literal["initial", "reassessment"]
    focus_areas: list[EvidenceAnalysisArea] = Field(default_factory=list, max_length=5)
    supported_facts: list[ContextGapSupportedFact] = Field(default_factory=list, max_length=64)
    information_gaps: list[InformationGap] = Field(default_factory=list, max_length=16)
    target_confirmation_needed: bool
    authorization_required: bool
    stop_reason: ResearchLoopStopReason | Literal["not_configured"]
    acquisition_state: Literal[
        "not_configured",
        "analysis_ready",
        "confirmation_required",
        "authorization_required",
        "acquisition_failure",
        "stopped",
    ] = "not_configured"
    alternative_inputs: list[Literal["snapshot", "manual"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_context_gap_shape(self) -> "ContextGapSnapshot":
        if len(self.focus_areas) != len(set(self.focus_areas)):
            raise ValueError("ContextGapSnapshot focus_areas 不得重复")
        if len(self.supported_facts) != len(
            {(item.source_id, item.statement, item.location) for item in self.supported_facts}
        ):
            raise ValueError("ContextGapSnapshot supported_facts 不得重复")
        if len(self.information_gaps) != len({item.gap_id for item in self.information_gaps}):
            raise ValueError("ContextGapSnapshot information_gaps 的 gap_id 不得重复")
        if len(self.alternative_inputs) != len(set(self.alternative_inputs)):
            raise ValueError("ContextGapSnapshot alternative_inputs 不得重复")
        return self


class AIConflictFindingInvocation(StrictModel):
    """Conflict/Finding-only candidates paired with privacy-bounded model metadata."""

    result: AIConflictFindingResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIConflictFindingInvocation":
        if self.trace.status != "success":
            raise ValueError("AIConflictFindingInvocation 只能包含成功 Trace")
        return self


class AIAnalysisInvocation(StrictModel):
    """Model candidates paired with a safe, non-content execution trace."""

    result: AIAnalysisResult
    trace: AIModelTrace

    @model_validator(mode="after")
    def validate_successful_invocation(self) -> "AIAnalysisInvocation":
        if self.trace.status != "success":
            raise ValueError("AIAnalysisInvocation 只能包含成功 Trace")
        return self


class AIAnalysisRun(StrictModel):
    """Persistable orchestration outcome without raw material or credentials."""

    run_id: UUID
    bundle_id: UUID
    state: AIAnalysisRunState
    created_at: datetime
    completed_at: datetime
    invocation: AIAnalysisInvocation | None = None
    failure_trace: AIModelTrace | None = None
    error_code: AIAnalysisRunErrorCode | None = None
    error_message: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_run_shape(self) -> "AIAnalysisRun":
        if self.completed_at < self.created_at:
            raise ValueError("completed_at 不得早于 created_at")
        if self.state == "completed":
            if self.invocation is None:
                raise ValueError("completed run 必须包含 invocation")
            if self.failure_trace is not None or self.error_code or self.error_message:
                raise ValueError("completed run 不得包含失败字段")
            if self.invocation.result.bundle_id != self.bundle_id:
                raise ValueError("completed run 的 bundle_id 必须匹配模型结果")
            return self

        if self.invocation is not None:
            raise ValueError("失败 run 不得包含 invocation")
        if self.error_code is None or self.error_message is None:
            raise ValueError("失败 run 必须包含安全错误代码与说明")
        expected_code = {
            "configuration_required": "llm_configuration_required",
            "model_unavailable": "llm_provider_unavailable",
            "invalid_model_response": "llm_response_invalid",
        }[self.state]
        if self.error_code != expected_code:
            raise ValueError("run state 与 error_code 不匹配")
        if self.failure_trace is not None and self.failure_trace.status != "failed":
            raise ValueError("failure_trace 必须是 failed 状态")
        if self.state != "configuration_required" and self.failure_trace is None:
            raise ValueError("模型调用失败必须保留安全 failure_trace")
        return self


class EvidenceValidationIssue(StrictModel):
    """One deterministic reason for accepting, downgrading, or rejecting a candidate."""

    code: EvidenceValidationIssueCode
    message: str = Field(min_length=1, max_length=1000)


class ExternalEvidenceVerification(StrictModel):
    """One deterministic read-only probe attached to a model evidence candidate."""

    url: HttpUrl
    kind: ExternalEvidenceKind
    state: ExternalEvidenceVerificationState
    detail: str = Field(min_length=1, max_length=1000)


class EvidenceValidationResult(StrictModel):
    """Rule-layer decision for one model-proposed EvidenceCandidate."""

    evidence_candidate_id: str = Field(min_length=1, max_length=100)
    decision: EvidenceValidationDecision
    source_verified: bool
    quote_verified: bool
    location_verified: bool
    claim_scope_verified: bool | None = None
    url_membership_verified: bool | None = None
    verified_locator: SourceLocator | None = None
    resulting_type: FindingType | None = None
    external_verifications: list[ExternalEvidenceVerification] = Field(default_factory=list)
    issues: list[EvidenceValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rule_decision(self) -> "EvidenceValidationResult":
        fully_verified = self.source_verified and self.quote_verified and self.location_verified
        if self.decision == "accepted" and not fully_verified:
            raise ValueError("accepted Evidence 必须通过 source/quote/location 全部验证")
        if self.decision == "accepted" and self.claim_scope_verified is False:
            raise ValueError("claim scope 校验失败的 Evidence 不得 accepted")
        if self.decision == "accepted" and self.url_membership_verified is False:
            raise ValueError("URL 归属校验失败的 Evidence 不得 accepted")
        if self.location_verified != (self.verified_locator is not None):
            raise ValueError("location_verified 必须与 verified_locator 同时成立")
        if self.decision in {"accepted", "downgraded"} and self.resulting_type is None:
            raise ValueError("accepted/downgraded Evidence 必须提供 resulting_type")
        if self.decision in {"rejected", "needs_human_confirmation"} and self.resulting_type:
            raise ValueError("rejected/needs_human_confirmation 不得提前形成 resulting_type")
        if self.decision != "accepted" and not self.issues:
            raise ValueError("非 accepted EvidenceValidationResult 必须说明 issue")
        return self


class AIAnalysisValidationResult(StrictModel):
    """Aggregate Rule validation result; still not a final Readiness decision."""

    analysis_id: UUID
    bundle_id: UUID
    analysis_source_ids_verified: bool = True
    analysis_issues: list[EvidenceValidationIssue] = Field(default_factory=list)
    evidence_results: list[EvidenceValidationResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_evidence_results(self) -> "AIAnalysisValidationResult":
        candidate_ids = [result.evidence_candidate_id for result in self.evidence_results]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("每个 EvidenceCandidate 只能产生一个验证结果")
        if not self.analysis_source_ids_verified and not self.analysis_issues:
            raise ValueError("analysis source ID 验证失败时必须说明 issue")
        if self.analysis_source_ids_verified and self.analysis_issues:
            raise ValueError("analysis source ID 全部有效时不得包含 analysis issue")
        return self


class CandidateGraphIssue(StrictModel):
    """One deterministic reason a Conflict or Finding candidate is not admitted as-is."""

    code: CandidateGraphIssueCode
    message: str = Field(min_length=1, max_length=1000)
    evidence_candidate_ids: list[str] = Field(default_factory=list)


class ConflictCandidateValidationResult(StrictModel):
    """Rule decision for one model-proposed cross-source conflict."""

    conflict_candidate_id: str = Field(min_length=1, max_length=100)
    decision: Literal["accepted", "rejected", "needs_human_confirmation"]
    issues: list[CandidateGraphIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_conflict_decision(self) -> "ConflictCandidateValidationResult":
        if self.decision == "accepted" and self.issues:
            raise ValueError("accepted ConflictCandidate 不得包含 issue")
        if self.decision != "accepted" and not self.issues:
            raise ValueError("未受理 ConflictCandidate 必须说明 issue")
        return self


class FindingCandidateValidationResult(StrictModel):
    """Rule decision and maximum admissible strength for one Finding candidate."""

    finding_candidate_id: str = Field(min_length=1, max_length=100)
    decision: CandidateAdjudicationDecision
    resulting_type: FindingType | None = None
    issues: list[CandidateGraphIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_finding_decision(self) -> "FindingCandidateValidationResult":
        if self.decision == "accepted" and self.issues:
            raise ValueError("accepted FindingCandidate 不得包含 issue")
        if self.decision in {"accepted", "downgraded"} and self.resulting_type is None:
            raise ValueError("受理的 FindingCandidate 必须包含 resulting_type")
        if self.decision in {"rejected", "needs_human_confirmation"} and self.resulting_type:
            raise ValueError("未受理 FindingCandidate 不得包含 resulting_type")
        if self.decision != "accepted" and not self.issues:
            raise ValueError("非 accepted FindingCandidate 必须说明 issue")
        return self


class AIAnalysisAdjudicationResult(StrictModel):
    """Candidate set admitted for later status rules; it still carries no Gate."""

    analysis_id: UUID
    bundle_id: UUID
    analysis_source_ids_verified: bool = True
    analysis_issues: list[EvidenceValidationIssue] = Field(default_factory=list)
    admitted_evidence_candidate_ids: list[str] = Field(default_factory=list)
    human_confirmation_candidate_ids: list[str] = Field(default_factory=list)
    conflict_results: list[ConflictCandidateValidationResult] = Field(default_factory=list)
    finding_results: list[FindingCandidateValidationResult] = Field(default_factory=list)
    admitted_conflict_candidates: list[ConflictCandidate] = Field(default_factory=list)
    admitted_finding_candidates: list[FindingCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_admitted_candidate_sets(self) -> "AIAnalysisAdjudicationResult":
        if len(self.admitted_evidence_candidate_ids) != len(
            set(self.admitted_evidence_candidate_ids)
        ):
            raise ValueError("admitted Evidence ID 不得重复")
        if len(self.human_confirmation_candidate_ids) != len(
            set(self.human_confirmation_candidate_ids)
        ):
            raise ValueError("human confirmation candidate ID 不得重复")
        if not self.analysis_source_ids_verified and not self.analysis_issues:
            raise ValueError("analysis source ID 验证失败时必须保留 issue")
        if self.analysis_source_ids_verified and self.analysis_issues:
            raise ValueError("analysis source ID 有效时不得保留 analysis issue")

        conflict_result_ids = [item.conflict_candidate_id for item in self.conflict_results]
        finding_result_ids = [item.finding_candidate_id for item in self.finding_results]
        if len(conflict_result_ids) != len(set(conflict_result_ids)):
            raise ValueError("每个 ConflictCandidate 只能有一个验证结果")
        if len(finding_result_ids) != len(set(finding_result_ids)):
            raise ValueError("每个 FindingCandidate 只能有一个验证结果")

        accepted_conflict_ids = {
            item.conflict_candidate_id
            for item in self.conflict_results
            if item.decision == "accepted"
        }
        admitted_conflict_ids = {item.candidate_id for item in self.admitted_conflict_candidates}
        if accepted_conflict_ids != admitted_conflict_ids:
            raise ValueError("admitted ConflictCandidate 必须匹配 accepted 结果")

        admitted_finding_types = {
            item.candidate_id: item.finding_type for item in self.admitted_finding_candidates
        }
        expected_finding_types = {
            item.finding_candidate_id: item.resulting_type
            for item in self.finding_results
            if item.decision in {"accepted", "downgraded"}
        }
        if admitted_finding_types != expected_finding_types:
            raise ValueError("admitted FindingCandidate 必须匹配受理结果及 resulting_type")
        return self


class ProjectedEvidence(StrictModel):
    """One verified domain Evidence object with its AI candidate/source lineage."""

    evidence_candidate_id: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=100)
    criterion_id: ReadinessCriterionId | None = None
    evidence: Evidence

    @model_validator(mode="after")
    def validate_verified_lineage(self) -> "ProjectedEvidence":
        if self.evidence.line_start is None or self.evidence.line_end is None:
            raise ValueError("Projected Evidence 必须包含已验证的原文件起止行号")
        return self


class ProjectedFinding(StrictModel):
    """One admitted domain Finding and the Evidence candidates that support it."""

    finding_candidate_id: str = Field(min_length=1, max_length=100)
    evidence_candidate_ids: list[str] = Field(default_factory=list)
    primary_dimension_id: DimensionId
    related_dimension_ids: list[DimensionId] = Field(default_factory=list, max_length=2)
    criterion_id: ReadinessCriterionId | None = None
    readiness_effect: ReadinessEffectCandidate | None = None
    finding: Finding

    @model_validator(mode="after")
    def validate_finding_identity(self) -> "ProjectedFinding":
        if self.finding.finding_id != self.finding_candidate_id:
            raise ValueError("Projected Finding 必须保留 candidate ID")
        if len(self.evidence_candidate_ids) != len(set(self.evidence_candidate_ids)):
            raise ValueError("Projected Finding 的 Evidence ID 不得重复")
        if len(self.finding.evidence) != len(self.evidence_candidate_ids):
            raise ValueError("Projected Finding 的 Evidence 对象必须匹配候选血缘")
        return self


class ProjectedConflict(StrictModel):
    """One admitted domain EvidenceConflict with complete Evidence lineage."""

    conflict_candidate_id: str = Field(min_length=1, max_length=100)
    evidence_candidate_ids: list[str] = Field(min_length=2)
    criterion_id: ReadinessCriterionId | None = None
    disposition: ConflictDispositionCandidate | None = None
    conflict: EvidenceConflict

    @model_validator(mode="after")
    def validate_conflict_identity(self) -> "ProjectedConflict":
        if self.conflict.conflict_id != self.conflict_candidate_id:
            raise ValueError("Projected Conflict 必须保留 candidate ID")
        if len(self.evidence_candidate_ids) != len(set(self.evidence_candidate_ids)):
            raise ValueError("Projected Conflict 的 Evidence ID 不得重复")
        if len(self.conflict.sources) != len(self.evidence_candidate_ids):
            raise ValueError("Projected Conflict 的 Evidence 对象必须匹配候选血缘")
        return self


class AIAnalysisDomainProjection(StrictModel):
    """Stable domain inputs for later readiness status and Gate rules."""

    analysis_id: UUID
    bundle_id: UUID
    analysis_source_ids_verified: bool = True
    analysis_issues: list[EvidenceValidationIssue] = Field(default_factory=list)
    evidence: list[ProjectedEvidence] = Field(default_factory=list)
    findings: list[ProjectedFinding] = Field(default_factory=list)
    conflicts: list[ProjectedConflict] = Field(default_factory=list)
    unresolved_questions: list[UnresolvedQuestion] = Field(default_factory=list)
    human_confirmation_candidate_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_projection_graph(self) -> "AIAnalysisDomainProjection":
        evidence_ids = [item.evidence_candidate_id for item in self.evidence]
        finding_ids = [item.finding_candidate_id for item in self.findings]
        conflict_ids = [item.conflict_candidate_id for item in self.conflicts]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Projected Evidence ID 不得重复")
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("Projected Finding ID 不得重复")
        if len(conflict_ids) != len(set(conflict_ids)):
            raise ValueError("Projected Conflict ID 不得重复")
        known_evidence_ids = set(evidence_ids)
        if any(
            not set(item.evidence_candidate_ids) <= known_evidence_ids for item in self.findings
        ):
            raise ValueError("Projected Finding 引用了未投影的 Evidence")
        if any(
            not set(item.evidence_candidate_ids) <= known_evidence_ids for item in self.conflicts
        ):
            raise ValueError("Projected Conflict 引用了未投影的 Evidence")
        if len(self.human_confirmation_candidate_ids) != len(
            set(self.human_confirmation_candidate_ids)
        ):
            raise ValueError("human confirmation candidate ID 不得重复")
        admitted_candidate_ids = {*evidence_ids, *finding_ids, *conflict_ids}
        if set(self.human_confirmation_candidate_ids) & admitted_candidate_ids:
            raise ValueError("待人工确认候选不得同时出现在受理投影中")
        if not self.analysis_source_ids_verified and not self.analysis_issues:
            raise ValueError("来源验证失败的 Projection 必须保留 analysis issue")
        if self.analysis_source_ids_verified and self.analysis_issues:
            raise ValueError("来源验证成功的 Projection 不得包含 analysis issue")
        return self


class HumanFeedback(StrictModel):
    """Human correction intent kept separate from model output and Rule decisions."""

    feedback_id: UUID
    assessment_id: UUID | None = None
    revision: int | None = Field(default=None, ge=1)
    target_type: HumanFeedbackTarget
    target_id: str = Field(min_length=1, max_length=100)
    action: HumanFeedbackAction
    comment: str | None = Field(default=None, min_length=1, max_length=4000)
    requires_reassessment: bool = False
    submitted_at: datetime

    @model_validator(mode="after")
    def validate_feedback_content(self) -> "HumanFeedback":
        if self.action in {"question", "correct", "supplement"} and self.comment is None:
            raise ValueError("question/correct/supplement HumanFeedback 必须包含 comment")
        return self


class HumanEvidenceResolution(StrictModel):
    """A human-selected occurrence that is still subject to deterministic validation."""

    source_id: str = Field(min_length=1, max_length=100)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    quote: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_line_range(self) -> "HumanEvidenceResolution":
        if self.line_end < self.line_start:
            raise ValueError("line_end 不得小于 line_start")
        return self


class HumanSourceSubmission(StrictModel):
    """User-provided material; it is evidence input, never an automatically trusted Fact."""

    material_type: MaterialType = "Other"
    title: str = Field(min_length=1, max_length=500)
    source_path: str = Field(min_length=1, max_length=1000)
    source_url: HttpUrl | None = None
    content: str = Field(min_length=1, max_length=100_000)


class AssessmentFeedbackRequest(StrictModel):
    """Confirm, question, correct, or supplement one displayed Finding or Evidence."""

    target_type: HumanFeedbackTarget
    target_id: str = Field(min_length=1, max_length=100)
    action: HumanFeedbackAction
    comment: str | None = Field(default=None, min_length=1, max_length=4000)
    evidence_resolution: HumanEvidenceResolution | None = None
    source_submission: HumanSourceSubmission | None = None

    @model_validator(mode="after")
    def validate_feedback_shape(self) -> "AssessmentFeedbackRequest":
        if self.evidence_resolution is not None and self.target_type != "evidence":
            raise ValueError("evidence_resolution 只适用于 Evidence 反馈")
        if self.action == "supplement" and self.source_submission is None:
            raise ValueError("supplement 必须提供 source_submission")
        if self.action == "correct" and not (
            self.source_submission is not None or self.evidence_resolution is not None
        ):
            raise ValueError("correct 必须提供来源材料或 Evidence 定位修正")
        if self.action in {"question", "correct", "supplement"} and self.comment is None:
            raise ValueError("question/correct/supplement 必须说明反馈内容")
        return self


class AssessmentFeedbackResponse(StrictModel):
    """Feedback receipt plus the latest deterministically adjudicated revision."""

    assessment_id: UUID
    revision: int = Field(ge=1)
    feedback: HumanFeedback
    requires_reassessment: bool
    reassessment_performed: bool
    reassessment_state: HumanReassessmentState
    reassessment_detail: str | None = Field(default=None, max_length=500)
    assessment: ReadinessAssessment


class AssessmentRevision(StrictModel):
    """An immutable, API-safe Assessment snapshot after a Human review event."""

    revision: int = Field(ge=0)
    created_at: datetime
    feedback: HumanFeedback | None = None
    assessment: ReadinessAssessment


class AssessmentRevisionChange(StrictModel):
    """A compact, source-safe comparison between consecutive revisions."""

    from_revision: int = Field(ge=0)
    to_revision: int = Field(ge=1)
    overall_gate_changed: bool
    changed_dimension_ids: list[str] = Field(default_factory=list)
    added_finding_ids: list[str] = Field(default_factory=list)
    removed_finding_ids: list[str] = Field(default_factory=list)
    added_evidence_ids: list[str] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)


class AssessmentRevisionHistory(StrictModel):
    """Assessment revision snapshots and deterministic diffs for Human review."""

    assessment_id: UUID
    revisions: list[AssessmentRevision] = Field(default_factory=list)
    changes: list[AssessmentRevisionChange] = Field(default_factory=list)


class FinalInvestmentDecisionRequest(StrictModel):
    """The user's decision; it cannot grant execution authority or replace the Rule Gate."""

    decision: FinalInvestmentDecisionValue
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)


class FinalInvestmentDecisionRecord(StrictModel):
    """Auditable human decision recorded alongside, but separate from, the Rule Gate."""

    decision_id: UUID
    assessment_id: UUID
    revision: int = Field(ge=0)
    decision: FinalInvestmentDecisionValue
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    rule_gate_at_decision: OverallGate | None
    gate_available_at_decision: bool
    submitted_at: datetime
