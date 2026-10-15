(() => {
  const targetResolutionEndpoint = '/api/v1/targets/resolve';
  const assessmentJobEndpoint = '/api/v1/assessment-jobs';
  const environmentAuthorizationEndpoint = '/api/v1/environment-authorizations';

  const apiTargetType = {
    repository: 'repository',
    paper: 'paper_title',
    doi: 'doi',
    arxiv: 'arxiv',
    project: 'project_page'
  };

  const targetTypeLabel = {
    repository: 'Repository',
    paper_title: 'Paper title',
    doi: 'DOI',
    arxiv: 'arXiv',
    project_page: 'Project page'
  };

  const statusClass = {
    Ready: 'status-chip status-ready',
    Warning: 'status-chip status-warning',
    Blocked: 'status-chip status-blocked',
    Unknown: 'status-chip status-unknown'
  };

  const analysisStateLabel = {
    empty: 'Not started',
    processing: 'Processing',
    partial_result: 'Partial result',
    acquisition_failure: 'Acquisition failure',
    partial_material_acquisition: 'Partial material acquisition',
    tool_failure: 'Tool acquisition failed',
    human_confirmation_required: 'Human confirmation required',
    authorization_required: 'Authorization required',
    manual_input_required: 'Manual input required',
    conflict: 'Conflict',
    configuration_required: 'Model configuration required',
    model_unavailable: 'AI analysis unavailable',
    invalid_model_response: 'Invalid AI output',
    evidence_validation_failure: 'Evidence validation failed'
  };

  const progressPhaseCopy = {
    queued: ['Assessment queued', 'Waiting'],
    resolving_target: ['Resolving the confirmed target', 'Processing'],
    acquiring_context: ['Acquiring environment context', 'Processing'],
    collecting_materials: ['Collecting linked target materials', 'Processing'],
    building_material_bundle: ['Building the bounded material bundle', 'Processing'],
    ai_evidence_analysis: ['AI is extracting Evidence candidates', 'Processing'],
    validating_evidence: ['Rule is validating Evidence sources and quotes', 'Processing'],
    ai_conflict_finding_analysis: ['AI is analyzing Conflict and Finding candidates', 'Processing'],
    validating_candidates: ['Rule is validating Conflict and Finding candidates', 'Processing'],
    rule_adjudication: ['Rule is computing Dimensions and Overall Gate', 'Processing'],
    validating_output: ['Validating the final Assessment contract', 'Processing'],
    completed: ['Assessment completed', 'Complete'],
    failed: ['Assessment processing failed', 'Failed']
  };

  const overviewScreen = document.getElementById('screen-overview');
  const assessmentHistoryBtn = document.getElementById('assessment-history-btn');
  const assessmentHistory = document.getElementById('revision-history');
  const assessmentHistoryContent = document.getElementById('revision-history-content');
  const assessmentHistoryCloseBtn = document.getElementById('assessment-history-close-btn');
  const dimensionKeys = ['rd01', 'rd02', 'rd03'];

  function dimensionsInScreen(screen) {
    return [...screen.querySelectorAll('.dimension-card')].map((card, index) => ({
      key: dimensionKeys[index],
      status: card.querySelector('.status-chip'),
      copy: card.querySelector('.dimension-copy'),
      impact: card.querySelector('.dimension-impact')
    }));
  }

  const overviewDimensionElements = dimensionsInScreen(overviewScreen);
  const dimensionElements = Object.fromEntries(
    ['RD-01', 'RD-02', 'RD-03'].map((dimensionId, index) => [
      dimensionId,
      overviewDimensionElements[index]
    ])
  );

  let latestTargetResolution = null;
  let resolvedTargetForAssessment = null;
  let activeApiConflicts = [];
  let activeApiConflictIndex = 0;
  const dimensionEvidenceByScenario = {
    conditional: {},
    pause: {},
    proceed: {}
  };
  const dimensionEvidenceIndexesByScenario = {
    conditional: {},
    pause: {},
    proceed: {}
  };
  let activeApiEvaluationSignal = null;
  let activeApiResourceSignal = null;
  let activeAcquisitionFailure = null;
  let activeFailureStage = null;
  let environmentAuthorized = false;
  let environmentAuthorizationToken = null;
  let latestAssessment = null;
  let latestAssessmentId = null;
  let activeFeedbackTarget = null;
  let activeAssessmentRun = 0;
  const findingIdByDimension = {};

  function currentTargetType() {
    return apiTargetType[targetTypeEl.value];
  }

  function resetResolvedTarget() {
    latestTargetResolution = null;
    resolvedTargetForAssessment = null;
  }

  function readErrorMessage(payload, response) {
    if (Array.isArray(payload?.details) && payload.details.length) {
      return payload.details.map((detail) => detail.message).join(' ');
    }
    return payload?.message || `API returned HTTP ${response.status}.`;
  }

  async function postJson(url, body) {
    const response = await window.ResearchOpsAccess.fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(readErrorMessage(payload, response));
      error.code = payload?.error_code || null;
      throw error;
    }
    return payload;
  }

  async function getJson(url) {
    const response = await window.ResearchOpsAccess.fetch(url, {headers: {'Accept': 'application/json'}});
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(readErrorMessage(payload, response));
      error.code = payload?.error_code || null;
      throw error;
    }
    return payload;
  }

  const finalDecisionCard = document.getElementById('final-decision');
  const finalDecisionForm = document.getElementById('final-decision-form');
  const finalDecisionStatus = document.getElementById('final-decision-status');
  const finalDecisionSubmit = document.getElementById('final-decision-submit');
  function syncFinalDecisionVisibility() {
    finalDecisionCard.hidden = !latestAssessmentId || !document.querySelector(
      '#screen-overview.active, #screen-pause.active, #screen-proceed.active, ' +
      '#screen-dimension-detail.active, #screen-partial-result.active, #screen-gate-not-available.active'
    );
  }
  const decisionVisibilityObserver = new MutationObserver(syncFinalDecisionVisibility);
  document.querySelectorAll('.screen').forEach((screen) => {
    decisionVisibilityObserver.observe(screen, {attributes: true, attributeFilter: ['class']});
  });
  finalDecisionForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!latestAssessmentId || finalDecisionSubmit.disabled) return;
    const assessmentId = latestAssessmentId;
    const decision = document.getElementById('final-decision-value').value;
    if (!decision) return;
    const rationale = document.getElementById('final-decision-rationale').value.trim();
    finalDecisionSubmit.disabled = true;
    finalDecisionStatus.textContent = 'Recording decision…';
    try {
      const result = await postJson(
        `/api/v1/assessments/${encodeURIComponent(assessmentId)}/final-decision`,
        {decision, rationale: rationale || null}
      );
      if (latestAssessmentId === assessmentId) {
        finalDecisionStatus.textContent = `Decision recorded: ${result.decision}. Rule Gate: ${result.rule_gate_at_decision || 'unavailable'}.`;
      }
    } catch (error) {
      if (latestAssessmentId === assessmentId) {
        finalDecisionStatus.textContent = `Decision could not be recorded: ${error.message}`;
      }
    } finally {
      finalDecisionSubmit.disabled = false;
    }
  });

  function revisionChangeCopy(change) {
    if (!change) return 'Initial AI → Rule adjudication.';
    const details = [];
    details.push(change.overall_gate_changed ? 'Overall Gate changed' : 'Overall Gate unchanged');
    if (change.changed_dimension_ids?.length) {
      details.push(`Dimensions changed: ${change.changed_dimension_ids.join(', ')}`);
    }
    const evidenceDelta = (change.added_evidence_ids?.length || 0) +
      (change.removed_evidence_ids?.length || 0);
    const findingDelta = (change.added_finding_ids?.length || 0) +
      (change.removed_finding_ids?.length || 0);
    if (findingDelta) details.push(`Finding changes: ${findingDelta}`);
    if (evidenceDelta) details.push(`Evidence changes: ${evidenceDelta}`);
    return details.join(' · ');
  }

  async function openAssessmentHistory() {
    if (!latestAssessmentId) return;
    assessmentHistoryContent.replaceChildren();
    assessmentHistory.hidden = false;
    const loading = document.createElement('div');
    loading.className = 'revision-row-copy';
    loading.textContent = 'Loading retained revisions…';
    assessmentHistoryContent.append(loading);
    try {
      const history = await getJson(
        `/api/v1/assessments/${encodeURIComponent(latestAssessmentId)}/revisions`
      );
      assessmentHistoryContent.replaceChildren();
      const changesByRevision = new Map(
        (history.changes || []).map((item) => [item.to_revision, item])
      );
      (history.revisions || []).forEach((revision) => {
        const row = document.createElement('div');
        row.className = 'revision-row';
        const title = document.createElement('div');
        title.className = 'revision-row-title';
        const action = revision.feedback
          ? ` · ${revision.feedback.action} feedback`
          : ' · initial assessment';
        title.textContent = `Revision ${revision.revision}${action}`;
        const copy = document.createElement('div');
        copy.className = 'revision-row-copy';
        copy.textContent = revisionChangeCopy(changesByRevision.get(revision.revision));
        row.append(title, copy);
        assessmentHistoryContent.append(row);
      });
    } catch (error) {
      assessmentHistoryContent.replaceChildren();
      const failure = document.createElement('div');
      failure.className = 'revision-row-copy';
      failure.textContent = `Revision history could not be loaded: ${error.message}`;
      assessmentHistoryContent.append(failure);
    }
  }

  function validateEnvironmentInput() {
    const snapshot = document.getElementById('snapshot-file');
    if (selectedMode === 'snapshot' && !(snapshot.files && snapshot.files[0])) {
      showSetupError('Upload an environment snapshot, choose another environment input mode, or select Not now.');
      return false;
    }

    const manualInput = document.querySelector('.manual-textarea');
    if (selectedMode === 'manual' && !manualInput.value.trim()) {
      showSetupError('Add the environment facts you know, choose another input mode, or select Not now.');
      return false;
    }
    return true;
  }

  function showResolvedTarget(resolvedTarget) {
    resolvedTargetForAssessment = resolvedTarget;
    targetResolved = true;
    targetDeferred = false;
    targetResolvedName = resolvedTarget.display_name;
    targetResolvedTypeLabel = targetTypeLabel[resolvedTarget.target_type];
    prepareTargetIdentified();
    identifiedMaterialsSummary.textContent =
      'Target identity is normalized. Material availability will be evaluated separately during read-only acquisition.';
  }

  function showTargetCandidates(resolution) {
    latestTargetResolution = resolution;
    selectedTargetCandidate = '0';

    const candidateList = document.querySelector('#screen-target-confirm .candidate-list');
    candidateList.replaceChildren();
    resolution.candidates.forEach((candidate, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'candidate';
      button.dataset.candidateIndex = String(index);
      button.innerHTML = [
        `<div class="candidate-type">Candidate ${index + 1} · ${targetTypeLabel[candidate.resolved_target.target_type] || 'Target'}</div>`,
        '<div class="candidate-name"></div>',
        '<div class="candidate-source"></div>',
        '<div class="candidate-source"></div>'
      ].join('');
      button.querySelector('.candidate-name').textContent = candidate.label;
      const details = button.querySelectorAll('.candidate-source');
      details[0].textContent = `Metadata basis · ${candidate.description}`;
      details[1].textContent =
        `Stable identity · ${candidate.resolved_target.canonical_id}` +
        (candidate.resolved_target.canonical_url
          ? ` · ${candidate.resolved_target.canonical_url}`
          : '');
      button.classList.toggle('active', index === 0);
      button.addEventListener('click', () => {
        selectedTargetCandidate = String(index);
        candidateList.querySelectorAll('.candidate').forEach((item) => {
          item.classList.toggle('active', item === button);
        });
      });
      candidateList.append(button);
    });
    document.querySelector('#screen-target-confirm .uncertainty-box').textContent =
      'These are public metadata matches returned for the submitted entry. No repository, paper, ' +
      'or project material has been analyzed yet. Confirm the intended stable identity before read-only material collection begins.';
    showScreen('targetConfirm');
  }

  async function resolveSubmittedTarget() {
    clearSetupError();
    resetResolvedTarget();

    const targetEntry = targetEntryEl.value.trim();
    if (!targetEntry) {
      showSetupError('Add a target entry before starting the assessment.');
      return;
    }
    if (!validateEnvironmentInput()) return;

    continueBtn.disabled = true;
    try {
      const resolution = await postJson(targetResolutionEndpoint, {
        target_type: currentTargetType(),
        target_entry: targetEntry
      });

      if (resolution.status === 'unresolved') {
        if (resolution.analysis_state === 'acquisition_failure') {
          applyAcquisitionFailure({
            failure_title: 'Paper metadata acquisition failed',
            failure_detail_title: 'Public bibliographic metadata lookup',
            main_risk: 'The paper title could not be checked against public metadata right now.',
            first_next_action: {
              description: 'Retry the read-only metadata lookup before confirming the paper target.'
            }
          }, 'target_resolution');
        } else {
          showSetupError('ResearchOps could not normalize this entry. Check its format or provide another identifier.');
        }
      } else if (resolution.status === 'requires_confirmation') {
        showTargetCandidates(resolution);
      } else {
        showResolvedTarget(resolution.resolved_target);
      }
    } catch (error) {
      showSetupError(`Target Resolution API unavailable: ${error.message}`);
    } finally {
      continueBtn.disabled = false;
    }
  }

  function getDimensionElements(dimensionId, scenario) {
    const target = dimensionElements[dimensionId];
    if (!target || scenario === 'conditional') return target;

    const screen = scenario === 'pause' ? pauseScreen : proceedScreen;
    const index = ['RD-01', 'RD-02', 'RD-03'].indexOf(dimensionId);
    const card = screen.querySelectorAll('.dimension-card')[index];
    if (!card) return null;
    return {
      key: target.key,
      status: card.querySelector('.status-chip'),
      copy: card.querySelector('.dimension-copy'),
      impact: card.querySelector('.dimension-impact')
    };
  }

  function relatedNextActionFor(dimension, finding) {
    if (dimension.status === 'Blocked') {
      return {title: `Resolve: ${finding.title}`, actionType: 'Resolve Blocker'};
    }
    if (dimension.status === 'Unknown' && finding.gate_critical) {
      return {
        title: `Verify: ${finding.title}`,
        actionType: 'Resolve Gate-critical Unknown'
      };
    }
    if (dimension.status === 'Warning') {
      return {title: `Mitigate: ${finding.title}`, actionType: 'Mitigate Warning'};
    }
    return {
      title: `Validate: ${finding.title}`,
      actionType: 'Minimum Validation'
    };
  }

  function applyDimension(dimension, assessment, scenario = 'conditional') {
    const target = getDimensionElements(dimension.dimension_id, scenario);
    if (!target) return;

    target.status.className = statusClass[dimension.status] || statusClass.Unknown;
    target.status.textContent = dimension.status;
    target.copy.textContent = dimension.summary;
    target.impact.textContent = `Gate impact · ${dimension.gate_impact}`;

    const finding = dimension.findings[0];
    const relatedNextAction = relatedNextActionFor(dimension, finding);
    // The detail screen renders only the decisive Finding. Its Evidence drawer
    // must therefore expose only Evidence explicitly attached to that same
    // Finding, never unrelated Evidence from another Finding in the Dimension.
    const inspectableEvidence = (finding.evidence || []).filter(hasInspectableEvidence);
    dimensionEvidenceByScenario[scenario][target.key] = inspectableEvidence;
    dimensionEvidenceIndexesByScenario[scenario][target.key] = 0;
    findingIdByDimension[target.key] = finding.finding_id;
    const detail = dimensionDetailDataByScenario[scenario][target.key];
    Object.assign(detail, {
      id: dimension.dimension_id,
      name: dimension.name,
      status: dimension.status,
      statusClass: statusClass[dimension.status] || statusClass.Unknown,
      statusCopy: dimension.summary,
      gateImpact: dimension.gate_impact,
      condition: `Condition · ${finding.condition}`,
      findingTitle: finding.title,
      findingSummary: finding.summary,
      findingType: `Finding type · ${finding.finding_type}`,
      gateCritical: finding.gate_critical,
      evidence: inspectableEvidence.length
        ? 'Evidence · Available'
        : 'Evidence · Not located in collected materials',
      findingImpact: `Gate impact · ${finding.readiness_impact}`,
      nextAction: relatedNextAction.title,
      nextActionType: relatedNextAction.actionType
    });

  }

  function applyEvaluationSignal(signal, conflicts) {
    const conflictCard = evaluationSignalBtn.closest('.signal-card');
    const conflictStatus = conflictCard.querySelector('.signal-status');
    const conflictSummary = conflictCard.querySelector('.signal-summary');
    activeApiEvaluationSignal = signal || null;
    activeApiConflicts = conflicts || [];
    activeApiConflictIndex = 0;

    if (!activeApiEvaluationSignal) {
      conflictStatus.className = 'signal-status unknown';
      conflictStatus.textContent = 'Unknown';
      conflictSummary.textContent =
        'Evaluation conflict evidence is not available for the current assessment.';
      evaluationSignalBtn.disabled = false;
      const sections = [...evaluationDrawerContent.querySelectorAll(':scope > .drawer-section')];
      sections[0].querySelector('.drawer-value').textContent = 'Unknown';
      sections[1].querySelector('.drawer-value').textContent = 'Other';
      sections[2].querySelector('.drawer-value').textContent = conflictSummary.textContent;
      sections[3].querySelector('.drawer-value').textContent =
        'No Gate impact can be inferred without evaluation evidence.';
      sections[4].querySelector('.drawer-value').textContent =
        'No evaluation evidence was returned by the current assessment.';
      return;
    }

    conflictCard.style.display = '';
    conflictStatus.className = `signal-status ${activeApiEvaluationSignal.status.toLowerCase()}`;
    conflictStatus.textContent = activeApiEvaluationSignal.status;
    conflictSummary.textContent = activeApiEvaluationSignal.summary;
    evaluationSignalBtn.disabled = false;
    evaluationSignalBtn.textContent = activeApiConflicts.length > 1
      ? `View ${activeApiConflicts.length} conflicts →`
      : 'View details →';
    evaluationEvidenceLink.textContent = activeApiConflicts.length > 1
      ? `Open conflict 1 of ${activeApiConflicts.length} →`
      : 'Open supporting Evidence →';

    const sections = [...evaluationDrawerContent.querySelectorAll(':scope > .drawer-section')];
    sections[0].querySelector('.drawer-value').textContent = activeApiEvaluationSignal.status;
    sections[1].querySelector('.drawer-value').textContent =
      activeApiEvaluationSignal.conflict_type;
    sections[2].querySelector('.drawer-value').textContent = activeApiEvaluationSignal.summary;
    sections[3].querySelector('.drawer-value').textContent = activeApiEvaluationSignal.gate_impact;
    sections[4].querySelector('.drawer-value').textContent = activeApiConflicts.length
      ? `${activeApiConflicts.length} conflict(s) preserved; each source pair remains inspectable.`
      : activeApiEvaluationSignal.evidence_refs[0]?.summary ||
        'The available evaluation evidence remains insufficient.';
  }

  function openApiConflictDrawer(conflict) {
    const [sourceA, sourceB] = conflict.sources;
    if (!hasInspectableEvidence(sourceA) || !hasInspectableEvidence(sourceB)) return;
    evidenceTitle.textContent = `${conflict.dimension_ids.join(' / ')} evidence conflict`;
    evidenceVerification.className = 'verification-chip';
    evidenceVerification.textContent = 'Conflicting';
    evidenceSummary.textContent = conflict.summary;
    evidenceSource.textContent = 'Multiple conflicting sources';
    evidenceLocation.textContent = [sourceA, sourceB]
      .map((source) => displayEvidenceLocation(source))
      .filter(Boolean)
      .join(' ↔ ');
    evidenceMaterialType.textContent = 'Evidence Conflict';
    evidenceConflict.textContent =
      'The sources disagree. ResearchOps has preserved both values for review.';
    evidenceConflict.classList.add('active');
    evidenceConflictATitle.textContent = `${sourceA.source} · ${displayEvidenceLocation(sourceA)}`;
    evidenceConflictACopy.textContent = sourceA.excerpt;
    evidenceConflictBTitle.textContent = `${sourceB.source} · ${displayEvidenceLocation(sourceB)}`;
    evidenceConflictBCopy.textContent = sourceB.excerpt;
    evidenceConflictCompare.classList.add('active');
    setEvidenceSourceUrl('');
    evidenceDrawer.classList.add('active');
    evidenceBackdrop.classList.add('active');
    evidenceDrawer.setAttribute('aria-hidden', 'false');
    activeFeedbackTarget = null;
  }

  function hasExactEvidenceLocation(evidence) {
    return Number.isInteger(evidence?.line_start) &&
      Number.isInteger(evidence?.line_end) &&
      evidence.line_start >= 1 &&
      evidence.line_end >= evidence.line_start;
  }

  function hasInspectableEvidence(evidence) {
    // A file-backed quote must show its verified line range.  Other real
    // Assessment evidence (for example a bounded public probe or user context)
    // can instead have a truthful non-file locator.  Do not hide it or replace
    // it with frozen-demo Evidence merely because it has no source lines.
    return Boolean(
      evidence &&
      typeof evidence.source === 'string' && evidence.source &&
      typeof evidence.location === 'string' && evidence.location &&
      typeof evidence.excerpt === 'string' && evidence.excerpt
    );
  }

  function exactEvidenceLocation(evidence) {
    if (!hasExactEvidenceLocation(evidence)) return '';
    const canonical = String(evidence.location || '').replace(
      /:lines?\s+\d+(?:-\d+)?$/i,
      ''
    );
    return `${canonical}:lines ${evidence.line_start}-${evidence.line_end}`;
  }

  function displayEvidenceLocation(evidence) {
    return exactEvidenceLocation(evidence) || String(evidence?.location || 'Locator unavailable');
  }

  function openApiDimensionEvidence(evidence, dimensionId) {
    if (!hasInspectableEvidence(evidence)) return;
    evidenceTitle.textContent = `${dimensionId} supporting evidence`;
    evidenceVerification.className = evidence.verification_status === 'Corroborated'
      ? 'verification-chip corroborated'
      : 'verification-chip';
    evidenceVerification.textContent = evidence.verification_status;
    evidenceSummary.textContent = evidence.summary;
    evidenceSource.textContent = evidence.source;
    evidenceLocation.textContent = displayEvidenceLocation(evidence);
    evidenceMaterialType.textContent = evidence.material_type || evidence.source_type;
    evidenceConflict.textContent = '';
    evidenceConflict.classList.remove('active');
    resetConflictComparison();
    setEvidenceSourceUrl(evidence.source_url ? String(evidence.source_url) : '');
    evidenceDrawer.classList.add('active');
    evidenceBackdrop.classList.add('active');
    evidenceDrawer.setAttribute('aria-hidden', 'false');
    activeFeedbackTarget = evidence.evidence_id
      ? {target_type: 'evidence', target_id: evidence.evidence_id}
      : null;
  }

  function displayedDimensionKey() {
    const dimensionId = String(detailDimensionId.textContent || '').trim().toUpperCase();
    return {
      'RD-01': 'rd01',
      'RD-02': 'rd02',
      'RD-03': 'rd03'
    }[dimensionId] || activeDimension;
  }

  function dimensionEvidenceState() {
    const scenario = dimensionEvidenceByScenario[activeScenario]
      ? activeScenario
      : 'conditional';
    const key = displayedDimensionKey();
    return {
      scenario,
      key,
      evidences: dimensionEvidenceByScenario[scenario]?.[key] || []
    };
  }

  function openApiEvaluationEvidence(signal, conflict) {
    if (conflict) {
      openApiConflictDrawer(conflict);
      return;
    }

    const evidence = signal.evidence_refs[0];
    if (!hasInspectableEvidence(evidence)) return;
    evidenceTitle.textContent = `${signal.conflict_type} evidence`;
    evidenceVerification.className = evidence.verification_status === 'Corroborated'
      ? 'verification-chip corroborated'
      : 'verification-chip';
    evidenceVerification.textContent = evidence.verification_status;
    evidenceSummary.textContent = evidence.summary;
    evidenceSource.textContent = evidence.source;
    evidenceLocation.textContent = displayEvidenceLocation(evidence);
    evidenceMaterialType.textContent = evidence.material_type || evidence.source_type;
    evidenceConflict.textContent = '';
    evidenceConflict.classList.remove('active');
    resetConflictComparison();
    setEvidenceSourceUrl(evidence.source_url ? String(evidence.source_url) : '');
    evidenceDrawer.classList.add('active');
    evidenceBackdrop.classList.add('active');
    evidenceDrawer.setAttribute('aria-hidden', 'false');
    activeFeedbackTarget = evidence.evidence_id
      ? {target_type: 'evidence', target_id: evidence.evidence_id}
      : null;
  }

  function applyResourceSignal(signal) {
    const resourceCard = resourceSignalBtn.closest('.signal-card');
    const status = resourceCard.querySelector('.signal-status');
    activeApiResourceSignal = signal || null;
    if (!signal) {
      status.className = 'signal-status unknown';
      status.textContent = 'Unknown';
      resourceCard.querySelector('.signal-summary').textContent =
        'Resource constraint evidence is not available for the current assessment.';
      const sections = [...resourceDrawerContent.querySelectorAll(':scope > .drawer-section')];
      sections[0].querySelector('.drawer-value').textContent = 'Unknown';
      sections[1].querySelector('.drawer-value').textContent =
        'No resource comparison is available.';
      sections[3].querySelector('.drawer-value').textContent =
        'No Gate impact can be inferred without resource evidence.';
      sections[4].querySelector('.drawer-value').textContent =
        'No resource evidence was returned by the current assessment.';
      return;
    }

    status.className = signal.status === 'Blocked'
      ? 'signal-status status-blocked'
      : `signal-status ${signal.status.toLowerCase()}`;
    status.textContent = signal.status;
    resourceCard.querySelector('.signal-summary').textContent = signal.summary;

    const sections = [...resourceDrawerContent.querySelectorAll(':scope > .drawer-section')];
    sections[0].querySelector('.drawer-value').textContent = signal.status;
    sections[1].querySelector('.drawer-value').textContent = signal.summary;
    const rows = [...resourceDrawerContent.querySelectorAll('.resource-row:not(.header)')];
    signal.items.forEach((item, index) => {
      const cells = rows[index]?.children;
      if (!cells) return;
      cells[0].textContent = item.resource;
      cells[0].className = 'resource-type';
      cells[1].textContent = item.current;
      cells[2].textContent = item.required;
    });
    sections[3].querySelector('.drawer-value').textContent = signal.gate_impact;
    sections[4].querySelector('.drawer-value').textContent = signal.evidence?.summary ||
      'No source-bound resource evidence was returned.';
  }

  function openApiResourceEvidence(signal) {
    const evidence = signal.evidence;
    if (!hasInspectableEvidence(evidence)) return;
    evidenceTitle.textContent = 'Resource constraint evidence';
    evidenceVerification.className = 'verification-chip';
    evidenceVerification.textContent = evidence.verification_status;
    evidenceSummary.textContent = evidence.summary;
    evidenceSource.textContent = evidence.source;
    evidenceLocation.textContent = displayEvidenceLocation(evidence);
    evidenceMaterialType.textContent = evidence.material_type || evidence.source_type;
    evidenceConflict.textContent = '';
    evidenceConflict.classList.remove('active');
    resetConflictComparison();
    setEvidenceSourceUrl(evidence.source_url ? String(evidence.source_url) : '');
    evidenceDrawer.classList.add('active');
    evidenceBackdrop.classList.add('active');
    evidenceDrawer.setAttribute('aria-hidden', 'false');
    activeFeedbackTarget = evidence.evidence_id
      ? {target_type: 'evidence', target_id: evidence.evidence_id}
      : null;
  }

  function applyCompletedAssessment(assessment) {
    const scenario = 'conditional';

    assessment.dimensions.forEach((dimension) =>
      applyDimension(dimension, assessment, scenario)
    );

    const primaryRiskDimension = assessment.dimensions.find(
      (dimension) => dimension.status !== 'Ready'
    );
    const primaryRiskFinding = primaryRiskDimension?.findings?.[0];
    overviewScreen.querySelector('.gate-value').textContent = assessment.overall_gate;
    overviewScreen.querySelector('.gate-reason-text').textContent = assessment.main_risk;
    overviewScreen.querySelector('.focus-title').textContent = assessment.main_risk;
    overviewScreen.querySelector('.focus-copy').textContent =
      primaryRiskFinding?.summary || 'Review the available evidence before continuing.';
    overviewScreen.querySelector('.focus-meta .meta-chip').textContent = primaryRiskFinding
      ? `${primaryRiskFinding.gate_critical ? 'Gate-critical ' : ''}${primaryRiskDimension.status}`
      : 'Evidence-backed assessment';
    overviewScreen.querySelector('.next-action-title').textContent =
      assessment.first_next_action.title;
    overviewScreen.querySelector('.next-action-copy').textContent =
      assessment.first_next_action.description;
    overviewScreen.querySelector('.next-action-type').textContent =
      `Action type · ${assessment.first_next_action.action_type}`;

    applyResourceSignal(assessment.resource_signal);
    applyEvaluationSignal(
      assessment.evaluation_signal,
      (assessment.conflicts || []).filter(
        (conflict) => conflict.condition_key.startsWith('evaluation.')
      )
    );
    activeScenario = 'conditional';
    showScreen('overview');
  }

  function firstBlockingEvidence(assessment) {
    if (assessment.resource_signal?.status === 'Blocked') {
      return assessment.resource_signal.evidence?.summary || assessment.resource_signal.summary;
    }
    const blocked = assessment.dimensions.find((dimension) => dimension.status === 'Blocked');
    return blocked?.findings?.[0]?.evidence?.[0]?.summary || blocked?.summary || assessment.main_risk;
  }

  function applyPauseAssessment(assessment) {
    pauseScreen.querySelector('.pause-reason-text').textContent = assessment.main_risk;
    const blocker = pauseScreen.querySelector('.pause-blocker');
    blocker.querySelector('.pause-section-title').textContent = assessment.main_risk;
    blocker.querySelector('.pause-section-copy').textContent =
      'This is a confirmed blocking condition, not a missing-information Unknown.';
    blocker.querySelector('.pause-evidence').textContent =
      `Blocking evidence · ${firstBlockingEvidence(assessment)}`;

    const action = pauseScreen.querySelector('.pause-action');
    action.querySelector('.pause-section-title').textContent = assessment.first_next_action.title;
    action.querySelector('.pause-section-copy').textContent =
      assessment.first_next_action.description;
    action.querySelector('.pause-action-type').textContent =
      `Action type · ${assessment.first_next_action.action_type}`;

    activeScenario = 'pause';
    showScreen('pause');
  }

  function applyProceedAssessment(assessment) {
    proceedScreen.querySelector('.proceed-reason-text').textContent = assessment.main_risk;
    const summary = proceedScreen.querySelector('.proceed-summary');
    summary.querySelector('.proceed-section-title').textContent = assessment.main_risk;
    summary.querySelector('.proceed-section-copy').textContent =
      'Positive evidence remains inspectable even when the current status is Ready.';
    summary.querySelector('.proceed-signal').textContent =
      `Additional Signals · ${assessment.resource_signal?.summary || 'No resource signal available.'} ` +
      `${assessment.evaluation_signal?.summary || 'No evaluation signal available.'}`;

    const action = proceedScreen.querySelector('.proceed-action');
    action.querySelector('.proceed-section-title').textContent = assessment.first_next_action.title;
    action.querySelector('.proceed-section-copy').textContent =
      assessment.first_next_action.description;
    action.querySelector('.proceed-action-type').textContent =
      `Action type · ${assessment.first_next_action.action_type}`;

    activeScenario = 'proceed';
    showScreen('proceed');
  }

  function applyPartialResult(assessment) {
    partialResult.querySelector('.partial-copy').textContent = assessment.main_risk;
    renderTechnicalTrace(document.getElementById('partial-trace'), assessment);
    const rows = [...partialResult.querySelectorAll('.partial-row')];
    rows[0].querySelector('.partial-row-state').textContent = 'Available';
    rows[1].querySelector('.partial-row-state').textContent =
      assessment.dimensions.find((dimension) => dimension.dimension_id === 'RD-02')?.status ||
      analysisStateLabel[
        assessment.dimensions.find((dimension) => dimension.dimension_id === 'RD-02')?.analysis_state
      ] ||
      'Incomplete';
    rows[2].querySelector('.partial-row-state').textContent = 'Still processing';
    partialContinue.textContent = 'Continue processing';
    showScreen('partialResult');
  }

  function applyAcquisitionFailure(assessment, stage = 'assessment') {
    activeAcquisitionFailure = assessment;
    activeFailureStage = stage;
    acquisitionFailure.querySelector('.failure-title').textContent =
      assessment.failure_title || 'Repository material acquisition failed';
    acquisitionFailure.querySelector('.failure-copy').textContent = assessment.main_risk;
    acquisitionFailure.querySelector('.failure-detail-title').textContent =
      assessment.failure_detail_title || 'Public Repository material acquisition';
    acquisitionFailure.querySelector('.failure-detail-copy').textContent =
      assessment.first_next_action.description;
    renderTechnicalTrace(document.getElementById('failure-trace'), assessment);
    failureRetry.textContent = 'Retry →';
    failureSnapshot.textContent = 'Back to Task Setup';
    failureManual.textContent = 'Change target';
    showScreen('acquisitionFailure');
  }

  function applyGateUnavailableAssessment(assessment) {
    gateNotAvailable.querySelector('.gate-na-title').textContent = 'Assessment Incomplete';
    gateNotAvailable.querySelector('.gate-na-copy').textContent = assessment.main_risk;
    renderTechnicalTrace(document.getElementById('gate-na-trace'), assessment);

    const rows = [...gateNotAvailable.querySelectorAll('.gate-na-row')];
    assessment.dimensions.forEach((dimension, index) => {
      rows[index].querySelector('.gate-na-row-copy').textContent = dimension.summary;
      const state = rows[index].querySelector('.gate-na-row-state');
      state.className = 'gate-na-row-state';
      state.textContent = dimension.status || analysisStateLabel[dimension.analysis_state] || 'Not started';
    });

    gateNaContinue.disabled = ![
      'configuration_required',
      'model_unavailable',
      'invalid_model_response',
      'manual_input_required'
    ].includes(assessment.analysis_state);
    gateNaContinue.textContent = assessment.analysis_state === 'manual_input_required'
      ? 'Provide manual input'
      : assessment.first_next_action.title;
    showScreen('gateNotAvailable');
  }

  function renderTechnicalTrace(element, assessment) {
    if (!element) return;
    const events = (assessment.audit_trail || []).filter((event) =>
      event.actor === 'ai' || event.actor === 'connector'
    );
    const event = [...events].reverse().find((item) =>
      item.outcome === 'failed' ||
      item.outcome === 'partial' ||
      item.stage === 'research_tool_execution'
    ) || events.at(-1);
    if (!event) {
      element.hidden = true;
      element.textContent = '';
      return;
    }
    const refs = event.refs || [];
    const round = refs.find((ref) => ref.startsWith('research_round:'));
    const sources = refs.filter((ref) => ref.startsWith('source:')).slice(0, 3);
    const stageLabel = {
      analysis_failure: {
        model_unavailable: 'Model provider unavailable',
        invalid_model_response: 'Invalid structured model output',
        configuration_required: 'Model configuration required',
        acquisition_failure: 'Material acquisition failed',
        partial_material_acquisition: 'Partial material acquisition',
        tool_failure: 'Deterministic tool acquisition failed',
        human_confirmation_required: 'Human confirmation required',
        authorization_required: 'Authorization required',
        manual_input_required: 'Manual input required'
      }[refs.find((ref) => ref.startsWith('analysis_state:'))?.slice(15)] || 'Analysis failed',
      research_tool_execution: 'Deterministic tool acquisition',
      material_acquisition: 'Partial material acquisition'
    }[event.stage] || event.stage;
    const metadata = [
      `Diagnostic: ${stageLabel}`,
      event.provider_request_id ? `Provider request: ${event.provider_request_id}` : null,
      Number.isInteger(event.duration_ms) ? `Duration: ${event.duration_ms} ms` : null,
      round ? `Round: ${round.split(':')[1]}` : null,
      sources.length ? `Sources: ${sources.map((ref) => ref.slice(7)).join(', ')}` : null
    ].filter(Boolean);
    element.textContent = metadata.join(' · ');
    element.hidden = metadata.length === 0;
  }

  async function readEnvironmentInput() {
    if (selectedMode === 'manual') {
      return document.querySelector('.manual-textarea').value.trim() || null;
    }
    if (selectedMode === 'snapshot') {
      const file = document.getElementById('snapshot-file').files[0];
      if (!file) return null;
      if (file.size > 50000) {
        throw new Error('Environment snapshot must be 50 KB or smaller for this MVP.');
      }
      return (await file.text()).slice(0, 50000);
    }
    return null;
  }

  function updateProcessingProgress(job) {
    const rows = [...processing.querySelectorAll('.processing-row')];
    const [label, state] = progressPhaseCopy[job.phase] || [job.phase, 'Processing'];
    processingCopy.textContent = label;

    const materialCount = job.material_source_count;
    const evidenceCount = job.evidence_candidate_count;
    const validatedCount = job.validated_evidence_count;
    const materialPreview = (job.material_titles || []).slice(0, 3).join(', ');
    const materialLabel = materialCount === null || materialCount === undefined
      ? 'Reviewing linked target materials'
      : `Material scope: ${materialCount} source${materialCount === 1 ? '' : 's'}` +
        (materialPreview ? ` · ${materialPreview}` : '');
    const evidenceLabel = evidenceCount === null || evidenceCount === undefined
      ? 'AI Evidence, Conflict and Finding analysis'
      : `Evidence candidates: ${evidenceCount}; Rule-validated: ${validatedCount ?? 0}`;

    if (rows[0]) {
      rows[0].querySelector('.processing-row-left div:last-child').textContent = label;
      rows[0].querySelector('.processing-state').textContent = state;
    }
    if (rows[1]) {
      rows[1].querySelector('.processing-row-left div:last-child').textContent = materialLabel;
      rows[1].querySelector('.processing-state').textContent = materialCount === null || materialCount === undefined
        ? 'Waiting'
        : 'Available';
    }
    if (rows[2]) {
      rows[2].querySelector('.processing-row-left div:last-child').textContent = evidenceLabel;
      rows[2].querySelector('.processing-state').textContent = evidenceCount === null || evidenceCount === undefined
        ? 'Waiting'
        : validatedCount === null || validatedCount === undefined
          ? 'AI complete'
          : 'Rule checked';
    }
    processingEnvLabel.textContent = label;
    processingEnvState.textContent = state;
  }

  async function waitForAssessmentJob(jobId, runId) {
    while (runId === activeAssessmentRun) {
      const job = await getJson(`${assessmentJobEndpoint}/${encodeURIComponent(jobId)}`);
      updateProcessingProgress(job);
      if (job.state === 'completed') return job.assessment;
      if (job.state === 'failed') {
        const error = new Error(job.error_message || 'Assessment processing failed.');
        error.code = 'ASSESSMENT_JOB_FAILED';
        throw error;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 750));
    }
    return null;
  }

  function renderAssessment(assessment) {
    if (!assessment) return;
    // Never leave an open drawer pointing at Evidence from the previous
    // Assessment revision after feedback-triggered reassessment.
    evidenceDrawer.classList.remove('active');
    evidenceBackdrop.classList.remove('active');
    evidenceDrawer.setAttribute('aria-hidden', 'true');
    latestAssessment = assessment;
    if (latestAssessmentId !== assessment.assessment_id) {
      finalDecisionForm.reset();
      finalDecisionStatus.textContent = '';
    }
    latestAssessmentId = assessment.assessment_id;
    syncFinalDecisionVisibility();
    activeFeedbackTarget = null;
    assessmentHistory.hidden = true;
    assessmentHistoryContent.replaceChildren();

    if (assessment.status === 'partial' || assessment.overall_gate === null) {
      if (assessment.analysis_state === 'acquisition_failure') {
        applyAcquisitionFailure(assessment);
      } else if (assessment.analysis_state === 'partial_result') {
        applyPartialResult(assessment);
      } else if (assessment.gate_available === false || assessment.overall_gate === null) {
        applyGateUnavailableAssessment(assessment);
      } else {
        applyCompletedAssessment(assessment);
      }
    } else {
      applyCompletedAssessment(assessment);
    }
  }

  startAssessmentProcessing = async function startApiAssessmentProcessing() {
    const runId = ++activeAssessmentRun;
    latestAssessment = null;
    latestAssessmentId = null;
    finalDecisionCard.hidden = true;
    finalDecisionStatus.textContent = '';
    processingCopy.textContent = 'Starting the real AI → Rule assessment workflow.';
    processingEnvLabel.textContent = 'Assessment queued';
    processingEnvState.textContent = 'Waiting';
    showScreen('processing');

    try {
      const environmentInput = await readEnvironmentInput();
      const job = await postJson(assessmentJobEndpoint, {
        target_type: currentTargetType(),
        target_entry: targetEntryEl.value.trim(),
        resolved_target: resolvedTargetForAssessment,
        environment_mode: selectedMode,
        environment_authorized: selectedMode === 'readonly' && environmentAuthorized,
        environment_authorization_token:
          selectedMode === 'readonly' ? environmentAuthorizationToken : null,
        environment_input: environmentInput
      });
      updateProcessingProgress(job);
      const assessment = await waitForAssessmentJob(job.job_id, runId);
      if (runId === activeAssessmentRun) renderAssessment(assessment);
    } catch (error) {
      if (runId !== activeAssessmentRun) return;
      if (error.code === 'ENVIRONMENT_AUTHORIZATION_INVALID') {
        environmentAuthorized = false;
        environmentAuthorizationToken = null;
        showScreen('auth');
        return;
      }
      applyAcquisitionFailure({
        failure_title: 'Assessment processing failed',
        failure_detail_title: 'AI → Rule assessment workflow',
        main_risk: 'The Assessment service could not produce a validated result.',
        first_next_action: {
          description: `${error.message} Retry when the service is available.`
        }
      });
    }
  };

  function assessmentEvidence(assessment) {
    const evidence = (assessment.dimensions || []).flatMap((dimension) =>
      (dimension.findings || []).flatMap((finding) => finding.evidence || [])
    );
    evidence.push(
      ...(assessment.conflicts || []).flatMap((conflict) => conflict.sources || []),
      ...(assessment.evaluation_signal?.evidence_refs || [])
    );
    if (assessment.resource_signal?.evidence) evidence.push(assessment.resource_signal.evidence);
    return evidence;
  }

  async function feedbackTargetForCurrentContext() {
    const assessment = await getJson(
      `/api/v1/assessments/${encodeURIComponent(latestAssessmentId)}`
    );
    latestAssessment = assessment;

    if (feedbackContext === 'evidence') {
      const evidence = assessmentEvidence(assessment);
      const targetId = activeFeedbackTarget?.target_type === 'evidence'
        ? activeFeedbackTarget.target_id
        : null;
      // Never infer identity from rendered labels: two Evidence records can
      // share a source and locator across Findings or revisions. Feedback must
      // target the exact Evidence ID returned by the current Assessment.
      const retained = targetId && evidence.some(
        (item) => item.evidence_id === targetId
      );
      return retained
        ? {target_type: 'evidence', target_id: targetId}
        : null;
    }

    const dimensionIndex = dimensionKeys.indexOf(activeDimension);
    const dimension = assessment.dimensions?.[dimensionIndex];
    const finding = dimension?.findings?.find(
      (item) => item.finding_id === findingIdByDimension[activeDimension]
    ) || dimension?.findings?.find(
      (item) => item.title === detailFindingTitle.textContent
    ) || dimension?.findings?.[0];
    return finding
      ? {target_type: 'finding', target_id: finding.finding_id}
      : null;
  }

  function feedbackPayload(target) {
    const comment = feedbackTextarea.value.trim();
    const actionByUiType = {
      confirm: 'accept',
      question: 'question',
      correct: 'correct',
      evidence: 'supplement'
    };
    const payload = {
      ...target,
      action: actionByUiType[selectedFeedbackType],
      comment: comment || null
    };
    if (selectedFeedbackType === 'correct' || selectedFeedbackType === 'evidence') {
      payload.source_submission = {
        material_type: 'Other',
        title: selectedFeedbackType === 'correct' ? 'User correction' : 'User-supplied Evidence',
        source_path: `user/assessment-feedback-${Date.now()}.txt`,
        content: comment
      };
    }
    return payload;
  }

  dimensionFeedbackBtn.addEventListener('click', (event) => {
    // Replace the frozen prototype listener: only a Finding returned by the
    // current Assessment can open a production feedback panel.
    event.preventDefault();
    event.stopImmediatePropagation();
    activeFeedbackTarget = null;
    if (!latestAssessmentId || !findingIdByDimension[activeDimension]) return;
    openFeedbackPanel('finding');
  }, true);

  evidenceFeedbackBtn.addEventListener('click', (event) => {
    // The source drawer may show non-file Evidence, but feedback is possible
    // only when the current revision supplied a stable Evidence ID.
    event.preventDefault();
    event.stopImmediatePropagation();
    if (activeFeedbackTarget?.target_type !== 'evidence') return;
    openFeedbackPanel('evidence');
  }, true);

  assessmentHistoryBtn.addEventListener('click', (event) => {
    event.preventDefault();
    void openAssessmentHistory();
  });

  assessmentHistoryCloseBtn.addEventListener('click', () => {
    assessmentHistory.hidden = true;
  });

  feedbackSubmit.addEventListener('click', async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    feedbackError.classList.remove('active');
    feedbackSuccess.classList.remove('active');

    if (!selectedFeedbackType) {
      feedbackError.textContent = 'Choose a feedback type first.';
      feedbackError.classList.add('active');
      return;
    }
    if (selectedFeedbackType !== 'confirm' && !feedbackTextarea.value.trim()) {
      feedbackError.textContent = 'Add a short note before submitting this feedback.';
      feedbackError.classList.add('active');
      feedbackTextarea.focus();
      return;
    }
    if (!latestAssessmentId) {
      feedbackError.textContent = 'Run a real Assessment before submitting feedback.';
      feedbackError.classList.add('active');
      return;
    }
    let target;
    try {
      target = await feedbackTargetForCurrentContext();
    } catch (error) {
      feedbackError.textContent = `The current Assessment could not be refreshed: ${error.message}`;
      feedbackError.classList.add('active');
      return;
    }
    if (!target) {
      feedbackError.textContent = 'This Finding or Evidence is not part of the current Assessment. Rerun the Assessment first.';
      feedbackError.classList.add('active');
      return;
    }

    feedbackSubmit.disabled = true;
    feedbackSubmit.textContent = selectedFeedbackType === 'confirm' || selectedFeedbackType === 'question'
      ? 'Recording feedback…'
      : 'Reassessing with feedback…';
    try {
      const response = await postJson(
        `/api/v1/assessments/${encodeURIComponent(latestAssessmentId)}/feedback`,
        feedbackPayload(target)
      );
      if (response.reassessment_performed) {
        renderAssessment(response.assessment);
        feedbackSuccess.textContent = 'Feedback was validated and the Assessment was recalculated.';
      } else if (response.reassessment_state === 'not_required') {
        feedbackSuccess.textContent = 'Feedback recorded without changing the Rule decision.';
      } else {
        feedbackError.textContent = response.reassessment_detail || analysisStateLabel[response.reassessment_state] ||
          'Reassessment could not produce a validated result. Your feedback was retained.';
        feedbackError.classList.add('active');
        return;
      }
      feedbackSuccess.classList.add('active');
      feedbackSubmit.textContent = 'Feedback submitted ✓';
    } catch (error) {
      feedbackError.textContent = `Feedback could not be submitted: ${error.message}`;
      feedbackError.classList.add('active');
      feedbackSubmit.textContent = 'Submit feedback';
    } finally {
      feedbackSubmit.disabled = false;
    }
  }, true);

  continueBtn.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    void resolveSubmittedTarget();
  }, true);

  targetConfirmBtn.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const index = Number.parseInt(selectedTargetCandidate, 10);
    const candidate = latestTargetResolution?.candidates[index];
    if (!candidate) {
      showScreen('setup');
      showSetupError('The selected target candidate is no longer available. Resolve the entry again.');
      return;
    }
    showResolvedTarget(candidate.resolved_target);
  }, true);

  skipConfirmProceed.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    closeSkipConfirmation();
    applyGateUnavailableAssessment({
      main_risk: 'The target identity is still ambiguous, so no bounded material set can be analyzed.',
      dimensions: ['RD-01', 'RD-02', 'RD-03'].map(() => ({
        analysis_state: 'conflict',
        summary: 'Analysis has not started because the target candidate was not confirmed.'
      })),
      first_next_action: {title: 'Return and confirm a target candidate'}
    });
  }, true);

  evaluationEvidenceLink.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (activeApiEvaluationSignal) {
      const conflict = activeApiConflicts[activeApiConflictIndex] || null;
      openApiEvaluationEvidence(activeApiEvaluationSignal, conflict);
      if (activeApiConflicts.length > 1) {
        activeApiConflictIndex = (activeApiConflictIndex + 1) % activeApiConflicts.length;
        evaluationEvidenceLink.textContent =
          `Open conflict ${activeApiConflictIndex + 1} of ${activeApiConflicts.length} →`;
      }
    }
  }, true);

  resourceEvidenceLink.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (activeApiResourceSignal) {
      openApiResourceEvidence(activeApiResourceSignal);
    }
  }, true);

  document.getElementById('dimension-view-evidence').addEventListener('click', (event) => {
    // Always suppress the frozen demo listener. If the real Assessment has no
    // Evidence, opening its static placeholder would create a feedback target
    // that cannot belong to the retained Assessment revision.
    event.preventDefault();
    event.stopImmediatePropagation();
    const {scenario, key, evidences} = dimensionEvidenceState();
    if (!evidences.length) {
      event.currentTarget.disabled = true;
      event.currentTarget.setAttribute('aria-disabled', 'true');
      return;
    }

    const index = dimensionEvidenceIndexesByScenario[scenario][key] || 0;
    const detail = dimensionDetailDataByScenario[scenario][key];
    openApiDimensionEvidence(evidences[index], detail.id);
    dimensionEvidenceIndexesByScenario[scenario][key] =
      (index + 1) % evidences.length;
  }, true);

  dimensionKeys.forEach((key) => {
    document.getElementById(`${key}-view-details`).addEventListener('click', () => {
      const hasRealEvidence = Boolean(
        dimensionEvidenceByScenario.conditional?.[key]?.length
      );
      const viewEvidence = document.getElementById('dimension-view-evidence');
      viewEvidence.disabled = !hasRealEvidence;
      viewEvidence.setAttribute('aria-disabled', String(!hasRealEvidence));
    });
  });

  authorizeBtn.addEventListener('click', async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    authorizeBtn.disabled = true;
    try {
      const grant = await postJson(environmentAuthorizationEndpoint, {});
      environmentAuthorizationToken = grant.authorization_token;
      environmentAuthorized = true;
      selectedMode = 'readonly';
      await startAssessmentProcessing();
    } catch (error) {
      environmentAuthorized = false;
      environmentAuthorizationToken = null;
      applyAcquisitionFailure({
        main_risk: 'The local service could not record read-only environment authorization.',
        first_next_action: {description: `${error.message} Return and authorize again.`}
      });
    } finally {
      authorizeBtn.disabled = false;
    }
  }, true);

  denyAuthorizeBtn.addEventListener('click', () => {
    environmentAuthorized = false;
    environmentAuthorizationToken = null;
  }, true);

  partialContinue.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    void startAssessmentProcessing();
  }, true);

  failureRetry.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (activeFailureStage === 'target_resolution') {
      void resolveSubmittedTarget();
    } else {
      void startAssessmentProcessing();
    }
  }, true);

  gateNaContinue.addEventListener('click', (event) => {
    if (gateNaContinue.disabled) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (latestAssessment?.analysis_state === 'manual_input_required') {
      history.replaceState(null, '', location.pathname);
      showScreen('setup');
      selectEnvironmentMode('manual');
      window.setTimeout(() => {
        const panel = document.getElementById('detail-manual');
        if (panel) panel.scrollIntoView({behavior: 'smooth', block: 'center'});
      }, 120);
      return;
    }
    void startAssessmentProcessing();
  }, true);

  failureSnapshot.addEventListener('click', (event) => {
    if (!activeAcquisitionFailure) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    showScreen('setup');
  }, true);

  failureManual.addEventListener('click', (event) => {
    if (!activeAcquisitionFailure) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    showScreen('setup');
    targetEntryEl.focus();
  }, true);

  targetTypeEl.addEventListener('change', resetResolvedTarget);
  targetEntryEl.addEventListener('input', resetResolvedTarget);

  const staticDemoHashes = new Set([
    '#target-identified',
    '#authorization-denied',
    '#partial-result',
    '#acquisition-failure',
    '#conflict',
    '#gate-not-available',
    '#pause',
    '#proceed'
  ]);
  if (staticDemoHashes.has(window.location.hash)) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    showScreen('setup');
  }
})();
