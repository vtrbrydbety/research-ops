"""冻结 Gate 聚合与 Next Action 优先级测试。"""

from researchops.schemas import (
    EvaluationSignal,
    Evidence,
    Finding,
    ReadinessDimension,
    ResourceItem,
    ResourceSignal,
)
from researchops.services import GateDecisionService


def _dimension(
    dimension_id: str,
    status: str,
    *,
    gate_critical: bool = False,
) -> ReadinessDimension:
    names = {
        "RD-01": "Data & Access Readiness",
        "RD-02": "Environment & Dependency Readiness",
        "RD-03": "Weights & Configuration Readiness",
    }
    return ReadinessDimension(
        dimension_id=dimension_id,
        name=names[dimension_id],
        status=status,
        summary=f"{dimension_id} is {status}.",
        gate_impact=f"{status} gate impact.",
        findings=[
            Finding(
                finding_id=f"{dimension_id}-F01",
                condition=f"{dimension_id} condition",
                title=f"{dimension_id} finding",
                summary=f"Evidence-backed {status} finding.",
                finding_type="Unknown" if status == "Unknown" else "Fact",
                gate_critical=gate_critical,
                readiness_impact=f"{status} impact",
                evidence=[
                    Evidence(
                        evidence_type="Unknown" if status == "Unknown" else "Fact",
                        verification_status="Located Only",
                        source_type="Material",
                        material_type="Other",
                        summary="Test evidence.",
                        source="test fixture",
                        location="fixture:1",
                        excerpt="fixture value",
                    )
                ],
            )
        ],
    )


def test_core_dimension_blocked_triggers_pause() -> None:
    decision = GateDecisionService().resolve(
        [
            _dimension("RD-01", "Ready"),
            _dimension("RD-02", "Blocked", gate_critical=True),
            _dimension("RD-03", "Ready"),
        ],
        None,
        None,
    )

    assert decision.overall_gate == "PAUSE"
    assert decision.main_risk == "RD-02 finding"
    assert decision.first_next_action.action_type == "Resolve Blocker"
    assert decision.trigger_refs == ("RD-02", "RD-02-F01")


def test_gate_critical_unknown_precedes_warning() -> None:
    decision = GateDecisionService().resolve(
        [
            _dimension("RD-01", "Unknown", gate_critical=True),
            _dimension("RD-02", "Warning"),
            _dimension("RD-03", "Ready"),
        ],
        None,
        None,
    )

    assert decision.overall_gate == "CONDITIONAL PROCEED"
    assert decision.main_risk == "RD-01 finding"
    assert decision.first_next_action.action_type == "Resolve Gate-critical Unknown"
    assert decision.trigger_refs == ("RD-01", "RD-01-F01")


def test_all_ready_without_material_signal_triggers_proceed() -> None:
    decision = GateDecisionService().resolve(
        [
            _dimension("RD-01", "Ready"),
            _dimension("RD-02", "Ready"),
            _dimension("RD-03", "Ready"),
        ],
        None,
        None,
    )

    assert decision.overall_gate == "PROCEED"
    assert decision.first_next_action.action_type == "Minimum Validation"
    assert decision.trigger_refs == ("RD-01", "RD-02", "RD-03")


def test_warning_signal_precedes_unknown_signal() -> None:
    evidence = Evidence(
        evidence_type="Unknown",
        verification_status="Located Only",
        source_type="Material",
        material_type="Other",
        summary="Signal evidence.",
        source="test fixture",
        location="fixture:signal",
        excerpt="fixture signal",
    )
    resource = ResourceSignal(
        status="Unknown",
        summary="Resource requirements are unknown.",
        gate_impact="Supports CONDITIONAL PROCEED.",
        items=[
            ResourceItem(resource="GPU / VRAM", current="Known", required="Unknown"),
            ResourceItem(resource="Disk", current="Known", required="Unknown"),
            ResourceItem(resource="Time budget", current="Known", required="Unknown"),
        ],
        evidence=evidence,
    )
    evaluation = EvaluationSignal(
        signal_id="evaluation-warning",
        status="Warning",
        conflict_type="Metric Definition",
        summary="A known metric difference requires mitigation.",
        evidence_refs=[evidence],
        gate_impact="Supports CONDITIONAL PROCEED.",
    )

    decision = GateDecisionService().resolve(
        [
            _dimension("RD-01", "Ready"),
            _dimension("RD-02", "Ready"),
            _dimension("RD-03", "Ready"),
        ],
        resource,
        evaluation,
    )

    assert decision.overall_gate == "CONDITIONAL PROCEED"
    assert decision.main_risk == evaluation.summary
    assert decision.first_next_action.action_type == "Mitigate Warning"


def test_warning_signal_precedes_noncritical_dimension_unknown() -> None:
    """明确 Warning 的处置优先级高于非 Gate-critical Unknown。"""

    evidence = Evidence(
        evidence_type="Fact",
        verification_status="Located Only",
        source_type="Material",
        material_type="Other",
        summary="Known signal difference.",
        source="test fixture",
        location="fixture:warning",
        excerpt="known warning",
    )
    evaluation = EvaluationSignal(
        signal_id="evaluation-warning",
        status="Warning",
        conflict_type="Paper-Code Setting",
        summary="A known evaluation setting difference requires mitigation.",
        evidence_refs=[evidence],
        gate_impact="Supports CONDITIONAL PROCEED.",
    )

    decision = GateDecisionService().resolve(
        [
            _dimension("RD-01", "Unknown", gate_critical=False),
            _dimension("RD-02", "Ready"),
            _dimension("RD-03", "Ready"),
        ],
        None,
        evaluation,
    )

    assert decision.overall_gate == "CONDITIONAL PROCEED"
    assert decision.main_risk == evaluation.summary
    assert decision.first_next_action.action_type == "Mitigate Warning"
    assert decision.trigger_refs == ("evaluation-warning",)
