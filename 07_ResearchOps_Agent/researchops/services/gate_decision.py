"""冻结 Gate 规则与 First Next Action 优先级的集中决策器。"""

from dataclasses import dataclass

from researchops.schemas import (
    EvaluationSignal,
    NextAction,
    OverallGate,
    ReadinessDimension,
    ResourceSignal,
)


@dataclass(frozen=True, slots=True)
class GateDecision:
    """可直接写入 ReadinessAssessment 的 Gate 决策。"""

    overall_gate: OverallGate
    main_risk: str
    first_next_action: NextAction
    trigger_refs: tuple[str, ...]


class GateDecisionService:
    """按 Blocker → Gate-critical Unknown → Warning → 最小验证聚合。"""

    def resolve(
        self,
        dimensions: list[ReadinessDimension],
        resource_signal: ResourceSignal | None,
        evaluation_signal: EvaluationSignal | None,
    ) -> GateDecision:
        """应用冻结规则，不使用平均分、投票或加权分。"""

        blocked_dimension = next(
            (dimension for dimension in dimensions if dimension.status == "Blocked"),
            None,
        )
        if blocked_dimension is not None:
            finding = next(
                (
                    finding
                    for finding in blocked_dimension.findings
                    if finding.gate_critical and finding.finding_type == "Fact"
                ),
                blocked_dimension.findings[0],
            )
            return GateDecision(
                overall_gate="PAUSE",
                main_risk=finding.title,
                first_next_action=NextAction(
                    action_id="action-resolve-dimension-blocker",
                    title=f"Resolve: {finding.title}",
                    description=finding.summary,
                    action_type="Resolve Blocker",
                    reason_refs=[blocked_dimension.dimension_id, finding.finding_id],
                ),
                trigger_refs=(blocked_dimension.dimension_id, finding.finding_id),
            )

        if resource_signal is not None and resource_signal.status == "Blocked":
            return GateDecision(
                overall_gate="PAUSE",
                main_risk=resource_signal.summary,
                first_next_action=NextAction(
                    action_id="action-resolve-resource-blocker",
                    title="Resolve the confirmed resource shortfall",
                    description=(
                        "Increase available resources or select a lower-cost validation path "
                        "before continuing."
                    ),
                    action_type="Resolve Blocker",
                    reason_refs=["resource_signal"],
                ),
                trigger_refs=("resource_signal",),
            )

        gate_critical_unknown = next(
            (
                dimension
                for dimension in dimensions
                if dimension.status == "Unknown"
                and any(finding.gate_critical for finding in dimension.findings)
            ),
            None,
        )
        if gate_critical_unknown is not None:
            finding = next(
                finding for finding in gate_critical_unknown.findings if finding.gate_critical
            )
            return GateDecision(
                overall_gate="CONDITIONAL PROCEED",
                main_risk=finding.title,
                first_next_action=NextAction(
                    action_id="action-resolve-gate-critical-unknown",
                    title=f"Verify: {finding.title}",
                    description=finding.summary,
                    action_type="Resolve Gate-critical Unknown",
                    reason_refs=[gate_critical_unknown.dimension_id, finding.finding_id],
                ),
                trigger_refs=(gate_critical_unknown.dimension_id, finding.finding_id),
            )

        warning_dimension = next(
            (dimension for dimension in dimensions if dimension.status == "Warning"),
            None,
        )
        if warning_dimension is not None:
            finding = warning_dimension.findings[0]
            return GateDecision(
                overall_gate="CONDITIONAL PROCEED",
                main_risk=finding.title,
                first_next_action=NextAction(
                    action_id="action-mitigate-dimension-warning",
                    title=f"Mitigate: {finding.title}",
                    description=finding.summary,
                    action_type="Mitigate Warning",
                    reason_refs=[warning_dimension.dimension_id, finding.finding_id],
                ),
                trigger_refs=(warning_dimension.dimension_id, finding.finding_id),
            )

        for signal in (resource_signal, evaluation_signal):
            if signal is not None and signal.status == "Warning":
                reference = getattr(signal, "signal_id", "resource_signal")
                return self._signal_decision(
                    signal.status,
                    signal.summary,
                    reference,
                )

        unknown_dimension = next(
            (dimension for dimension in dimensions if dimension.status == "Unknown"),
            None,
        )
        if unknown_dimension is not None:
            finding = unknown_dimension.findings[0]
            return GateDecision(
                overall_gate="CONDITIONAL PROCEED",
                main_risk=unknown_dimension.summary,
                first_next_action=NextAction(
                    action_id="action-validate-dimension-unknown",
                    title=f"Validate: {finding.title}",
                    description=finding.summary,
                    action_type="Minimum Validation",
                    reason_refs=[unknown_dimension.dimension_id, finding.finding_id],
                ),
                trigger_refs=(unknown_dimension.dimension_id, finding.finding_id),
            )

        if resource_signal is not None and resource_signal.status == "Unknown":
            return self._signal_decision(
                resource_signal.status,
                resource_signal.summary,
                "resource_signal",
            )
        if evaluation_signal is not None and evaluation_signal.status == "Unknown":
            return self._signal_decision(
                evaluation_signal.status,
                evaluation_signal.summary,
                evaluation_signal.signal_id,
            )

        return GateDecision(
            overall_gate="PROCEED",
            main_risk="No confirmed blocker or material unresolved readiness condition is present.",
            first_next_action=NextAction(
                action_id="action-run-minimum-validation",
                title="Run the minimum validation before higher-cost reproduction work",
                description=(
                    "Continue with the smallest reasonable validation step before committing to "
                    "a more expensive reproduction path."
                ),
                action_type="Minimum Validation",
                reason_refs=["RD-01", "RD-02", "RD-03"],
            ),
            trigger_refs=("RD-01", "RD-02", "RD-03"),
        )

    @staticmethod
    def _signal_decision(status: str, summary: str, reference: str) -> GateDecision:
        action_type = "Mitigate Warning" if status == "Warning" else "Minimum Validation"
        verb = "Mitigate" if status == "Warning" else "Validate"
        return GateDecision(
            overall_gate="CONDITIONAL PROCEED",
            main_risk=summary,
            first_next_action=NextAction(
                action_id=f"action-review-{reference}",
                title=f"{verb} the unresolved additional signal",
                description=summary,
                action_type=action_type,
                reason_refs=[reference],
            ),
            trigger_refs=(reference,),
        )
