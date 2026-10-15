"""Rule admission for local Evidence/Finding drafts."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from researchops.schemas import (
    AIEvidenceFindingDraftResult,
    EvidenceFindingConditionContext,
    EvidenceFindingHandoff,
    EvidenceFindingInput,
    MaterialBundle,
    MaterialSource,
    PhaseInformationGap,
    ResolvedTarget,
)
from researchops.services import LocalEvidenceFindingRuleService


def _context() -> EvidenceFindingInput:
    content = "Python 3.11 is required."
    bundle = MaterialBundle(
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
                source_id="src-readme",
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
    return EvidenceFindingInput(
        bundle=bundle,
        focus={"scope_refs": ["RD-02"], "finding_refs": []},
        condition_contexts=[
            EvidenceFindingConditionContext(
                condition_ref="rd02.software_requirements",
                primary_dimension="RD-02",
            )
        ],
        current_information_gaps=[
            PhaseInformationGap(
                gap_id="GAP-python",
                question="Which Python version is required?",
                scope_ref="RD-02",
                needed_source_type="Material",
                reason="The version must be source-bound.",
            )
        ],
        relevant_source_ids=["src-readme"],
    )


def _draft(*, quote: str = "Python 3.11 is required.") -> AIEvidenceFindingDraftResult:
    return AIEvidenceFindingDraftResult(
        evidence_drafts=[
            {
                "local_evidence_id": "EVD-python",
                "condition_refs": ["rd02.software_requirements"],
                "source_ref": "src-readme",
                "source_type": "Material",
                "evidence_type": "Fact",
                "location": "README.md lines 1-1",
                "line_start": 1,
                "line_end": 1,
                "material_type": "README",
                "quote": quote,
                "claim": "The project requires Python 3.11.",
                "verification_status": "Located Only",
            }
        ],
        finding_drafts=[
            {
                "local_finding_id": "FD-python-a",
                "operation": "create",
                "condition": "rd02.software_requirements",
                "summary": "Python 3.11 is documented.",
                "finding_type": "Fact",
                "primary_dimension": "RD-02",
                "evidence_refs_local": ["EVD-python"],
                "source_gap_refs": ["GAP-python"],
            },
            {
                "local_finding_id": "FD-python-b",
                "operation": "create",
                "condition": "rd02.software_requirements",
                "summary": "The same requirement has a second local draft.",
                "finding_type": "Fact",
                "primary_dimension": "RD-02",
                "evidence_refs_local": ["EVD-python"],
                "source_gap_refs": ["GAP-python"],
            },
        ],
        handoff=EvidenceFindingHandoff(
            needs_more_information=False,
            ready_for_rule=True,
        ),
    )


def test_same_local_draft_has_stable_ids_merges_and_rule_result() -> None:
    context = _context()
    draft = _draft()
    service = LocalEvidenceFindingRuleService()

    first = service.adjudicate(context, draft)
    second = service.adjudicate(context, draft)

    assert first.analysis.analysis_id == second.analysis.analysis_id
    assert first.stable_id_by_local_ref == second.stable_id_by_local_ref
    assert first.candidate_adjudication.admitted_evidence_candidate_ids
    assert len(first.candidate_adjudication.admitted_finding_candidates) == 1
    assert first.merges[0].candidate_kind == "finding"
    assert first.gap_resolutions[0].state == "resolved_by_verified_evidence"
    assert first.readiness.decision_available is True
    assert first.readiness.overall_gate is not None
    assert first.readiness.first_next_action is not None


def test_hallucinated_quote_is_rejected_and_cannot_enter_assessment() -> None:
    outcome = LocalEvidenceFindingRuleService().adjudicate(
        _context(),
        _draft(quote="Python 9.99 is required."),
    )

    assert outcome.evidence_validation.evidence_results[0].decision == "rejected"
    assert not outcome.candidate_adjudication.admitted_evidence_candidate_ids
    assert not outcome.candidate_adjudication.admitted_finding_candidates
    assert outcome.gap_resolutions[0].state == "unresolved"
    assert "No linked Evidence Draft passed" in outcome.gap_resolutions[0].reason


def test_remaining_gap_has_concrete_rule_reason_without_global_coverage() -> None:
    draft = AIEvidenceFindingDraftResult(
        remaining_information_gaps=[
            {
                "gap_ref": "GAP-python",
                "reason": "No supplied source states the required Python version.",
            }
        ],
        handoff={"needs_more_information": True, "ready_for_rule": True},
    )

    outcome = LocalEvidenceFindingRuleService().adjudicate(_context(), draft)

    assert outcome.gap_resolutions == (
        outcome.gap_resolutions[0],
    )
    assert outcome.gap_resolutions[0].state == "unresolved"
    assert outcome.gap_resolutions[0].reason.startswith("No supplied source")
    assert not outcome.analysis.evidence_candidates


def test_unresolved_candidate_reference_is_a_rule_issue_not_a_model_failure() -> None:
    draft = AIEvidenceFindingDraftResult(
        finding_drafts=[
            {
                "local_finding_id": "FD-missing-evidence",
                "operation": "create",
                "condition": "rd02.software_requirements",
                "summary": "A requirement was proposed without a resolvable Evidence Draft.",
                "finding_type": "Fact",
                "primary_dimension": "RD-02",
                "evidence_refs_local": ["EVD-missing"],
                "source_gap_refs": ["GAP-python"],
            }
        ],
        handoff={"needs_more_information": False, "ready_for_rule": True},
    )

    outcome = LocalEvidenceFindingRuleService().adjudicate(_context(), draft)

    assert not outcome.candidate_adjudication.admitted_finding_candidates
    assert outcome.gap_resolutions[0].state == "unresolved"
    assert any("could not resolve" in item.reason for item in outcome.rule_issues)
