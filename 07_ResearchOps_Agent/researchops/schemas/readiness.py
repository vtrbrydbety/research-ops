"""Reproduction Readiness Assessment 的稳定 API 数据契约。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from researchops.schemas.task import StrictModel

ReadinessStatus = Literal["Ready", "Warning", "Blocked", "Unknown"]
OverallGate = Literal["PROCEED", "CONDITIONAL PROCEED", "PAUSE"]
AnalysisState = Literal[
    "empty",
    "processing",
    "partial_result",
    "acquisition_failure",
    "partial_material_acquisition",
    "tool_failure",
    "human_confirmation_required",
    "authorization_required",
    "manual_input_required",
    "conflict",
    "configuration_required",
    "model_unavailable",
    "invalid_model_response",
    "evidence_validation_failure",
]
FindingType = Literal["Fact", "Inference", "Unknown"]
EvidenceVerificationStatus = Literal["Located Only", "Corroborated", "Unverifiable"]
EvidenceSourceType = Literal["Material", "User Context"]
MaterialType = Literal[
    "Paper",
    "Repository",
    "README",
    "Supplementary",
    "Dataset Page",
    "Checkpoint-Release",
    "Config",
    "Issue",
    "Project Page",
    "Other",
]
NextActionType = Literal[
    "Resolve Blocker",
    "Resolve Gate-critical Unknown",
    "Mitigate Warning",
    "Minimum Validation",
    "Higher-cost Reproduction",
]
DimensionId = Literal["RD-01", "RD-02", "RD-03"]
CriterionOutcome = Literal["supported", "warning", "blocked", "unknown"]
EvaluationConflictType = Literal[
    "Dataset Split",
    "Metric Definition",
    "Aggregation",
    "Paper-Code Setting",
    "Other",
]
TargetType = Literal["repository", "paper_title", "doi", "arxiv", "project_page"]
ResolutionStatus = Literal["identified", "requires_confirmation", "unresolved"]
AssessmentJobState = Literal["queued", "running", "completed", "failed"]
AssessmentAuditActor = Literal["connector", "ai", "rule", "human", "system"]
AssessmentAuditOutcome = Literal["completed", "partial", "failed", "recorded", "unavailable"]
AssessmentJobPhase = Literal[
    "queued",
    "resolving_target",
    "acquiring_context",
    "collecting_materials",
    "building_material_bundle",
    "ai_research_planning",
    "ai_evidence_analysis",
    "validating_evidence",
    "ai_conflict_finding_analysis",
    "validating_candidates",
    "rule_adjudication",
    "validating_output",
    "completed",
    "failed",
]


class TargetResolutionRequest(StrictModel):
    """将用户输入转换为统一目标的请求。"""

    target_type: TargetType
    target_entry: str = Field(min_length=1, max_length=2000)


class ResolvedTarget(StrictModel):
    """材料获取与 Assessment 共用的规范化目标。"""

    target_type: TargetType
    source_entry: str = Field(min_length=1, max_length=2000)
    display_name: str = Field(min_length=1, max_length=500)
    canonical_id: str = Field(min_length=1, max_length=500)
    canonical_url: HttpUrl | None = None
    resolution_method: Literal[
        "direct_url",
        "normalized_identifier",
        "title_candidate",
    ]


class TargetCandidate(StrictModel):
    """目标身份存在歧义时供用户确认的候选项。"""

    candidate_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=1000)
    resolved_target: ResolvedTarget


class TargetResolutionResponse(StrictModel):
    """目标解析结果；歧义和 Evidence 冲突是两个独立状态。"""

    status: ResolutionStatus
    data_mode: Literal["deterministic", "live_metadata"]
    source_entry: str = Field(min_length=1, max_length=2000)
    analysis_state: AnalysisState | None = None
    resolved_target: ResolvedTarget | None = None
    candidates: list[TargetCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_resolution_shape(self) -> "TargetResolutionResponse":
        """确保每种解析状态只携带适用的数据。"""

        if self.status == "identified" and self.resolved_target is None:
            raise ValueError("identified 状态必须包含 resolved_target")
        if self.status == "identified" and self.candidates:
            raise ValueError("identified 状态不得同时包含候选项")
        if self.status == "requires_confirmation" and len(self.candidates) < 2:
            raise ValueError("requires_confirmation 状态至少需要两个候选项")
        if self.status == "requires_confirmation" and self.resolved_target is not None:
            raise ValueError("requires_confirmation 状态不得提前确定 resolved_target")
        if self.status == "unresolved" and (self.resolved_target is not None or self.candidates):
            raise ValueError("unresolved 状态不得携带目标或候选项")
        if self.analysis_state is not None and self.status != "unresolved":
            raise ValueError("Target analysis_state 仅适用于 unresolved 技术状态")
        return self


class AssessmentRequest(StrictModel):
    """创建 Readiness Assessment 的请求。"""

    target_type: TargetType
    target_entry: str = Field(min_length=1, max_length=2000)
    resolved_target: ResolvedTarget | None = Field(
        default=None,
        description="候选确认后由前端回传的规范化目标。",
    )
    environment_mode: Literal["readonly", "snapshot", "manual", "later"] = Field(
        default="readonly",
        description="用户选择的环境信息提供方式。",
    )
    environment_authorized: bool = Field(
        default=False,
        description="仅表示用户已在现有授权界面批准本次只读本机环境采集。",
    )
    environment_authorization_token: str | None = Field(
        default=None,
        min_length=32,
        max_length=200,
        description="授权界面向本地 API 申请的短期内存令牌。",
    )
    environment_input: str | None = Field(
        default=None,
        max_length=50_000,
        description="Snapshot 或 Manual Input 提供的环境文本；不会作为命令执行。",
    )

    @model_validator(mode="after")
    def validate_environment_authorization_shape(self) -> "AssessmentRequest":
        if self.environment_authorized and self.environment_mode != "readonly":
            raise ValueError("只有 readonly 模式可以声明本机环境授权")
        if self.environment_authorized != bool(self.environment_authorization_token):
            raise ValueError("environment_authorized 必须与短期授权令牌同时提供")
        return self


class EnvironmentAuthorizationResponse(StrictModel):
    """授权按钮触发后返回的短期令牌。"""

    authorization_token: str = Field(min_length=32, max_length=200)
    expires_at: datetime
    access_mode: Literal["read-only"] = "read-only"


class Evidence(StrictModel):
    """一条可定位的 Assessment 证据。"""

    evidence_id: str | None = Field(default=None, min_length=1, max_length=100)
    source_id: str | None = Field(default=None, min_length=1, max_length=100)
    evidence_type: FindingType
    verification_status: EvidenceVerificationStatus
    source_type: EvidenceSourceType
    material_type: MaterialType | None = None
    summary: str = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=500)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    excerpt: str = Field(min_length=1, max_length=2000)
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_line_range(self) -> "Evidence":
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("Evidence line_start 与 line_end 必须同时提供或同时省略")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("Evidence line_end 不得小于 line_start")
        return self


class EvidenceConflict(StrictModel):
    """同一复现条件由多个来源给出不兼容信息时的冲突记录。"""

    conflict_id: str = Field(min_length=1, max_length=100)
    condition_key: str = Field(min_length=1, max_length=300)
    dimension_ids: list[DimensionId] = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=2000)
    gate_critical: bool = False
    status: Literal["unresolved", "resolved"] = "unresolved"
    sources: list[Evidence] = Field(min_length=2)


class EvaluationSignal(StrictModel):
    """P06-light Evaluation Conflict Signal，不升级为核心 Dimension。"""

    signal_id: str = Field(min_length=1, max_length=100)
    status: Literal["Warning", "Unknown"]
    conflict_type: EvaluationConflictType
    summary: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[Evidence] = Field(default_factory=list)
    gate_impact: str = Field(min_length=1, max_length=1000)


class ResourceItem(StrictModel):
    """Resource Constraint 中一个现有表格行的数据。"""

    resource: Literal["GPU / VRAM", "Disk", "Time budget"]
    current: str = Field(min_length=1, max_length=300)
    required: str = Field(min_length=1, max_length=300)


class ResourceSignal(StrictModel):
    """不升级为核心 Dimension 的资源约束信号。"""

    status: Literal["Blocked", "Warning", "Unknown"]
    summary: str = Field(min_length=1, max_length=1000)
    gate_impact: str = Field(min_length=1, max_length=1000)
    items: list[ResourceItem] = Field(default_factory=list, max_length=3)
    evidence: Evidence | None = None


class Finding(StrictModel):
    """影响一个 Readiness Dimension 的结构化结论。"""

    finding_id: str = Field(min_length=1, max_length=100)
    condition: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    finding_type: FindingType
    gate_critical: bool = False
    readiness_impact: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(default_factory=list)


class ReadinessDimension(StrictModel):
    """RD-01、RD-02 或 RD-03 的聚合结果。"""

    dimension_id: DimensionId
    name: str = Field(min_length=1, max_length=200)
    status: ReadinessStatus | None = None
    analysis_state: AnalysisState | None = Field(
        default=None,
        description="尚未形成业务判断时使用；不得用 Processing 等值替代 status。",
    )
    summary: str = Field(min_length=1, max_length=2000)
    gate_impact: str = Field(min_length=1, max_length=1000)
    findings: list[Finding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimension_state(self) -> "ReadinessDimension":
        """业务 Status 与处理状态互斥，并保证已形成判断时有 Finding。"""

        if (self.status is None) == (self.analysis_state is None):
            raise ValueError("Dimension 必须且只能填写 status 或 analysis_state")
        if self.status is not None and not self.findings:
            raise ValueError("已形成业务 status 的 Dimension 必须包含至少一个 Finding")
        return self


class NextAction(StrictModel):
    """当前最优先执行的一步。"""

    action_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=1000)
    action_type: NextActionType
    priority: int = Field(default=1, ge=1)
    reason_refs: list[str] = Field(min_length=1)


class CriterionAdjudication(StrictModel):
    """Rule 层对一个冻结 Gate criterion 的可审计裁决。"""

    criterion_id: str = Field(min_length=1, max_length=100)
    dimension_id: DimensionId
    outcome: CriterionOutcome
    reason: str = Field(min_length=1, max_length=1000)
    trigger_refs: list[str] = Field(min_length=1)


class ReadinessAdjudicationResult(StrictModel):
    """AI 候选经确定性规则映射后的状态、Signal 与 Gate。"""

    analysis_id: UUID
    bundle_id: UUID
    decision_available: bool
    dimensions: list[ReadinessDimension] = Field(default_factory=list, max_length=3)
    resource_signal: ResourceSignal | None = None
    evaluation_signal: EvaluationSignal | None = None
    overall_gate: OverallGate | None = None
    main_risk: str | None = Field(default=None, min_length=1, max_length=1000)
    first_next_action: NextAction | None = None
    trigger_refs: list[str] = Field(default_factory=list)
    criterion_decisions: list[CriterionAdjudication] = Field(default_factory=list)
    unavailable_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    rule_trace: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "ReadinessAdjudicationResult":
        if self.decision_available:
            if [item.dimension_id for item in self.dimensions] != ["RD-01", "RD-02", "RD-03"]:
                raise ValueError("可用裁决必须按固定顺序包含三个核心 Dimension")
            if (
                self.overall_gate is None
                or self.main_risk is None
                or self.first_next_action is None
            ):
                raise ValueError("可用裁决必须包含 Gate、Main Risk 与 First Next Action")
            if not self.trigger_refs or self.unavailable_reason is not None:
                raise ValueError("可用裁决必须包含 trigger_refs 且不得包含 unavailable_reason")
        else:
            if (
                self.dimensions
                or self.overall_gate is not None
                or self.first_next_action is not None
            ):
                raise ValueError("不可用裁决不得伪造 Dimension、Gate 或 Next Action")
            if self.main_risk is not None or self.trigger_refs or self.criterion_decisions:
                raise ValueError("不可用裁决不得伪造业务风险、触发项或 criterion 结果")
            if self.unavailable_reason is None:
                raise ValueError("不可用裁决必须说明 unavailable_reason")
        return self


class AssessmentAuditEvent(StrictModel):
    """Content-free lineage event spanning Connector, AI, Rule, and Human boundaries."""

    event_id: str = Field(min_length=1, max_length=100, pattern=r"^audit-[a-f0-9]{20}$")
    actor: AssessmentAuditActor
    stage: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    outcome: AssessmentAuditOutcome
    occurred_at: datetime
    refs: list[str] = Field(default_factory=list, max_length=128)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    model_trace_id: UUID | None = None
    provider_request_id: str | None = Field(default=None, min_length=1, max_length=300)
    duration_ms: int | None = Field(default=None, ge=0, le=600_000)
    detail: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_model_metadata(self) -> "AssessmentAuditEvent":
        if self.actor == "ai" and self.outcome == "completed":
            if self.model is None or self.model_trace_id is None:
                raise ValueError("成功 AI 审计事件必须包含 model 与 model_trace_id")
        if self.actor != "ai" and any(
            value is not None
            for value in (self.model, self.model_trace_id, self.provider_request_id)
        ):
            raise ValueError("非 AI 审计事件不得携带模型调用元数据")
        if len(self.refs) != len(set(self.refs)):
            raise ValueError("审计事件 refs 不得重复")
        return self


class ReadinessAssessment(StrictModel):
    """前端可直接消费的完整 Readiness Assessment。"""

    assessment_id: UUID
    status: Literal["completed", "partial"]
    data_mode: Literal["live_repository", "live_metadata", "normalized_target"] = Field(
        description="区分真实材料采集、公开元数据解析与仅完成标识符规范化。",
    )
    target_type: TargetType
    target_entry: str = Field(min_length=1, max_length=2000)
    resolved_target: ResolvedTarget
    generated_at: datetime
    dimensions: list[ReadinessDimension] = Field(min_length=3, max_length=3)
    analysis_state: AnalysisState | None = Field(
        default=None,
        description="独立于业务 Readiness Status 的处理或获取状态。",
    )
    gate_available: bool = Field(
        description="是否已具备形成三种正式 Overall Gate 之一的判断基础。",
    )
    overall_gate: OverallGate | None
    trigger_refs: list[str] = Field(default_factory=list)
    main_risk: str = Field(min_length=1, max_length=1000)
    first_next_action: NextAction
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    evaluation_signal: EvaluationSignal | None = None
    resource_signal: ResourceSignal | None = None
    trace_summary: list[str] = Field(default_factory=list)
    audit_trail: list[AssessmentAuditEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_core_dimensions(self) -> "ReadinessAssessment":
        """确保三个核心 Dimension 完整且顺序稳定。"""

        actual = [dimension.dimension_id for dimension in self.dimensions]
        expected = ["RD-01", "RD-02", "RD-03"]
        if actual != expected:
            raise ValueError("dimensions 必须按 RD-01、RD-02、RD-03 顺序完整返回")
        if self.gate_available != (self.overall_gate is not None):
            raise ValueError("gate_available 必须与 overall_gate 是否存在保持一致")
        if self.gate_available != bool(self.trigger_refs):
            raise ValueError("Gate 可用时必须提供 trigger_refs，不可用时不得伪造触发引用")
        if self.status == "completed" and not self.gate_available:
            raise ValueError("completed Assessment 必须形成 Overall Gate")
        if self.status == "completed" and self.analysis_state is not None:
            raise ValueError("completed Assessment 不得携带未完成的 analysis_state")
        if self.status == "completed" and any(
            dimension.status is None for dimension in self.dimensions
        ):
            raise ValueError("completed Assessment 的三个 Dimension 都必须形成业务 status")
        if self.analysis_state is not None and self.status != "partial":
            raise ValueError("analysis_state 仅适用于 partial Assessment")
        event_ids = [event.event_id for event in self.audit_trail]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("audit_trail event_id 不得重复")
        return self


class AssessmentJobResponse(StrictModel):
    """Safe progress snapshot for one asynchronous Assessment request."""

    job_id: UUID
    state: AssessmentJobState
    phase: AssessmentJobPhase
    created_at: datetime
    updated_at: datetime
    material_source_count: int | None = Field(default=None, ge=0, le=64)
    material_titles: list[str] = Field(default_factory=list, max_length=64)
    evidence_candidate_count: int | None = Field(default=None, ge=0)
    validated_evidence_count: int | None = Field(default=None, ge=0)
    assessment: ReadinessAssessment | None = None
    error_message: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_job_shape(self) -> "AssessmentJobResponse":
        if self.state == "completed" and self.assessment is None:
            raise ValueError("completed Assessment job 必须包含 assessment")
        if self.state != "completed" and self.assessment is not None:
            raise ValueError("未完成 Assessment job 不得提前包含 assessment")
        if self.state == "failed" and self.error_message is None:
            raise ValueError("failed Assessment job 必须说明安全错误")
        if self.state != "failed" and self.error_message is not None:
            raise ValueError("非 failed Assessment job 不得携带 error_message")
        return self
