"""Context & Gap → Tool Acquisition loop for the production Readiness path.

The model owns only the two phase handoffs. The deterministic executor consumes
the Tool Acquisition request list directly; no legacy Research Planning object
is constructed on the production path.
"""

from __future__ import annotations

from uuid import uuid4

from researchops.core.config import Settings, get_settings
from researchops.schemas import (
    AIToolAcquisitionInvocation,
    MaterialBundle,
    ResearchLoopHandoff,
    ResearchLoopResult,
    ResearchLoopRound,
    ResearchLoopStopReason,
    ToolAcquisitionInput,
    ToolRequest,
)
from researchops.services.analysis_boundaries import ResearchToolExecutor


class PhasedResearchLoopService:
    """Run only the explicit Context/Gap and Tool Acquisition phases.

    It preserves the existing executor and ``ResearchLoopResult`` audit shape
    while recording the two provider invocations separately on every round.
    """

    def __init__(
        self,
        model: object,
        tool_executor: ResearchToolExecutor,
        settings: Settings | None = None,
        *,
        max_rounds: int | None = None,
        max_tool_requests: int | None = None,
    ) -> None:
        config = settings or get_settings()
        self.model = model
        self.tool_executor = tool_executor
        self.max_rounds = config.research_max_rounds if max_rounds is None else max_rounds
        self.max_tool_requests = (
            config.research_max_tool_requests if max_tool_requests is None else max_tool_requests
        )
        if not 1 <= self.max_rounds <= 5:
            raise ValueError("研究循环最多只能执行 5 轮")
        if not 1 <= self.max_tool_requests <= 12:
            raise ValueError("研究循环工具请求总量必须在 1 到 12 之间")

    def run(
        self,
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchLoopResult:
        current_bundle = bundle
        rounds: list[ResearchLoopRound] = []
        used = 0
        previous_fingerprint: tuple[str, ...] | None = None
        stop_reason: ResearchLoopStopReason = "round_limit_reached"
        handoff: ResearchLoopHandoff | None = None

        for number in range(1, self.max_rounds + 1):
            from researchops.core.access_context import check_operation

            check_operation()
            context_invocation = self.model.analyze_context_gaps(current_bundle)
            context = context_invocation.result
            if context.control.target_confirmation_needed:
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                    )
                )
                stop_reason = "needs_user_input"
                handoff = ResearchLoopHandoff(
                    state="confirmation_required",
                    reason=stop_reason,
                    user_question="Confirm the intended target or material mapping before continuing.",
                )
                break

            if not context.control.more_information_needed:
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                    )
                )
                stop_reason = "ready_for_analysis"
                handoff = ResearchLoopHandoff(state="analysis_ready", reason=stop_reason)
                break

            acquisition_invocation = self.model.plan_tool_acquisition(
                ToolAcquisitionInput(
                    bundle=current_bundle,
                    context_gap=context,
                    available_tools=list(self._available_tools()),
                    local_environment_authorized=local_environment_authorized,
                    current_round=number - 1,
                    configured_max_rounds=self.max_rounds,
                    remaining_tool_requests=self.max_tool_requests - used,
                )
            )
            acquisition = acquisition_invocation.result
            requests = self._executor_requests(acquisition_invocation)

            if acquisition.acquisition_state == "human_confirmation":
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = "needs_user_input"
                handoff = ResearchLoopHandoff(
                    state="confirmation_required",
                    reason=stop_reason,
                    user_question="Provide the requested clarification before continuing.",
                )
                break
            if acquisition.acquisition_state == "authorization_required":
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = "authorization_required"
                handoff = ResearchLoopHandoff(
                    state="authorization_required",
                    reason=stop_reason,
                    alternative_inputs=["snapshot", "manual"],
                )
                break
            if acquisition.acquisition_state == "alternative_input":
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = "no_reliable_next_source"
                handoff = ResearchLoopHandoff(state="stopped", reason=stop_reason)
                break
            if acquisition.acquisition_state == "stop_acquisition":
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = self._stop_reason(acquisition.loop_control.stop_reason)
                handoff = ResearchLoopHandoff(state="stopped", reason=stop_reason)
                break

            fingerprint = tuple(sorted(gap.gap_id for gap in context.information_gaps))
            if fingerprint == previous_fingerprint:
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = "repeated_information_gaps"
                handoff = ResearchLoopHandoff(state="stopped", reason=stop_reason)
                break
            previous_fingerprint = fingerprint
            if used + len(requests) > self.max_tool_requests:
                rounds.append(
                    ResearchLoopRound(
                        round_number=number,
                        context_gap=context_invocation,
                        tool_acquisition=acquisition_invocation,
                    )
                )
                stop_reason = "tool_request_limit_reached"
                handoff = ResearchLoopHandoff(state="stopped", reason=stop_reason)
                break

            execution = self.tool_executor.execute(
                requests,
                current_bundle,
                local_environment_authorized=local_environment_authorized,
            )
            used += len(execution.request_results)
            rounds.append(
                ResearchLoopRound(
                    round_number=number,
                    context_gap=context_invocation,
                    tool_acquisition=acquisition_invocation,
                    execution=execution,
                )
            )
            current_bundle = execution.output_bundle
            statuses = {item.status for item in execution.request_results}
            # A mixed batch is partial material acquisition, not a total Tool
            # Failure. Continue with verified new sources; Context & Gap decides
            # whether the failed request still matters on the next round.
            if "failed" in statuses and not execution.new_source_ids:
                has_prior_material = any(
                    item.execution is not None and item.execution.new_source_ids
                    for item in rounds[:-1]
                )
                if has_prior_material:
                    # The failed read remains explicit in the Tool Result, but
                    # it must not discard useful material admitted in an earlier
                    # round. Hand the bounded partial bundle to Evidence/Rule.
                    stop_reason = "partial_material_acquisition"
                    handoff = ResearchLoopHandoff(
                        state="analysis_ready",
                        reason=stop_reason,
                    )
                else:
                    stop_reason = "tool_acquisition_failed"
                    handoff = ResearchLoopHandoff(
                        state="acquisition_failure",
                        reason=stop_reason,
                        retry_allowed=True,
                        alternative_inputs=(
                            ["snapshot", "manual"]
                            if any(
                                request.tool_name == "inspect_local_environment"
                                for request in requests
                            )
                            else []
                        ),
                    )
                break
            if "succeeded" not in statuses or not execution.new_source_ids:
                stop_reason = (
                    "no_new_material" if "succeeded" in statuses else "no_reliable_next_source"
                )
                handoff = ResearchLoopHandoff(state="stopped", reason=stop_reason)
                break
        else:
            handoff = ResearchLoopHandoff(state="stopped", reason="round_limit_reached")

        return ResearchLoopResult(
            run_id=uuid4(),
            initial_bundle_id=bundle.bundle_id,
            final_bundle=current_bundle,
            stop_reason=stop_reason,
            tool_requests_used=used,
            rounds=rounds,
            handoff=handoff,
        )

    def _available_tools(self) -> set[str]:
        return set(getattr(self.tool_executor, "allowed_tools", set()))

    @staticmethod
    def _stop_reason(value: str | None) -> ResearchLoopStopReason:
        return {
            "round_limit": "round_limit_reached",
            "request_budget_exhausted": "tool_request_limit_reached",
            "no_reliable_next_source": "no_reliable_next_source",
            "acquisition_failed": "tool_acquisition_failed",
        }.get(value or "", "no_reliable_next_source")

    def _executor_requests(
        self,
        acquisition_invocation: AIToolAcquisitionInvocation,
    ) -> list[ToolRequest]:
        return [
            ToolRequest(
                request_id=f"acq-{index + 1}-{request.gap_ref}",
                tool_name=request.tool_ref,
                gap_ids=[request.gap_ref],
                purpose=request.requested_fact,
                query=request.query,
                url=request.url,
                identifier=request.identifier,
                requires_user_authorization=request.authorization_required,
            )
            for index, request in enumerate(acquisition_invocation.result.requests)
            if request.tool_ref is not None
        ]
