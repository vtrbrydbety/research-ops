"""Static guardrails for the frozen-visual Step 10 frontend wiring."""

from pathlib import Path

MVP_API = Path("apps/mvp/mvp-api.js")
MVP_HTML = Path("apps/mvp/index.html")


def test_frontend_uses_real_job_progress_and_human_feedback_endpoints() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "'/api/v1/assessment-jobs'" in script
    assert "waitForAssessmentJob" in script
    assert "material_source_count" in script
    assert "evidence_candidate_count" in script
    assert "/feedback`" in script


def test_target_confirmation_renders_real_candidates_with_identity_provenance() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "candidateList.replaceChildren()" in script
    assert "resolution.candidates.forEach" in script
    assert "Metadata basis" in script
    assert "Stable identity" in script
    assert "No repository, paper" in script
    assert "Number.parseInt(selectedTargetCandidate, 10)" in script


def test_all_real_gate_results_render_in_the_shared_overview() -> None:
    script = MVP_API.read_text(encoding="utf-8")
    function_body = script.split("function applyCompletedAssessment", maxsplit=1)[1].split(
        "function firstBlockingEvidence", maxsplit=1
    )[0]

    assert "const scenario = 'conditional'" in function_body
    assert "showScreen('overview')" in function_body
    assert "showScreen('pause')" not in function_body
    assert "showScreen('proceed')" not in function_body


def test_frontend_does_not_post_to_legacy_synchronous_assessment_path() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "const assessmentEndpoint = '/api/v1/assessments'" not in script


def test_gate_unavailable_does_not_invent_a_candidate_review_workflow() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "assessment.pending_confirmations" not in script
    assert "openPendingConfirmation" not in script
    assert "feedbackContext === 'pending'" not in script
    assert "gateNaContinue.addEventListener('click'" in script
    assert "void startAssessmentProcessing()" in script
    assert "'model_unavailable'" in script


def test_manual_input_state_has_an_enabled_action_that_opens_manual_setup() -> None:
    script = MVP_API.read_text(encoding="utf-8")
    render = script.split("function applyGateUnavailableAssessment", maxsplit=1)[1].split(
        "function renderTechnicalTrace", maxsplit=1
    )[0]
    handler = script.split(
        "gateNaContinue.addEventListener('click'", maxsplit=1
    )[1].split("failureSnapshot.addEventListener", maxsplit=1)[0]

    assert "'manual_input_required'" in render
    assert "Provide manual input" in render
    assert "latestAssessment?.analysis_state === 'manual_input_required'" in handler
    assert "selectEnvironmentMode('manual')" in handler
    assert "showScreen('setup')" in handler


def test_dimension_feedback_targets_the_displayed_finding() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "findingIdByDimension[target.key] = finding.finding_id" in script
    assert "target_type: 'finding', target_id: finding.finding_id" in script
    assert "/api/v1/assessments/${encodeURIComponent(latestAssessmentId)}" in script
    assert "target_type: 'unresolved_question'" not in script
    assert "target_type: 'criterion'" not in script


def test_evidence_feedback_uses_only_the_current_revision_evidence_id() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "const targetId = activeFeedbackTarget?.target_type === 'evidence'" in script
    assert "item.evidence_id === targetId" in script
    assert "Never infer identity from rendered labels" in script
    assert "const displayed = retained ||" not in script


def test_missing_real_evidence_cannot_open_the_frozen_demo_evidence() -> None:
    script = MVP_API.read_text(encoding="utf-8")
    handler = script.split(
        "document.getElementById('dimension-view-evidence').addEventListener",
        maxsplit=1,
    )[1].split("authorizeBtn.addEventListener", maxsplit=1)[0]

    assert handler.index("event.stopImmediatePropagation()") < handler.index(
        "if (!evidences.length)"
    )
    assert handler.index("event.preventDefault()") < handler.index("if (!evidences.length)")
    assert "const {scenario, key, evidences} = dimensionEvidenceState()" in handler
    assert "const key = displayedDimensionKey()" in script
    assert "dimensionEvidenceByScenario.conditional?.[key]?.length" in handler
    assert "viewEvidence.disabled = !hasRealEvidence" in handler


def test_production_mvp_has_no_fgi_default_or_static_feedback_path() -> None:
    page = MVP_HTML.read_text(encoding="utf-8")
    script = MVP_API.read_text(encoding="utf-8")

    assert "aseuteurideu/FGI" not in page
    assert "FGI reproduction" not in page
    assert "staticDemoHashes" in script
    assert "window.history.replaceState(null, '', window.location.pathname + window.location.search)" in script
    assert "only a Finding returned by the\n    // current Assessment can open a production feedback panel" in script
    assert "current revision supplied a stable Evidence ID" in script


def test_evidence_drawer_preserves_verified_lines_and_truthful_non_file_locators() -> None:
    script = MVP_API.read_text(encoding="utf-8")

    assert "function hasExactEvidenceLocation(evidence)" in script
    assert "evidence.line_start >= 1" in script
    assert "evidence.line_end >= evidence.line_start" in script
    assert "return `${canonical}:lines ${evidence.line_start}-${evidence.line_end}`" in script
    assert "function hasInspectableEvidence(evidence)" in script
    assert "return exactEvidenceLocation(evidence) || String(evidence?.location || 'Locator unavailable')" in script
    assert script.count("evidenceLocation.textContent = displayEvidenceLocation(evidence)") == 3
    assert "(finding.evidence || []).filter(hasInspectableEvidence)" in script
    assert "!hasInspectableEvidence(sourceA) || !hasInspectableEvidence(sourceB)" in script
    assert "evidenceDrawer.classList.remove('active');" in script


def test_revision_history_is_loaded_from_the_current_assessment_and_shows_diffs() -> None:
    page = MVP_HTML.read_text(encoding="utf-8")
    script = MVP_API.read_text(encoding="utf-8")

    assert 'id="assessment-history-btn"' in page
    assert 'id="revision-history"' in page
    assert "/revisions`" in script
    assert "function revisionChangeCopy(change)" in script
    assert "Overall Gate changed" in script
    assert "Assessment revision history" in page
