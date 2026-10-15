"""Frozen Prompt V1.0 phase-contract regression tests."""

import pytest
from pydantic import ValidationError

from researchops.schemas import (
    AcquisitionLoopControl,
    AcquisitionRequestDraft,
    AIContextGapResult,
    AIEvidenceFindingDraftResult,
    AIFeedbackScopeResult,
    AIToolAcquisitionResult,
    ContextGapControl,
    ContextGapFocus,
    EvidenceDraft,
    EvidenceFindingHandoff,
    FeedbackAffectedRefs,
    FindingDraft,
    PhaseInformationGap,
    RemainingInformationGap,
    SupportedFactDraft,
)


def _gap(gap_id: str = "GAP-01") -> PhaseInformationGap:
    return PhaseInformationGap(
        gap_id=gap_id,
        question="Which Python version is required?",
        scope_ref="RD-02",
        needed_source_type="Material",
        reason="The environment condition cannot be evaluated without the version.",
    )


def test_context_gap_contract_has_no_tool_or_gate_fields() -> None:
    result = AIContextGapResult(
        analysis_mode="initial",
        focus=ContextGapFocus(scope_refs=["RD-02"]),
        supported_facts=[
            SupportedFactDraft(
                statement="The repository contains an environment file.",
                source_ref="src-environment",
                verification_status="Located Only",
            )
        ],
        information_gaps=[_gap()],
        control=ContextGapControl(
            target_confirmation_needed=False,
            more_information_needed=True,
        ),
    )

    assert result.information_gaps[0].gap_id == "GAP-01"
    payload = result.model_dump()
    payload["tool_requests"] = []
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIContextGapResult.model_validate(payload)

    payload = result.model_dump()
    payload["overall_gate"] = "PROCEED"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIContextGapResult.model_validate(payload)


def test_context_gap_contract_enforces_minimum_consistent_handoff() -> None:
    with pytest.raises(ValidationError, match="需要更多信息"):
        AIContextGapResult(
            analysis_mode="initial",
            focus=ContextGapFocus(scope_refs=["RD-01"]),
            information_gaps=[_gap()],
            control=ContextGapControl(
                target_confirmation_needed=False,
                more_information_needed=False,
            ),
        )

    with pytest.raises(ValidationError, match="target_confirmation_required"):
        AIContextGapResult(
            analysis_mode="initial",
            focus=ContextGapFocus(scope_refs=["RD-01"]),
            control=ContextGapControl(
                target_confirmation_needed=True,
                more_information_needed=True,
            ),
        )


def test_tool_acquisition_contract_is_gap_bound_and_non_executing() -> None:
    result = AIToolAcquisitionResult(
        acquisition_state="tool_request",
        requests=[
            AcquisitionRequestDraft(
                gap_ref="GAP-01",
                requested_fact="Read the declared Python version.",
                source_type="Material",
                material_type_hint="Config",
                tool_ref="read_github_file",
                read_scope="environment.yml only",
                url="https://github.com/example/project/blob/main/environment.yml",
                expected_evidence="An exact version declaration with its source location.",
            )
        ],
        loop_control=AcquisitionLoopControl(
            current_round=1,
            configured_max_rounds=5,
            continue_after_result=True,
        ),
    )

    assert result.requests[0].gap_ref == "GAP-01"
    payload = result.model_dump()
    payload["tool_results"] = []
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIToolAcquisitionResult.model_validate(payload)

    with pytest.raises(ValidationError, match="最小 read_scope"):
        AcquisitionRequestDraft(
            gap_ref="GAP-01",
            requested_fact="Read the requirement.",
            source_type="Material",
            tool_ref="read_github_file",
            expected_evidence="A source-bound requirement.",
        )


def test_evidence_finding_contract_validates_local_lineage_and_location() -> None:
    evidence = EvidenceDraft(
        local_evidence_id="EVD-01",
        condition_refs=["rd02.software_requirements"],
        source_ref="src-readme",
        source_type="Material",
        evidence_type="Fact",
        location="README.md lines 12-13",
        line_start=12,
        line_end=13,
        material_type="README",
        quote="Python 3.11 is required.",
        claim="The reproduction environment requires Python 3.11.",
        verification_status="Located Only",
    )
    result = AIEvidenceFindingDraftResult(
        evidence_drafts=[evidence],
        finding_drafts=[
            FindingDraft(
                local_finding_id="FD-01",
                operation="create",
                condition="rd02.software_requirements",
                summary="A Python version requirement is documented.",
                finding_type="Fact",
                primary_dimension="RD-02",
                evidence_refs_local=["EVD-01"],
            )
        ],
        handoff=EvidenceFindingHandoff(
            needs_more_information=False,
            ready_for_rule=True,
        ),
    )

    assert result.finding_drafts[0].evidence_refs_local == ["EVD-01"]
    payload = result.model_dump()
    payload["status"] = "Ready"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIEvidenceFindingDraftResult.model_validate(payload)

    unresolved_reference = AIEvidenceFindingDraftResult(
        evidence_drafts=[evidence],
        finding_drafts=[
            FindingDraft(
                local_finding_id="FD-02",
                operation="create",
                condition="rd02.dependency_requirements",
                summary="A dependency requirement was proposed.",
                finding_type="Inference",
                primary_dimension="RD-02",
                evidence_refs_local=["EVD-missing"],
            )
        ],
        handoff=EvidenceFindingHandoff(
            needs_more_information=False,
            ready_for_rule=True,
        ),
    )
    assert unresolved_reference.finding_drafts[0].evidence_refs_local == ["EVD-missing"]

    with pytest.raises(ValidationError, match="同时提供起止行"):
        EvidenceDraft(
            local_evidence_id="EVD-02",
            condition_refs=["rd02.software_requirements"],
            source_ref="src-readme",
            source_type="Material",
            evidence_type="Fact",
            location="README.md line 12",
            line_start=12,
            quote="Python 3.11 is required.",
            claim="Python 3.11 is required.",
            verification_status="Located Only",
        )


def test_evidence_finding_contract_preserves_unresolved_gaps() -> None:
    result = AIEvidenceFindingDraftResult(
        remaining_information_gaps=[
            RemainingInformationGap(
                gap_ref="GAP-01",
                reason="The exact CUDA version remains absent.",
            )
        ],
        handoff=EvidenceFindingHandoff(
            needs_more_information=True,
            ready_for_rule=True,
        ),
    )

    assert result.remaining_information_gaps[0].still_unresolved is True


def test_feedback_scope_contract_is_local_and_includes_dependent_dimensions() -> None:
    result = AIFeedbackScopeResult(
        reassessment_required=True,
        affected_refs=FeedbackAffectedRefs(
            finding_refs=["finding-checkpoint"],
            evidence_refs=["evidence-checkpoint"],
            dimension_refs=["RD-03", "RD-02"],
            signal_refs=["evaluation_conditions"],
        ),
        change_summary="The checkpoint mapping may also change environment compatibility.",
        handoff="evidence_finding",
    )

    assert result.affected_refs.dimension_refs == ["RD-03", "RD-02"]
    assert "RD-01" not in result.affected_refs.dimension_refs

    payload = result.model_dump()
    payload["overall_gate"] = "PROCEED"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIFeedbackScopeResult.model_validate(payload)


def test_feedback_scope_requires_gap_before_tool_handoff() -> None:
    with pytest.raises(ValidationError, match="必须包含新增 Gap"):
        AIFeedbackScopeResult(
            reassessment_required=True,
            affected_refs=FeedbackAffectedRefs(
                finding_refs=["finding-dataset"],
                dimension_refs=["RD-01"],
            ),
            change_summary="The feedback exposes a missing dataset identity fact.",
            handoff="tool_acquisition",
        )

    result = AIFeedbackScopeResult(
        reassessment_required=True,
        affected_refs=FeedbackAffectedRefs(
            finding_refs=["finding-dataset"],
            dimension_refs=["RD-01"],
        ),
        change_summary="The feedback exposes a missing dataset identity fact.",
        new_information_gaps=[
            PhaseInformationGap(
                gap_id="GAP-feedback-01",
                question="Which dataset release is available to the user?",
                scope_ref="RD-01",
                needed_source_type="User Context",
                reason="The exact dataset identity affects the existing Finding.",
            )
        ],
        handoff="tool_acquisition",
    )
    assert result.handoff == "tool_acquisition"
