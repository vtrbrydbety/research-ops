"""Conflict/Finding safeguards at the current local Draft -> Rule boundary.

The separate global ConflictFindingContextBuilder/Normalizer were retired.
These scenarios retain source validation, both conflict sides, deduplication,
unknown propagation, bounded model scope and safe provider/fake boundaries.
"""

import asyncio
import json
from hashlib import sha256

import httpx
import pytest
from pydantic import ValidationError

from researchops.schemas import AIEvidenceFindingDraftInvocation, AIEvidenceFindingDraftResult
from researchops.services import (
    AIModelResponseError,
    DeepSeekAnalysisModel,
    LocalEvidenceFindingRuleService,
)
from tests.test_deepseek_context_gap import _settings
from tests.test_deepseek_evidence_finding_draft import _chat_response
from tests.test_local_evidence_finding_rules import _context
from tests.test_model_readiness_graph import _trace


def _fixture():
    context = _context()
    first = context.bundle.sources[0]
    second_text = "Python 3.10 is required."
    second = first.model_copy(
        update={
            "source_id": "src-config",
            "source_path": "config.yaml",
            "title": "config.yaml",
            "content": second_text,
            "content_sha256": sha256(second_text.encode()).hexdigest(),
            "original_content_sha256": sha256(second_text.encode()).hexdigest(),
            "original_char_count": len(second_text),
        }
    )
    unrelated = first.model_copy(
        update={"source_id": "src-unrelated", "content": "private-unrelated-material"}
    )
    context = context.model_copy(
        update={
            "bundle": context.bundle.model_copy(update={"sources": [first, second, unrelated]}),
            "relevant_source_ids": [first.source_id, second.source_id],
        }
    )
    evidence = []
    for index, source in enumerate([first, second]):
        evidence.append(
            {
                "local_evidence_id": f"E{index}",
                "condition_refs": ["rd02.software_requirements"],
                "source_ref": source.source_id,
                "source_type": "Material",
                "evidence_type": "Fact",
                "location": f"{source.source_path} lines 1-1",
                "line_start": 1,
                "line_end": 1,
                "material_type": "README",
                "quote": source.content,
                "claim": source.content,
                "verification_status": "Located Only",
            }
        )
    finding = {
        "local_finding_id": "F1",
        "operation": "create",
        "condition": "rd02.software_requirements",
        "summary": "The two source-backed versions disagree.",
        "finding_type": "Unknown",
        "primary_dimension": "RD-02",
        "related_dimensions": [],
        "evidence_refs_local": ["E0", "E1"],
    }
    conflict = {
        "local_conflict_id": "C1",
        "condition_ref": "rd02.software_requirements",
        "summary": "Both stated versions must remain visible.",
        "local_evidence_refs": ["E0", "E1"],
        "related_existing_evidence_refs": [],
        "primary_dimension": "RD-02",
        "related_dimensions": [],
    }
    draft = AIEvidenceFindingDraftResult(
        evidence_drafts=evidence,
        finding_drafts=[finding],
        conflict_drafts=[conflict],
        handoff={"needs_more_information": False, "ready_for_rule": True},
    )
    return context, draft


def test_context_contains_only_rule_usable_evidence_and_no_unbounded_source_text():
    context, draft = _fixture()
    outcome = LocalEvidenceFindingRuleService().adjudicate(context, draft)
    assert outcome.analysis.examined_source_ids == ["src-readme", "src-config"]
    assert {candidate.locator.source_id for candidate in outcome.analysis.evidence_candidates} == {
        "src-readme",
        "src-config",
    }
    assert all(
        result.decision == "accepted" for result in outcome.evidence_validation.evidence_results
    )
    assert "private-unrelated-material" not in outcome.analysis.model_dump_json()


def test_normalizer_merges_duplicate_conflicts_and_same_root_findings_without_picking_side():
    context, draft = _fixture()
    duplicate = draft.model_copy(
        update={
            "conflict_drafts": [
                draft.conflict_drafts[0],
                draft.conflict_drafts[0].model_copy(update={"local_conflict_id": "C2"}),
            ],
            "finding_drafts": [
                draft.finding_drafts[0],
                draft.finding_drafts[0].model_copy(
                    update={"local_finding_id": "F2", "finding_type": "Fact"}
                ),
            ],
        }
    )
    outcome = LocalEvidenceFindingRuleService().adjudicate(context, duplicate)
    assert (
        len(outcome.analysis.conflict_candidates) == len(outcome.analysis.finding_candidates) == 1
    )
    evidence_ids = {item.candidate_id for item in outcome.analysis.evidence_candidates}
    assert set(outcome.analysis.conflict_candidates[0].evidence_candidate_ids) == evidence_ids
    assert set(outcome.analysis.finding_candidates[0].evidence_candidate_ids) == evidence_ids
    assert outcome.analysis.finding_candidates[0].finding_type == "Unknown"
    assert {item.candidate_kind for item in outcome.merges} == {"conflict", "finding"}
    assert outcome.candidate_adjudication.conflict_results[0].decision == "accepted"


def test_normalizer_rejects_partial_or_foreign_evidence_accounting():
    context, draft = _fixture()
    payload = draft.model_dump(mode="json")
    payload["conflict_drafts"][0]["local_evidence_refs"] = ["E0", "invented-evidence"]
    payload["finding_drafts"][0]["evidence_refs_local"] = ["E0", "invented-evidence"]
    outcome = LocalEvidenceFindingRuleService().adjudicate(
        context, AIEvidenceFindingDraftResult.model_validate(payload)
    )
    assert outcome.rule_issues
    assert not outcome.candidate_adjudication.admitted_conflict_candidates
    assert not outcome.candidate_adjudication.admitted_finding_candidates


def test_downgraded_located_evidence_can_inform_finding_but_not_confirm_conflict():
    context, draft = _fixture()
    payload = draft.model_dump(mode="json")
    payload["evidence_drafts"][1]["evidence_type"] = "Unknown"
    payload["evidence_drafts"][1]["conflict_note"] = "The current material is insufficient."
    outcome = LocalEvidenceFindingRuleService().adjudicate(
        context, AIEvidenceFindingDraftResult.model_validate(payload)
    )
    assert not outcome.candidate_adjudication.admitted_conflict_candidates
    assert outcome.candidate_adjudication.admitted_finding_candidates, (
        outcome.evidence_validation.model_dump()
    )
    finding = outcome.candidate_adjudication.admitted_finding_candidates[0]
    assert finding.finding_type == "Unknown"
    assert len(finding.evidence_candidate_ids) == 2


def test_contract_forbids_gate_and_requires_stable_merge_keys():
    _, draft = _fixture()
    payload = draft.model_dump(mode="json")
    payload["overall_gate"] = "PROCEED"
    with pytest.raises(ValidationError):
        AIEvidenceFindingDraftResult.model_validate(payload)
    payload.pop("overall_gate")
    payload["conflict_drafts"][0]["condition_ref"] = ""
    with pytest.raises(ValidationError):
        AIEvidenceFindingDraftResult.model_validate(payload)


def test_fake_conflict_finding_model_supports_sync_and_async_boundaries():
    from researchops.testing.fake_model import FakeEvidenceFindingDraftModel

    context, draft = _fixture()
    expected = AIEvidenceFindingDraftInvocation(result=draft, trace=_trace("fake-local-draft"))
    fake = FakeEvidenceFindingDraftModel([expected, expected])
    first = fake.draft_evidence_findings(context)
    first.result.conflict_drafts[0].summary = "mutated"
    second = asyncio.run(fake.draft_evidence_findings_async(context))
    assert second.result.conflict_drafts[0].summary == expected.result.conflict_drafts[0].summary
    assert fake.bundle_ids == [context.bundle.bundle_id] * 2


def test_deepseek_conflict_stage_sends_only_validated_context_and_rejects_partial_accounting():
    context, draft = _fixture()
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        return httpx.Response(200, json=_chat_response(draft.model_dump(mode="json")))

    model = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    invocation = model.draft_evidence_findings(context)
    content = json.loads(observed["messages"][1]["content"])
    assert content["ANALYSIS_STAGE"] == "evidence_finding_draft"
    assert "MATERIAL_BUNDLE" not in content
    assert "private-unrelated-material" not in json.dumps(content)
    assert len(invocation.result.conflict_drafts[0].local_evidence_refs) == 2
    assert "overall_gate" not in content["OUTPUT_SCHEMA"]["properties"]
    invalid = draft.model_dump(mode="json")
    invalid["conflict_drafts"][0]["local_evidence_refs"] = ["invented"]
    bad_client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_chat_response(invalid)))
    )
    with pytest.raises(AIModelResponseError):
        DeepSeekAnalysisModel(_settings(), client=bad_client).draft_evidence_findings(context)


def test_probe_failure_finding_must_keep_its_validated_evidence():
    context = _context()
    text = "Probe failed: network timeout; checkpoint accessibility is not established."
    source = context.bundle.sources[0].model_copy(
        update={
            "material_type": "Checkpoint-Release",
            "source_url": None,
            "source_path": ".researchops/tool-results/checkpoint.json",
            "content": text,
            "content_sha256": sha256(text.encode()).hexdigest(),
            "original_content_sha256": sha256(text.encode()).hexdigest(),
            "original_char_count": len(text),
        }
    )
    context = context.model_copy(
        update={
            "bundle": context.bundle.model_copy(update={"sources": [source]}),
            "condition_contexts": [
                context.condition_contexts[0].model_copy(
                    update={
                        "condition_ref": "rd03.checkpoint_access",
                        "primary_dimension": "RD-03",
                    }
                )
            ],
            "focus": context.focus.model_copy(update={"scope_refs": ["RD-03"]}),
            "current_information_gaps": [],
        }
    )
    # Validate copied nested objects too, preserving the real provider input contract.
    context = type(context).model_validate(context.model_dump())
    payload = {
        "evidence_drafts": [
            {
                "local_evidence_id": "probe",
                "condition_refs": ["rd03.checkpoint_access"],
                "source_ref": source.source_id,
                "source_type": "Material",
                "evidence_type": "Fact",
                "location": source.source_path,
                "line_start": 1,
                "line_end": 1,
                "material_type": source.material_type,
                "quote": text,
                "claim": text,
                "verification_status": "Located Only",
            }
        ],
        "finding_drafts": [
            {
                "local_finding_id": "probe-unknown",
                "operation": "create",
                "condition": "rd03.checkpoint_access",
                "summary": "The failed probe leaves access unverified.",
                "finding_type": "Unknown",
                "primary_dimension": "RD-03",
                "evidence_refs_local": ["probe"],
            }
        ],
        "handoff": {"needs_more_information": False, "ready_for_rule": True},
    }
    model = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(payload))
            )
        ),
    )
    invocation = model.draft_evidence_findings(context)
    outcome = LocalEvidenceFindingRuleService().adjudicate(context, invocation.result)
    assert outcome.candidate_adjudication.admitted_finding_candidates, (
        outcome.evidence_validation.model_dump()
    )
    finding = outcome.candidate_adjudication.admitted_finding_candidates[0]
    assert finding.finding_type == "Unknown"
    assert finding.evidence_candidate_ids == [outcome.analysis.evidence_candidates[0].candidate_id]
    assert outcome.readiness.overall_gate != "PAUSE"
    payload["finding_drafts"][0]["evidence_refs_local"] = []
    with pytest.raises(AIModelResponseError, match="probe"):
        model.draft_evidence_findings(context)
