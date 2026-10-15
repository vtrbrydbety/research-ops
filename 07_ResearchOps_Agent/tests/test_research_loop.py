"""Stop-condition tests for the bounded research planning loop."""

from collections import deque
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from researchops.core.config import Settings
from researchops.schemas import (
    AcquisitionLoopControl,
    AcquisitionRequestDraft,
    AIContextGapInvocation,
    AIContextGapResult,
    AIModelTrace,
    AIToolAcquisitionInvocation,
    AIToolAcquisitionResult,
    ContextGapControl,
    ContextGapFocus,
    MaterialBundle,
    MaterialSource,
    PhaseInformationGap,
    ResearchToolExecutionResult,
    ResolvedTarget,
    ToolRequest,
    ToolRequestExecutionResult,
)
from researchops.services.phased_research_loop import PhasedResearchLoopService


def _bundle() -> MaterialBundle:
    content = "Initial material."
    return MaterialBundle(
        bundle_id=uuid4(),
        target=ResolvedTarget(
            target_type="repository",
            source_entry="https://github.com/example/project",
            display_name="example/project",
            canonical_id="github:example/project",
            canonical_url="https://github.com/example/project",
            resolution_method="direct_url",
        ),
        assembled_at=datetime.now(UTC),
        sources=[
            MaterialSource(
                source_id="src-initial",
                material_type="README",
                title="README",
                source_path="README.md",
                source_url="https://github.com/example/project/blob/main/README.md",
                content=content,
                content_sha256=sha256(content.encode()).hexdigest(),
                access_scope="public",
            )
        ],
    )


class _Planner:
    def __init__(self, templates: list[dict[str, object]]) -> None:
        self.templates = deque(templates)
        self.bundle_ids = []

    def analyze_context_gaps(self, bundle):
        self.bundle_ids.append(bundle.bundle_id)
        self.template = self.templates.popleft()
        state = self.template["state"]
        label = str(self.template.get("gap_label", "missing checkpoint"))
        self.gaps = (
            [
                PhaseInformationGap(
                    gap_id=f"gap-{label.replace(' ', '-')}-{index}",
                    question=f"{label} {index}",
                    scope_ref="RD-03",
                    needed_source_type="Material",
                    reason="Checkpoint access is unverified.",
                )
                for index in range(1, max(int(self.template.get("request_count", 0)), 1) + 1)
            ]
            if state != "ready_for_analysis"
            else []
        )
        return AIContextGapInvocation(
            result=AIContextGapResult(
                analysis_mode="initial",
                focus=ContextGapFocus(scope_refs=["RD-03"]),
                information_gaps=self.gaps,
                control=ContextGapControl(
                    target_confirmation_needed=state == "needs_user_input",
                    more_information_needed=state != "ready_for_analysis",
                    stop_reason="target_confirmation_required"
                    if state == "needs_user_input"
                    else None,
                ),
            ),
            trace=_PhasedModel._trace(),
        )

    def plan_tool_acquisition(self, context):
        tool = str(self.template.get("tool_name", "search_github"))
        state = (
            "authorization_required"
            if tool == "inspect_local_environment" and not context.local_environment_authorized
            else "tool_request"
        )
        requests = (
            [
                AcquisitionRequestDraft(
                    gap_ref=gap.gap_id,
                    requested_fact="Find bounded repository material.",
                    source_type="User Context"
                    if tool == "inspect_local_environment"
                    else "Material",
                    tool_ref=tool,
                    read_scope="Current authorized environment"
                    if tool == "inspect_local_environment"
                    else "Target repository releases.",
                    query=f"project candidate {index}" if tool == "search_github" else None,
                    authorization_required=tool == "inspect_local_environment",
                    expected_evidence="A source-bound result.",
                )
                for index, gap in enumerate(self.gaps)
            ]
            if state == "tool_request"
            else []
        )
        return AIToolAcquisitionInvocation(
            result=AIToolAcquisitionResult(
                acquisition_state=state,
                requests=requests,
                loop_control=AcquisitionLoopControl(
                    current_round=context.current_round,
                    configured_max_rounds=context.configured_max_rounds,
                    continue_after_result=state == "tool_request",
                    stop_reason="authorization_required"
                    if state == "authorization_required"
                    else None,
                ),
            ),
            trace=_PhasedModel._trace(),
        )


class _Executor:
    def __init__(self, *, add_material: bool = True, status: str = "succeeded") -> None:
        self.add_material = add_material
        self.status = status
        self.calls = 0

    def execute(
        self,
        requests: list[ToolRequest],
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchToolExecutionResult:
        self.calls += 1
        new_sources = []
        if self.add_material and self.status == "succeeded":
            for index, _request in enumerate(requests, start=1):
                content = f"Tool material from call {self.calls}, request {index}."
                new_sources.append(
                    MaterialSource(
                        source_id=f"src-tool-{self.calls}-{index}",
                        material_type="Repository",
                        title="Tool result",
                        source_path=f".researchops/tool-{self.calls}-{index}.json",
                        content=content,
                        content_sha256=sha256(content.encode()).hexdigest(),
                        access_scope="public",
                    )
                )
        output_bundle = MaterialBundle(
            bundle_id=uuid4() if new_sources else bundle.bundle_id,
            target=bundle.target,
            assembled_at=datetime.now(UTC),
            sources=[*bundle.sources, *new_sources],
        )
        now = datetime.now(UTC)
        results = [
            ToolRequestExecutionResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=self.status,
                source_ids=([new_sources[index].source_id] if new_sources else []),
                detail="Synthetic deterministic execution.",
                started_at=now,
                completed_at=now,
            )
            for index, request in enumerate(requests)
        ]
        return ResearchToolExecutionResult(
            plan_id=uuid4(),
            input_bundle_id=bundle.bundle_id,
            output_bundle=output_bundle,
            input_source_ids=[source.source_id for source in bundle.sources],
            new_source_ids=[source.source_id for source in new_sources],
            request_results=results,
        )


class _PhasedModel:
    def __init__(self, *, acquisition_state: str = "tool_request") -> None:
        self.acquisition_state = acquisition_state
        self.acquisition_inputs = []

    @staticmethod
    def _trace() -> AIModelTrace:
        now = datetime.now(UTC)
        return AIModelTrace(
            trace_id=uuid4(),
            model="fake-phased-model",
            started_at=now,
            completed_at=now,
            duration_ms=0,
            attempts=1,
            status="success",
        )

    def analyze_context_gaps(self, bundle: MaterialBundle) -> AIContextGapInvocation:
        return AIContextGapInvocation(
            result=AIContextGapResult(
                analysis_mode="initial",
                focus=ContextGapFocus(scope_refs=["RD-03"]),
                information_gaps=[
                    PhaseInformationGap(
                        gap_id="gap-checkpoint",
                        question="Locate the official checkpoint.",
                        scope_ref="RD-03",
                        needed_source_type="Material",
                        reason="Checkpoint access is not established.",
                    )
                ],
                control=ContextGapControl(
                    target_confirmation_needed=False, more_information_needed=True
                ),
            ),
            trace=self._trace(),
        )

    def plan_tool_acquisition(self, _context) -> AIToolAcquisitionInvocation:
        self.acquisition_inputs.append(_context)
        state = self.acquisition_state
        request = (
            AcquisitionRequestDraft(
                gap_ref="gap-checkpoint",
                requested_fact="Official checkpoint location.",
                source_type="Material",
                tool_ref="search_github",
                read_scope="Target repository releases.",
                query="example checkpoint",
                expected_evidence="Official release or artifact reference.",
            )
            if state == "tool_request"
            else None
        )
        stop_reason = (
            None
            if state == "tool_request"
            else (
                "confirmation_required"
                if state == "human_confirmation"
                else "no_reliable_next_source"
            )
        )
        return AIToolAcquisitionInvocation(
            result=AIToolAcquisitionResult(
                acquisition_state=state,
                requests=[request] if request is not None else [],
                loop_control=AcquisitionLoopControl(
                    current_round=0,
                    configured_max_rounds=5,
                    continue_after_result=state == "tool_request",
                    stop_reason=stop_reason,
                ),
            ),
            trace=self._trace(),
        )


class _MixedPhasedModel(_PhasedModel):
    def plan_tool_acquisition(self, context) -> AIToolAcquisitionInvocation:
        invocation = super().plan_tool_acquisition(context)
        second = invocation.result.requests[0].model_copy(
            update={"tool_ref": "search_web", "query": "secondary source"}
        )
        return invocation.model_copy(
            update={
                "result": invocation.result.model_copy(
                    update={"requests": [*invocation.result.requests, second]}
                )
            }
        )


class _MixedExecutor(_Executor):
    def execute(
        self,
        requests: list[ToolRequest],
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchToolExecutionResult:
        result = super().execute(
            requests,
            bundle,
            local_environment_authorized=local_environment_authorized,
        )
        failed = result.request_results[1].model_copy(
            update={"status": "failed", "source_ids": [], "detail": "Synthetic failure."}
        )
        successful_source_id = result.request_results[0].source_ids[0]
        successful_source = next(
            source
            for source in result.output_bundle.sources
            if source.source_id == successful_source_id
        )
        output_bundle = result.output_bundle.model_copy(
            update={"sources": [*bundle.sources, successful_source]}
        )
        return result.model_copy(
            update={
                "output_bundle": output_bundle,
                "new_source_ids": [successful_source_id],
                "request_results": [result.request_results[0], failed],
            }
        )


class _ChangingGapPhasedModel(_PhasedModel):
    def __init__(self) -> None:
        super().__init__()
        self.context_round = 0

    def analyze_context_gaps(self, bundle: MaterialBundle) -> AIContextGapInvocation:
        self.context_round += 1
        return AIContextGapInvocation(
            result=AIContextGapResult(
                analysis_mode="initial",
                focus=ContextGapFocus(scope_refs=["RD-03"]),
                information_gaps=[
                    PhaseInformationGap(
                        gap_id=f"gap-checkpoint-{self.context_round}",
                        question="Locate another official checkpoint fact.",
                        scope_ref="RD-03",
                        needed_source_type="Material",
                        reason="The next bounded source is still needed.",
                    )
                ],
                control=ContextGapControl(
                    target_confirmation_needed=False,
                    more_information_needed=True,
                ),
            ),
            trace=self._trace(),
        )

    def plan_tool_acquisition(self, context) -> AIToolAcquisitionInvocation:
        self.acquisition_inputs.append(context)
        gap_id = context.context_gap.information_gaps[0].gap_id
        return AIToolAcquisitionInvocation(
            result=AIToolAcquisitionResult(
                acquisition_state="tool_request",
                requests=[
                    AcquisitionRequestDraft(
                        gap_ref=gap_id,
                        requested_fact="Official checkpoint location.",
                        source_type="Material",
                        tool_ref="search_github",
                        read_scope="Target repository releases.",
                        query="example checkpoint",
                        expected_evidence="Official release or artifact reference.",
                    )
                ],
                loop_control=AcquisitionLoopControl(
                    current_round=context.current_round,
                    configured_max_rounds=context.configured_max_rounds,
                    continue_after_result=True,
                ),
            ),
            trace=self._trace(),
        )


class _SuccessThenTimeoutExecutor(_Executor):
    def execute(
        self,
        requests: list[ToolRequest],
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchToolExecutionResult:
        if self.calls == 0:
            return super().execute(
                requests,
                bundle,
                local_environment_authorized=local_environment_authorized,
            )
        self.calls += 1
        now = datetime.now(UTC)
        return ResearchToolExecutionResult(
            plan_id=uuid4(),
            input_bundle_id=bundle.bundle_id,
            output_bundle=bundle,
            input_source_ids=[source.source_id for source in bundle.sources],
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
                for request in requests
            ],
        )


def test_phased_loop_records_context_gap_and_tool_acquisition_separately() -> None:
    result = PhasedResearchLoopService(_PhasedModel(), _Executor()).run(_bundle())

    assert result.rounds[0].context_gap is not None
    assert result.rounds[0].tool_acquisition is not None
    assert result.rounds[0].execution is not None
    assert result.rounds[0].planning is None
    assert result.rounds[0].execution.request_results[0].request_id.startswith("acq-1-")
    assert result.handoff is not None


def test_phased_loop_supplies_the_remaining_request_budget_to_tool_acquisition() -> None:
    model = _PhasedModel()

    PhasedResearchLoopService(
        model,
        _Executor(),
        max_rounds=2,
        max_tool_requests=1,
    ).run(_bundle())

    assert [item.remaining_tool_requests for item in model.acquisition_inputs] == [1, 0]


def test_phased_loop_exposes_confirmation_without_executing_a_tool() -> None:
    executor = _Executor()
    result = PhasedResearchLoopService(
        _PhasedModel(acquisition_state="human_confirmation"), executor
    ).run(_bundle())

    assert executor.calls == 0
    assert result.handoff is not None
    assert result.handoff.state == "confirmation_required"


def test_phased_loop_preserves_partial_material_when_another_tool_fails() -> None:
    result = PhasedResearchLoopService(_MixedPhasedModel(), _MixedExecutor()).run(_bundle())

    assert result.stop_reason == "repeated_information_gaps"
    assert result.handoff is not None
    assert result.handoff.state == "stopped"
    assert len(result.final_bundle.sources) == 2
    assert {item.status for item in result.rounds[0].execution.request_results} == {
        "succeeded",
        "failed",
    }


def test_phased_loop_hands_prior_material_to_analysis_after_later_timeout() -> None:
    result = PhasedResearchLoopService(
        _ChangingGapPhasedModel(),
        _SuccessThenTimeoutExecutor(),
        max_rounds=3,
    ).run(_bundle())

    assert result.stop_reason == "partial_material_acquisition"
    assert result.handoff is not None
    assert result.handoff.state == "analysis_ready"
    assert len(result.final_bundle.sources) == 2
    assert result.rounds[-1].execution is not None
    assert result.rounds[-1].execution.request_results[0].failure_code == "transport_timeout"


def test_phased_loop_keeps_total_first_read_failure_terminal() -> None:
    result = PhasedResearchLoopService(
        _PhasedModel(),
        _Executor(add_material=False, status="failed"),
        max_rounds=1,
    ).run(_bundle())

    assert result.stop_reason == "tool_acquisition_failed"
    assert result.handoff is not None
    assert result.handoff.state == "acquisition_failure"


def test_default_settings_allow_five_rounds_and_freeze_twelve_request_limit() -> None:
    settings = Settings()
    assert settings.research_max_rounds == 5
    assert settings.research_max_tool_requests == 12

    with pytest.raises(ValueError):
        Settings(research_max_rounds=6)


def test_ready_and_human_input_states_stop_without_running_tools() -> None:
    bundle = _bundle()
    ready_executor = _Executor()
    ready = PhasedResearchLoopService(
        _Planner([{"state": "ready_for_analysis"}]), ready_executor
    ).run(bundle)
    human_executor = _Executor()
    human = PhasedResearchLoopService(
        _Planner([{"state": "needs_user_input", "gap_label": "target ambiguity"}]),
        human_executor,
    ).run(bundle)

    assert ready.stop_reason == "ready_for_analysis"
    assert human.stop_reason == "needs_user_input"
    assert ready_executor.calls == human_executor.calls == 0


def test_default_loop_stops_after_five_productive_rounds() -> None:
    planner = _Planner(
        [
            {"state": "needs_tool_calls", "request_count": 1, "gap_label": f"gap round {i}"}
            for i in range(1, 6)
        ]
    )
    executor = _Executor()

    result = PhasedResearchLoopService(planner, executor).run(_bundle())

    assert result.stop_reason == "round_limit_reached"
    assert len(result.rounds) == 5
    assert executor.calls == 5
    assert result.tool_requests_used == 5
    assert all(round_.tool_acquisition is not None for round_ in result.rounds)
    assert all(
        round_.tool_acquisition.result.acquisition_state == "tool_request"
        for round_ in result.rounds
    )
    assert all(round_.execution is not None for round_ in result.rounds)
    assert all(
        not hasattr(round_.tool_acquisition.result, "request_results") for round_ in result.rounds
    )
    assert result.handoff is not None
    assert result.handoff.state == "stopped"


def test_unapproved_environment_read_stops_before_tools_and_offers_snapshot_or_manual() -> None:
    executor = _Executor()
    result = PhasedResearchLoopService(
        _Planner(
            [
                {
                    "state": "needs_tool_calls",
                    "request_count": 1,
                    "tool_name": "inspect_local_environment",
                }
            ]
        ),
        executor,
    ).run(_bundle())

    assert result.stop_reason == "authorization_required"
    assert executor.calls == 0
    assert result.handoff is not None
    assert result.handoff.state == "authorization_required"
    assert result.handoff.alternative_inputs == ["snapshot", "manual"]


def test_failed_environment_acquisition_offers_retry_snapshot_and_manual_without_status() -> None:
    executor = _Executor(add_material=False, status="failed")
    result = PhasedResearchLoopService(
        _Planner(
            [
                {
                    "state": "needs_tool_calls",
                    "request_count": 1,
                    "tool_name": "inspect_local_environment",
                }
            ]
        ),
        executor,
    ).run(_bundle(), local_environment_authorized=True)

    assert result.stop_reason == "tool_acquisition_failed"
    assert result.handoff is not None
    assert result.handoff.state == "acquisition_failure"
    assert result.handoff.retry_allowed is True
    assert result.handoff.alternative_inputs == ["snapshot", "manual"]


def test_no_reliable_tool_result_stops_without_inventing_business_outcome() -> None:
    result = PhasedResearchLoopService(
        _Planner([{"state": "needs_tool_calls", "request_count": 1}]),
        _Executor(add_material=False, status="denied"),
    ).run(_bundle())

    assert result.stop_reason == "no_reliable_next_source"
    assert result.handoff is not None
    assert result.handoff.state == "stopped"


def test_ready_plan_becomes_explicit_stop_acquisition_handoff() -> None:
    result = PhasedResearchLoopService(
        _Planner([{"state": "ready_for_analysis"}]), _Executor()
    ).run(_bundle())

    context = result.rounds[0].context_gap
    assert context is not None
    assert context.result.control.more_information_needed is False
    assert context.result.information_gaps == []
    assert result.rounds[0].tool_acquisition is None


def test_no_new_material_stops_immediately() -> None:
    planner = _Planner(
        [
            {"state": "needs_tool_calls", "request_count": 1, "gap_label": "same gap"},
            {"state": "ready_for_analysis"},
        ]
    )
    executor = _Executor(add_material=False)

    result = PhasedResearchLoopService(planner, executor).run(_bundle())

    assert result.stop_reason == "no_new_material"
    assert len(result.rounds) == 1
    assert len(planner.bundle_ids) == 1


def test_same_semantic_gaps_in_two_consecutive_rounds_stop_before_duplicate_tools() -> None:
    planner = _Planner(
        [
            {"state": "needs_tool_calls", "request_count": 1, "gap_label": "same gap"},
            {"state": "needs_tool_calls", "request_count": 1, "gap_label": "same gap"},
        ]
    )
    executor = _Executor()

    result = PhasedResearchLoopService(planner, executor).run(_bundle())

    assert result.stop_reason == "repeated_information_gaps"
    assert len(result.rounds) == 2
    assert result.rounds[-1].execution is None
    assert executor.calls == 1


def test_global_twelve_request_budget_is_never_partially_overrun() -> None:
    planner = _Planner(
        [
            {"state": "needs_tool_calls", "request_count": 8, "gap_label": "first"},
            {"state": "needs_tool_calls", "request_count": 5, "gap_label": "second"},
        ]
    )
    executor = _Executor()

    result = PhasedResearchLoopService(planner, executor).run(_bundle())

    assert result.stop_reason == "tool_request_limit_reached"
    assert result.tool_requests_used == 8
    assert executor.calls == 1
    assert result.rounds[-1].execution is None
