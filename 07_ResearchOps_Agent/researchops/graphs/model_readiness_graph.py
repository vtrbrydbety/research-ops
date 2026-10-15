"""LangGraph main chain for the model-backed Readiness MVP."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from researchops.schemas import (
    AIAnalysisAdjudicationResult,
    AIAnalysisDomainProjection,
    AIAnalysisResult,
    AIAnalysisValidationResult,
    AIModelTrace,
    AnalysisState,
    AssessmentRequest,
    ContextGapFocus,
    EvidenceFindingConditionContext,
    EvidenceFindingInput,
    MaterialBundle,
    MaterialBundleBuildReport,
    NextAction,
    ReadinessAdjudicationResult,
    ReadinessAssessment,
    ReadinessDimension,
    ResearchLoopResult,
    ResolvedTarget,
    TargetResolutionRequest,
)
from researchops.services.analysis_boundaries import (
    EvidenceFindingDraftModel,
    ResearchLoopRunner,
)
from researchops.services.candidate_adjudication import (
    CandidateGraphValidationError,
    DeterministicCandidateGraphValidator,
)
from researchops.services.decision_audit import build_assessment_audit
from researchops.services.deepseek_analysis import (
    AIModelConfigurationError,
    AIModelError,
    AIModelResponseError,
)
from researchops.services.domain_projection import (
    DomainProjectionError,
    ReadinessDomainProjectionService,
)
from researchops.services.environment_facts import EnvironmentFacts, EnvironmentFactService
from researchops.services.evidence_validation import (
    DeterministicEvidenceRuleValidator,
    EvidenceRuleValidationError,
)
from researchops.services.local_evidence_finding_rules import LocalEvidenceFindingRuleService
from researchops.services.material_context import MaterialBundleBuilder, MaterialContextError
from researchops.services.paper_materials import PaperMaterialCollectionError, PaperMaterials
from researchops.services.readiness_adjudication import DeterministicReadinessAdjudicator
from researchops.services.readiness_assessment import ReadinessAssessmentService
from researchops.services.repository_materials import (
    RepositoryCollectionError,
    RepositoryMaterials,
)


class ModelReadinessGraphState(TypedDict, total=False):
    """Internal state with separate AI, Rule, and workflow failure fields."""

    request: AssessmentRequest
    resolved_target: ResolvedTarget
    environment_facts: EnvironmentFacts
    repository_materials: RepositoryMaterials
    paper_materials: PaperMaterials
    linked_repository_materials: RepositoryMaterials
    material_partial: bool
    material_bundle: MaterialBundle
    initial_material_bundle: MaterialBundle
    build_report: MaterialBundleBuildReport
    research_loop: ResearchLoopResult
    local_analysis: AIAnalysisResult
    local_evidence_invocations: list
    local_completed_condition_refs: list[str]
    evidence_validation: AIAnalysisValidationResult
    candidate_adjudication: AIAnalysisAdjudicationResult
    projection: AIAnalysisDomainProjection
    readiness: ReadinessAdjudicationResult
    assessment: ReadinessAssessment
    failure_state: AnalysisState
    failure_message: str
    failure_trace: AIModelTrace
    workflow_trace: list[str]


def _trace(state: ModelReadinessGraphState, message: str) -> list[str]:
    return [*state.get("workflow_trace", []), message]


def _research_gap_refs(result: ResearchLoopResult) -> str:
    """Return a bounded, content-free Gap reference list for workflow Trace."""
    if not result.rounds:
        return "none"
    latest = result.rounds[-1]
    if latest.context_gap is not None:
        return (
            ",".join(item.gap_id for item in latest.context_gap.result.information_gaps[:16])
            or "none"
        )
    if latest.planning is not None:
        return (
            ",".join(item.gap_id for item in latest.planning.result.information_gaps[:16]) or "none"
        )
    return "none"


def _research_loop_has_tool_failures(result: ResearchLoopResult) -> bool:
    return any(
        request.status == "failed"
        for round_record in result.rounds
        if round_record.execution is not None
        for request in round_record.execution.request_results
    )


def _configuration_failure(exc: AIModelConfigurationError) -> tuple[str, str]:
    """Translate safe provider status metadata into an actionable partial result."""
    error_type = exc.trace.error_type if exc.trace is not None else None
    if error_type == "http_402":
        return (
            "The model account has insufficient balance; AI analysis was not started.",
            "ai analysis: failed - model account balance required.",
        )
    if error_type == "http_401":
        return (
            "The model provider rejected the configured API Key; AI analysis was not started.",
            "ai analysis: failed - API Key rejected.",
        )
    if error_type == "http_403":
        return (
            "The model account is not authorized for the configured model; AI analysis was not started.",
            "ai analysis: failed - model access denied.",
        )
    if error_type in {"http_400", "http_404", "http_422"}:
        return (
            "The model provider rejected the configured model or API mode; AI analysis was not started.",
            "ai analysis: failed - model request configuration rejected.",
        )
    return (
        "The model API configuration is not available; AI analysis was not started.",
        "ai analysis: failed - model configuration required.",
    )


def _response_contract_failure(
    exc: AIModelResponseError, *, stage: str, artifact: str
) -> tuple[str, str]:
    """Expose only bounded execution metadata for a rejected model response.

    Model text and raw validation details are intentionally not copied into an
    assessment or workflow trace.  The retained category, transport, and
    bounded attempt count are enough to distinguish a schema failure from a
    business Unknown and make an operator retry actionable.
    """
    trace = exc.trace
    error_type = trace.error_type if trace is not None else "contract_error"
    api_mode = trace.api_mode if trace is not None and trace.api_mode else "unknown"
    attempts = trace.attempts if trace is not None else 0
    error_detail = trace.error_detail if trace is not None else None
    detail_suffix = f" Contract: {error_detail}." if error_detail else ""
    return (
        (
            f"The model returned an invalid structured {artifact} response after "
            f"{attempts} bounded attempt(s); the current batch was not admitted."
            f"{detail_suffix}"
        ),
        (
            f"{stage}: failed - invalid structured model response "
            f"({error_type}; mode={api_mode}; attempts={attempts}; "
            f"contract={error_detail or 'unavailable'})."
        ),
    )


def build_model_readiness_graph(
    *,
    assessment_service: ReadinessAssessmentService,
    evidence_model: EvidenceFindingDraftModel,
    research_loop: ResearchLoopRunner | None = None,
    material_builder: MaterialBundleBuilder | None = None,
    environment_service: EnvironmentFactService | None = None,
    evidence_validator: DeterministicEvidenceRuleValidator | None = None,
    candidate_validator: DeterministicCandidateGraphValidator | None = None,
    projector: ReadinessDomainProjectionService | None = None,
    readiness_adjudicator: DeterministicReadinessAdjudicator | None = None,
) -> CompiledStateGraph:
    """Compile the production model-backed workflow with explicit failure routing."""

    bundles = material_builder or MaterialBundleBuilder()
    environments = environment_service or assessment_service.environment_fact_service
    evidence_rules = evidence_validator or DeterministicEvidenceRuleValidator()
    candidate_rules = candidate_validator or DeterministicCandidateGraphValidator()
    domain = projector or ReadinessDomainProjectionService()
    readiness_rules = readiness_adjudicator or DeterministicReadinessAdjudicator()
    local_draft_rules = LocalEvidenceFindingRuleService(
        evidence_validator=evidence_rules,
        candidate_validator=candidate_rules,
        projector=domain,
        readiness_adjudicator=readiness_rules,
    )
    # A model that only exposes the local Draft method is a feedback-only test
    # adapter. Production first-pass routing requires the complete phased
    # Context/Gap + Tool Acquisition + Evidence/Finding boundary set.
    use_local_evidence_finding = all(
        callable(getattr(evidence_model, method, None))
        for method in (
            "analyze_context_gaps",
            "plan_tool_acquisition",
            "draft_evidence_findings",
        )
    )

    def fail(
        state: ModelReadinessGraphState,
        failure_state: AnalysisState,
        message: str,
        trace_message: str,
        failure_trace: AIModelTrace | None = None,
    ) -> ModelReadinessGraphState:
        result: ModelReadinessGraphState = {
            "failure_state": failure_state,
            "failure_message": message,
            "workflow_trace": _trace(state, trace_message),
        }
        if failure_trace is not None:
            result["failure_trace"] = failure_trace
        return result

    def resolve_target(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        target = assessment_service.resolve_target(state["request"])
        return {
            "resolved_target": target,
            "workflow_trace": _trace(state, f"resolve_target: success - {target.canonical_id}"),
        }

    def acquire_environment(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        request = state["request"]
        try:
            facts = environments.acquire(
                request.environment_mode,
                authorized=request.environment_authorized,
                supplied_text=request.environment_input,
            )
        except Exception:  # Environment collection is optional and must remain read-only.
            return {
                "material_partial": True,
                "workflow_trace": _trace(
                    state,
                    "acquire_environment: partial - environment facts were not acquired.",
                ),
            }
        result: ModelReadinessGraphState = {
            "workflow_trace": _trace(
                state,
                "acquire_environment: success - read-only facts acquired."
                if facts is not None
                else "acquire_environment: skipped - no environment facts supplied.",
            )
        }
        if facts is not None:
            result["environment_facts"] = facts
        return result

    def collect_materials(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        target = state["resolved_target"]
        if target.target_type == "repository":
            try:
                repository = assessment_service.collect_repository_materials(target)
            except RepositoryCollectionError:
                return fail(
                    state,
                    "acquisition_failure",
                    "Public Repository materials could not be acquired for this assessment.",
                    "collect_materials: failed - repository acquisition failed.",
                )
            return {
                "repository_materials": repository,
                "workflow_trace": _trace(
                    state, "collect_materials: success - repository materials collected read-only."
                ),
            }

        try:
            paper = assessment_service.paper_material_collector.collect(target)
        except PaperMaterialCollectionError:
            return fail(
                state,
                "acquisition_failure",
                "Public paper or project-page materials could not be acquired.",
                "collect_materials: failed - target material acquisition failed.",
            )

        result: ModelReadinessGraphState = {"paper_materials": paper}
        linked_repository = None
        for repository_url in paper.repository_urls:
            resolution = assessment_service.target_resolution_service.resolve(
                TargetResolutionRequest(target_type="repository", target_entry=repository_url)
            )
            if resolution.resolved_target is None:
                continue
            try:
                linked_repository = assessment_service.collect_repository_materials(
                    resolution.resolved_target
                )
            except RepositoryCollectionError:
                result["material_partial"] = True
                continue
            break
        if linked_repository is not None:
            result["linked_repository_materials"] = linked_repository
        result["workflow_trace"] = _trace(
            state,
            "collect_materials: success - target material and linked repository collected."
            if linked_repository is not None
            else "collect_materials: partial - target material collected without a linked repository."
            if paper.repository_urls
            else "collect_materials: success - target material collected; no repository was linked.",
        )
        return result

    def build_bundle(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        target = state["resolved_target"]
        environment = state.get("environment_facts")
        try:
            if "repository_materials" in state:
                build = bundles.from_repository(
                    target,
                    state["repository_materials"],
                    environment_facts=environment,
                )
            elif "linked_repository_materials" in state:
                build = bundles.from_paper_and_repository(
                    target,
                    state["paper_materials"],
                    state["linked_repository_materials"],
                    environment_facts=environment,
                )
            else:
                build = bundles.from_paper(
                    target,
                    state["paper_materials"],
                    environment_facts=environment,
                )
        except (MaterialContextError, ValueError):
            return fail(
                state,
                "acquisition_failure",
                "Collected materials could not be converted into a safe model context.",
                "build_material_bundle: failed - safe context construction failed.",
            )
        return {
            "material_bundle": build.bundle,
            "build_report": build.report,
            "workflow_trace": _trace(
                state,
                f"build_material_bundle: success - {len(build.bundle.sources)} bounded sources.",
            ),
        }

    def ai_local_evidence_findings(
        state: ModelReadinessGraphState,
    ) -> ModelReadinessGraphState:
        """Run the new first-pass Evidence/Finding phase in bounded condition batches."""
        draft_method = getattr(evidence_model, "draft_evidence_findings", None)
        if not callable(draft_method):
            return fail(
                state,
                "invalid_model_response",
                "The configured model does not implement the required local Evidence/Finding phase.",
                "ai_local_evidence_finding: failed - phase boundary is unavailable.",
            )
        bundle = state["material_bundle"]
        source_ids = [source.source_id for source in bundle.sources]
        contexts_by_scope = _initial_condition_contexts()
        phase_context = _latest_phase_context(state.get("research_loop"))
        # Initial core readiness still evaluates every Rule-owned condition, but
        # the AI boundary is one current Condition at a time.  This keeps source
        # relationships local and prevents one malformed, oversized Dimension
        # graph from invalidating unrelated Conditions.
        batches = [[condition] for values in contexts_by_scope.values() for condition in values]
        analyses: list[AIAnalysisResult] = []
        invocations = []
        completed_condition_refs: list[str] = []
        active_condition_ref = "unknown"
        try:
            jobs: list[tuple[str, EvidenceFindingInput]] = []
            for conditions in batches:
                condition_ref = conditions[0].condition_ref
                condition_scopes = {item.primary_dimension for item in conditions}
                gaps = (
                    [
                        gap
                        for gap in phase_context.result.information_gaps
                        if gap.scope_ref in condition_scopes
                    ]
                    if phase_context is not None
                    else []
                )
                jobs.append(
                    (
                        condition_ref,
                        EvidenceFindingInput(
                            bundle=bundle,
                            focus=ContextGapFocus(scope_refs=sorted(condition_scopes)),
                            condition_contexts=conditions,
                            current_information_gaps=gaps,
                            relevant_source_ids=source_ids,
                        ),
                    )
                )

            failures: list[tuple[str, Exception]] = []
            worker_count = min(3, len(jobs))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(copy_context().run, draft_method, context)
                    for _condition_ref, context in jobs
                ]
                for (condition_ref, context), future in zip(jobs, futures, strict=True):
                    try:
                        invocation = future.result()
                        outcome = local_draft_rules.adjudicate(
                            context,
                            invocation.result,
                        )
                    except Exception as exc:  # Classified below after all bounded work settles.
                        from researchops.services.access_store import AccessError

                        if isinstance(exc, AccessError):
                            raise
                        failures.append((condition_ref, exc))
                        continue
                    analyses.append(outcome.analysis)
                    invocations.append(invocation)
                    completed_condition_refs.append(condition_ref)

            if failures:
                active_condition_ref, failure = failures[0]
                raise failure
        except AIModelConfigurationError as exc:
            message, trace_message = _configuration_failure(exc)
            return fail(
                state,
                "configuration_required",
                message,
                f"ai_local_evidence_finding: {trace_message}",
                exc.trace,
            )
        except AIModelResponseError as exc:
            message, trace_message = _response_contract_failure(
                exc, stage="ai_local_evidence_finding", artifact="Evidence/Finding Draft"
            )
            if analyses:
                message = (
                    f"{message} {len(analyses)} of {len(batches)} Condition batch(es) "
                    "completed successfully and were retained, but the formal assessment "
                    "was not replaced by a technically incomplete result."
                )
                trace_message = (
                    f"{trace_message[:-1]}; completed={len(analyses)}/{len(batches)}; "
                    f"failed_condition={active_condition_ref})."
                )
            result = fail(
                state,
                "invalid_model_response",
                message,
                trace_message,
                exc.trace,
            )
            if analyses:
                result["local_analysis"] = _merge_local_analyses(bundle, analyses)
                result["local_evidence_invocations"] = invocations
                result["local_completed_condition_refs"] = completed_condition_refs
            return result
        except AIModelError as exc:
            return fail(
                state,
                "model_unavailable",
                "The model provider was unavailable during local Evidence/Finding analysis.",
                "ai_local_evidence_finding: failed - model unavailable.",
                exc.trace,
            )
        except (ValueError, EvidenceRuleValidationError, CandidateGraphValidationError):
            return fail(
                state,
                "evidence_validation_failure",
                "The local Evidence/Finding draft could not be admitted by deterministic Rule validation.",
                "ai_local_evidence_finding: failed - local Rule admission rejected the draft.",
            )

        try:
            merged = _merge_local_analyses(bundle, analyses)
        except ValueError as exc:
            return fail(
                state,
                "evidence_validation_failure",
                "Rule could not merge the bounded local Evidence/Finding batches.",
                "ai_local_evidence_finding: failed - bounded local batch merge rejected "
                f"({type(exc).__name__}).",
            )
        return {
            "local_analysis": merged,
            "local_evidence_invocations": invocations,
            "local_completed_condition_refs": completed_condition_refs,
            "workflow_trace": _trace(
                state,
                "ai_local_evidence_finding: completed - "
                f"{len(batches)} single-Condition batch(es), {len(merged.evidence_candidates)} Evidence candidate(s), "
                f"{len(merged.finding_candidates)} Finding candidate(s), "
                f"parallelism={min(3, len(batches))}, "
                f"request_ids={','.join(str(item.trace.request_id or 'none') for item in invocations)}.",
            ),
        }

    def rule_local_evidence_findings(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        try:
            analysis = state["local_analysis"]
            validation = evidence_rules.validate(state["material_bundle"], analysis)
            adjudication = candidate_rules.validate(analysis, validation)
            projection = domain.project(
                state["material_bundle"], analysis, validation, adjudication
            )
        except (
            EvidenceRuleValidationError,
            CandidateGraphValidationError,
            DomainProjectionError,
            ValueError,
        ):
            return fail(
                state,
                "evidence_validation_failure",
                "Rule could not validate the locally scoped Evidence/Finding candidates.",
                "rule_local_evidence_finding: failed - candidate provenance or relationship rejected.",
            )
        return {
            "evidence_validation": validation,
            "candidate_adjudication": adjudication,
            "projection": projection,
            "workflow_trace": _trace(
                state,
                "rule_local_evidence_finding: success - source provenance, candidate references, and stable identities validated.",
            ),
        }

    def research_materials(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        if research_loop is None:
            return {
                "workflow_trace": _trace(
                    state,
                    "research_materials: skipped - no research planning boundary configured.",
                )
            }
        initial_bundle = state["material_bundle"]
        try:
            result = research_loop.run(
                initial_bundle,
                local_environment_authorized=state["request"].environment_authorized,
            )
        except AIModelConfigurationError as exc:
            message, trace_message = _configuration_failure(exc)
            return fail(
                state,
                "configuration_required",
                message,
                f"ai_research_planning: {trace_message}",
                exc.trace,
            )
        except AIModelResponseError as exc:
            message, trace_message = _response_contract_failure(
                exc, stage="ai_research_planning", artifact="Research Plan"
            )
            return fail(
                state,
                "invalid_model_response",
                message,
                trace_message,
                exc.trace,
            )
        except AIModelError as exc:
            return fail(
                state,
                "model_unavailable",
                "The model provider was unavailable during Research Planning.",
                "ai_research_planning: failed - model unavailable.",
                exc.trace,
            )

        source_delta = len(result.final_bundle.sources) - len(initial_bundle.sources)
        handoff = result.handoff
        handoff_state = handoff.state if handoff is not None else "analysis_ready"
        handoff_reason = handoff.reason if handoff is not None else result.stop_reason
        trace_message = (
            "research_materials: completed - "
            f"{len(result.rounds)} round(s), {result.tool_requests_used} tool request(s), "
            f"{source_delta} new bounded source(s), stop={result.stop_reason}, "
            f"handoff={handoff_state}, gaps={_research_gap_refs(result)}."
        )
        # A workflow handoff is a technical/input state, never business Unknown.
        # Do not continue into Evidence/Rule with a result that explicitly says it
        # needs a human decision, authorization, or a deterministic tool retry.
        handoff_failures: dict[str, tuple[AnalysisState, str]] = {
            "confirmation_required": (
                "human_confirmation_required",
                "Human confirmation is required before the requested material scope can be analyzed.",
            ),
            "authorization_required": (
                "authorization_required",
                "Explicit authorization is required before the requested local material can be read.",
            ),
            "acquisition_failure": (
                "tool_failure",
                "A deterministic material acquisition tool failed; no business Unknown was fabricated.",
            ),
        }
        if handoff_state in handoff_failures:
            failure_state, message = handoff_failures[handoff_state]
            failure = fail(
                state,
                failure_state,
                message,
                f"{trace_message} technical_state={failure_state}; reason={handoff_reason}.",
            )
            return {
                **failure,
                "initial_material_bundle": initial_bundle,
                "material_bundle": result.final_bundle,
                "research_loop": result,
                "material_partial": state.get("material_partial", False) or source_delta > 0,
            }
        # Exhausting safe acquisition options ends the search loop, not the
        # Assessment.  The already collected bounded sources remain analyzable;
        # unresolved Gaps are business inputs for Evidence/Rule and may become
        # concrete Unknown Findings.  Only confirmation, authorization, or a
        # total acquisition failure above blocks analysis.
        if handoff_state == "stopped" and result.stop_reason in {
            "no_reliable_next_source",
            "no_new_material",
            "repeated_information_gaps",
        }:
            trace_message = (
                f"{trace_message} acquisition_stopped={result.stop_reason}; "
                "continuing_with_collected_material=true."
            )
        return {
            "initial_material_bundle": initial_bundle,
            "material_bundle": result.final_bundle,
            "research_loop": result,
            "material_partial": (
                state.get("material_partial", False) or _research_loop_has_tool_failures(result)
            ),
            "workflow_trace": _trace(
                state,
                (trace_message),
            ),
        }

    def ensure_phased_boundary(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        if use_local_evidence_finding:
            return {
                "workflow_trace": _trace(
                    state,
                    "ensure_phased_boundary: success - Context/Gap, Tool Acquisition, and local Evidence/Finding are configured.",
                )
            }
        return fail(
            state,
            "configuration_required",
            "The configured model does not implement the required phased AI boundary; legacy analysis is disabled.",
            "ensure_phased_boundary: failed - legacy Evidence/Conflict fallback is disabled.",
        )

    def rule_readiness(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        repository = state.get("repository_materials") or state.get("linked_repository_materials")
        resource_signal = (
            assessment_service.resource_signal_service.create(
                repository.readme,
                state.get("environment_facts"),
                repository_url=repository.repository_url,
            )
            if repository is not None
            else None
        )
        result = readiness_rules.adjudicate(
            state["projection"],
            resource_signal=resource_signal,
        )
        if not result.decision_available:
            failure_state: AnalysisState = "evidence_validation_failure"
            return {
                "readiness": result,
                "failure_state": failure_state,
                "failure_message": result.unavailable_reason or "Gate is not available.",
                "workflow_trace": _trace(
                    state,
                    f"rule_readiness: unavailable - {failure_state}.",
                ),
            }
        return {
            "readiness": result,
            "workflow_trace": _trace(
                state, f"rule_readiness: success - Overall Gate {result.overall_gate}."
            ),
        }

    def build_success(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        rule = state["readiness"]
        projection = state["projection"]
        partial = state.get("material_partial", False)
        assessment = ReadinessAssessment(
            assessment_id=uuid4(),
            status="partial" if partial else "completed",
            data_mode=_data_mode(state["resolved_target"]),
            target_type=state["request"].target_type,
            target_entry=state["request"].target_entry,
            resolved_target=state["resolved_target"],
            generated_at=datetime.now(UTC),
            dimensions=rule.dimensions,
            analysis_state="partial_result" if partial else None,
            gate_available=True,
            overall_gate=rule.overall_gate,
            trigger_refs=rule.trigger_refs,
            main_risk=rule.main_risk or "No material readiness risk was identified.",
            first_next_action=rule.first_next_action,
            conflicts=[item.conflict for item in projection.conflicts],
            evaluation_signal=rule.evaluation_signal,
            resource_signal=rule.resource_signal,
            trace_summary=[*state.get("workflow_trace", []), *rule.rule_trace],
        )
        return {"assessment": assessment}

    def build_failure(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        analysis_state = state["failure_state"]
        assessment = _partial_assessment(
            state["request"],
            state["resolved_target"],
            analysis_state,
            state["failure_message"],
            state.get("workflow_trace", []),
        )
        return {"assessment": assessment}

    def validate_output(state: ModelReadinessGraphState) -> ModelReadinessGraphState:
        assessment = ReadinessAssessment.model_validate(state["assessment"])
        assessment = assessment.model_copy(
            update={
                "trace_summary": [
                    *assessment.trace_summary,
                    "validate_output: success - stable Assessment contract validated.",
                ],
                "audit_trail": build_assessment_audit(
                    {**state, "assessment": assessment},
                    existing=assessment.audit_trail,
                ),
            }
        )
        return {"assessment": ReadinessAssessment.model_validate(assessment)}

    def route_failure(state: ModelReadinessGraphState) -> str:
        return "build_failure" if "failure_state" in state else "continue"

    graph = StateGraph(ModelReadinessGraphState)
    graph.add_node("resolve_target", resolve_target)
    graph.add_node("acquire_environment", acquire_environment)
    graph.add_node("collect_materials", collect_materials)
    graph.add_node("build_material_bundle", build_bundle)
    graph.add_node("research_materials", research_materials)
    graph.add_node("ensure_phased_boundary", ensure_phased_boundary)
    graph.add_node("ai_local_evidence_finding", ai_local_evidence_findings)
    graph.add_node("rule_local_evidence_finding", rule_local_evidence_findings)
    graph.add_node("rule_readiness", rule_readiness)
    graph.add_node("build_success", build_success)
    graph.add_node("build_failure", build_failure)
    graph.add_node("validate_output", validate_output)

    graph.add_edge(START, "resolve_target")
    graph.add_edge("resolve_target", "acquire_environment")
    graph.add_edge("acquire_environment", "collect_materials")
    for node, next_node in (
        ("collect_materials", "build_material_bundle"),
        ("build_material_bundle", "research_materials"),
    ):
        graph.add_conditional_edges(
            node,
            route_failure,
            {"build_failure": "build_failure", "continue": next_node},
        )
    graph.add_conditional_edges(
        "research_materials",
        route_failure,
        {"build_failure": "build_failure", "continue": "ensure_phased_boundary"},
    )
    graph.add_conditional_edges(
        "ensure_phased_boundary",
        route_failure,
        {"build_failure": "build_failure", "continue": "ai_local_evidence_finding"},
    )
    graph.add_conditional_edges(
        "ai_local_evidence_finding",
        route_failure,
        {"build_failure": "build_failure", "continue": "rule_local_evidence_finding"},
    )
    graph.add_conditional_edges(
        "rule_local_evidence_finding",
        route_failure,
        {"build_failure": "build_failure", "continue": "rule_readiness"},
    )
    graph.add_conditional_edges(
        "rule_readiness",
        route_failure,
        {"build_failure": "build_failure", "continue": "build_success"},
    )
    graph.add_edge("build_success", "validate_output")
    graph.add_edge("build_failure", "validate_output")
    graph.add_edge("validate_output", END)
    return graph.compile()


def invoke_model_readiness_graph(
    graph: CompiledStateGraph,
    request: AssessmentRequest,
) -> ReadinessAssessment:
    result = graph.invoke({"request": request, "workflow_trace": []})
    return ReadinessAssessment.model_validate(result["assessment"])


def _partial_assessment(
    request: AssessmentRequest,
    target: ResolvedTarget,
    analysis_state: AnalysisState,
    message: str,
    trace: list[str],
) -> ReadinessAssessment:
    dimensions = [
        ReadinessDimension(
            dimension_id=dimension_id,
            name=name,
            analysis_state=analysis_state,
            summary=message,
            gate_impact="Overall Gate is not available until this analysis state is resolved.",
        )
        for dimension_id, name in (
            ("RD-01", "Data & Access Readiness"),
            ("RD-02", "Environment & Dependency Readiness"),
            ("RD-03", "Weights & Configuration Readiness"),
        )
    ]
    return ReadinessAssessment(
        assessment_id=uuid4(),
        status="partial",
        data_mode=_data_mode(target),
        target_type=request.target_type,
        target_entry=request.target_entry,
        resolved_target=target,
        generated_at=datetime.now(UTC),
        dimensions=dimensions,
        analysis_state=analysis_state,
        gate_available=False,
        overall_gate=None,
        trigger_refs=[],
        main_risk=message,
        first_next_action=NextAction(
            action_id=f"action-{analysis_state.replace('_', '-')}",
            title="Resolve the analysis state and retry",
            description=message,
            action_type="Minimum Validation",
            reason_refs=[analysis_state],
        ),
        trace_summary=trace,
    )


def _initial_condition_contexts() -> dict[str, list[EvidenceFindingConditionContext]]:
    """Rule-owned core conditions for the first local Evidence/Finding pass."""
    return {
        "RD-01": [
            EvidenceFindingConditionContext(condition_ref=criterion, primary_dimension="RD-01")
            for criterion in ("rd01.dataset_identity", "rd01.dataset_access", "rd01.input_contract")
        ],
        "RD-02": [
            EvidenceFindingConditionContext(condition_ref=criterion, primary_dimension="RD-02")
            for criterion in (
                "rd02.software_requirements",
                "rd02.dependency_requirements",
                "rd02.environment_compatibility",
            )
        ],
        "RD-03": [
            EvidenceFindingConditionContext(condition_ref=criterion, primary_dimension="RD-03")
            for criterion in (
                "rd03.checkpoint_access",
                "rd03.configuration_mapping",
                "rd03.execution_contract",
            )
        ],
    }


def _latest_phase_context(research_loop: ResearchLoopResult | None):
    if research_loop is None:
        return None
    return next(
        (
            item.context_gap
            for item in reversed(research_loop.rounds)
            if item.context_gap is not None
        ),
        None,
    )


def _merge_local_analyses(
    bundle: MaterialBundle,
    analyses: list[AIAnalysisResult],
) -> AIAnalysisResult:
    """Combine disjoint, bounded condition batches before one global Rule pass."""
    evidence = {
        item.candidate_id: item for analysis in analyses for item in analysis.evidence_candidates
    }
    conflicts = {
        item.candidate_id: item for analysis in analyses for item in analysis.conflict_candidates
    }
    findings = {
        item.candidate_id: item for analysis in analyses for item in analysis.finding_candidates
    }
    questions = {
        item.question_id: item for analysis in analyses for item in analysis.unresolved_questions
    }
    return AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="Merged first-pass local Evidence/Finding drafts.",
        examined_source_ids=[source.source_id for source in bundle.sources],
        evidence_candidates=list(evidence.values()),
        conflict_candidates=list(conflicts.values()),
        finding_candidates=list(findings.values()),
        unresolved_questions=list(questions.values()),
    )


def _model_trace(stage: str, trace) -> str:
    return (
        f"{stage}: success - request_id={trace.request_id or 'unavailable'}, "
        f"tokens={trace.total_tokens if trace.total_tokens is not None else 'unavailable'}, "
        f"duration_ms={trace.duration_ms}."
    )


def _data_mode(target: ResolvedTarget) -> str:
    return "live_repository" if target.target_type == "repository" else "live_metadata"
