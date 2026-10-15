const signalDrawer = document.getElementById('signal-drawer');
  const signalBackdrop = document.getElementById('signal-backdrop');
  const signalDrawerClose = document.getElementById('signal-drawer-close');
  const resourceSignalBtn = document.getElementById('resource-signal-btn');
  const evaluationSignalBtn = document.getElementById('evaluation-signal-btn');
  const resourceDrawerContent = document.getElementById('resource-drawer-content');
  const evaluationDrawerContent = document.getElementById('evaluation-drawer-content');
  const drawerTitle = document.getElementById('drawer-title');

  function openSignalDrawer(type){
    const resource = type === 'resource';
    resourceDrawerContent.style.display = resource ? 'block' : 'none';
    evaluationDrawerContent.style.display = resource ? 'none' : 'block';
    drawerTitle.textContent = resource ? 'Resource Constraint' : 'Evaluation Conflict';
    signalDrawer.classList.add('active');
    signalBackdrop.classList.add('active');
    signalDrawer.setAttribute('aria-hidden','false');
  }

  function closeSignalDrawer(){
    signalDrawer.classList.remove('active');
    signalBackdrop.classList.remove('active');
    signalDrawer.setAttribute('aria-hidden','true');
  }

  resourceSignalBtn.addEventListener('click', () => openSignalDrawer('resource'));
  evaluationSignalBtn.addEventListener('click', () => openSignalDrawer('evaluation'));
  signalDrawerClose.addEventListener('click', closeSignalDrawer);
  signalBackdrop.addEventListener('click', closeSignalDrawer);

  const resourceEvidenceLink = document.getElementById('resource-evidence-link');
  const evaluationEvidenceLink = document.getElementById('evaluation-evidence-link');

  resourceEvidenceLink.addEventListener('click', openResourceEvidenceDrawer);
  evaluationEvidenceLink.addEventListener('click', openConflictEvidenceDrawer);

  const contextToggle = document.getElementById('context-toggle');
  const contextPanel = document.getElementById('context-panel');
  const contextToggleIcon = document.getElementById('context-toggle-icon');

  contextToggle.addEventListener('click', () => {
    const open = contextPanel.classList.toggle('active');
    contextToggle.setAttribute('aria-expanded', String(open));
    contextToggleIcon.textContent = open ? '−' : '＋';
  });

  const setup = document.getElementById('screen-setup');
  const auth = document.getElementById('screen-auth');
  const authDenied = document.getElementById('screen-auth-denied');
  const targetConfirm = document.getElementById('screen-target-confirm');
  const targetIdentified = document.getElementById('screen-target-identified');
  const modes = [...document.querySelectorAll('.mode')];
  const continueBtn = document.getElementById('continue-btn');
  const backBtn = document.getElementById('back-btn');
  let selectedMode = 'readonly';

  const processing = document.getElementById('screen-processing');
  const partialResult = document.getElementById('screen-partial-result');
  const acquisitionFailure = document.getElementById('screen-acquisition-failure');
  const conflictScreen = document.getElementById('screen-conflict');
  const gateNotAvailable = document.getElementById('screen-gate-not-available');
  const pauseScreen = document.getElementById('screen-pause');
  const proceedScreen = document.getElementById('screen-proceed');
  const overview = document.getElementById('screen-overview');
  const dimensionDetail = document.getElementById('screen-dimension-detail');
  const overviewBackBtn = document.getElementById('overview-back-btn');

  function showScreen(type){
    setup.classList.toggle('active', type === 'setup');
    targetConfirm.classList.toggle('active', type === 'targetConfirm');
    targetIdentified.classList.toggle('active', type === 'targetIdentified');
    auth.classList.toggle('active', type === 'auth');
    authDenied.classList.toggle('active', type === 'authDenied');
    processing.classList.toggle('active', type === 'processing');
    partialResult.classList.toggle('active', type === 'partialResult');
    acquisitionFailure.classList.toggle('active', type === 'acquisitionFailure');
    conflictScreen.classList.toggle('active', type === 'conflict');
    gateNotAvailable.classList.toggle('active', type === 'gateNotAvailable');
    pauseScreen.classList.toggle('active', type === 'pause');
    proceedScreen.classList.toggle('active', type === 'proceed');
    overview.classList.toggle('active', type === 'overview');
    dimensionDetail.classList.toggle('active', type === 'dimensionDetail');
    window.scrollTo({top:0,behavior:'smooth'});
  }

  const targetTypeEl = document.getElementById('target-type');
  const targetEntryEl = document.getElementById('target-entry');
  const setupError = document.getElementById('setup-error');
  const processingCopy = document.getElementById('processing-copy');
  const processingEnvLabel = document.getElementById('processing-env-label');
  const processingEnvState = document.getElementById('processing-env-state');

  let targetResolved = false;
  let targetDeferred = false;
  let targetResolvedName = '';
  let targetResolvedTypeLabel = '';
  let selectedTargetCandidate = 'a';

  function showSetupError(message){
    setupError.textContent = message;
    setupError.classList.add('active');
  }

  function clearSetupError(){
    setupError.textContent = '';
    setupError.classList.remove('active');
  }

  function targetNeedsConfirmation(){
    // Prototype branch used to demonstrate the conditional confirmation flow.
    // Paper-title entries simulate a potentially ambiguous title match.
    return targetTypeEl.value === 'paper' && !targetResolved && !targetDeferred;
  }

  function prepareTargetConfirmation(){
    const entry = targetEntryEl.value.trim() || 'Provided paper title';
    selectedTargetCandidate = 'a';
    document.getElementById('candidate-a-name').textContent = entry;
    document.getElementById('candidate-b-name').textContent = entry + ' — related project match';
    candidateA.classList.add('active');
    candidateB.classList.remove('active');
    showScreen('targetConfirm');
  }

  const identifiedTargetName = document.getElementById('identified-target-name');
  const identifiedTargetType = document.getElementById('identified-target-type');
  const identifiedSourceEntry = document.getElementById('identified-source-entry');
  const identifiedMaterialsSummary = document.getElementById('identified-materials-summary');
  const identifiedBack = document.getElementById('identified-back');
  const identifiedContinue = document.getElementById('identified-continue');

  function getTargetDisplayName(){
    const entry = targetEntryEl.value.trim();
    if(targetTypeEl.value === 'repository'){
      try{
        const url = new URL(entry);
        const cleanPath = url.pathname.replace(/^\/|\/$/g,'');
        return cleanPath || entry;
      }catch(e){
        return entry;
      }
    }
    return entry;
  }

  function prepareTargetIdentified(){
    const typeLabel = targetResolvedTypeLabel || targetTypeEl.options[targetTypeEl.selectedIndex].textContent;
    identifiedTargetName.textContent = targetResolvedName || getTargetDisplayName();
    identifiedTargetType.textContent = typeLabel + ' · resolution status: Identified';
    identifiedSourceEntry.textContent = targetEntryEl.value.trim();
    identifiedMaterialsSummary.textContent =
      'Primary target resolved from the submitted entry. Related public materials will be linked during the assessment when available.';
    showScreen('targetIdentified');
  }

  identifiedBack.addEventListener('click', () => showScreen('setup'));
  identifiedContinue.addEventListener('click', () => continueAfterTargetResolution());

  function configureOverviewForEnvironment(){
    const rd02Status = document.getElementById('rd02-status');
    const rd02Copy = document.getElementById('rd02-copy');
    const rd02Impact = document.getElementById('rd02-impact');

    if(selectedMode === 'later'){
      rd02Status.className = 'status-chip status-unknown';
      rd02Status.textContent = 'Unknown';
      rd02Copy.textContent = 'Environment information was not provided, so dependency readiness cannot be fully assessed.';
      rd02Impact.textContent = 'Gate impact · Depends on unresolved environment evidence';
    }else{
      rd02Status.className = 'status-chip status-warning';
      rd02Status.textContent = 'Warning';
      rd02Copy.textContent = 'The environment is usable for assessment, with a known compatibility risk that needs validation.';
      rd02Impact.textContent = 'Gate impact · Non-blocking risk';
    }
  }

  const partialBackSetup = document.getElementById('partial-back-setup');
  const partialContinue = document.getElementById('partial-continue');

  partialBackSetup.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
  });

  partialContinue.addEventListener('click', () => {
    showScreen('processing');
    setTimeout(() => showScreen('overview'), 1200);
  });

  const failureRetry = document.getElementById('failure-retry');
  const failureSnapshot = document.getElementById('failure-snapshot');
  const failureManual = document.getElementById('failure-manual');

  failureRetry.addEventListener('click', () => {
    selectedMode = 'readonly';
    showScreen('processing');
    processingCopy.textContent = 'ResearchOps is retrying read-only environment acquisition and rebuilding the assessment.';
    processingEnvLabel.textContent = 'Retrying environment acquisition';
    processingEnvState.textContent = 'Processing';
    setTimeout(() => showScreen('overview'), 1200);
  });

  failureSnapshot.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
    selectEnvironmentMode('snapshot');
    setTimeout(() => {
      const panel = document.getElementById('detail-snapshot');
      if(panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  failureManual.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
    selectEnvironmentMode('manual');
    setTimeout(() => {
      const panel = document.getElementById('detail-manual');
      if(panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  const conflictBackSetup = document.getElementById('conflict-back-setup');
  const conflictReview = document.getElementById('conflict-review');

  conflictBackSetup.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
  });

  conflictReview.addEventListener('click', () => {
    openConflictEvidenceDrawer();
  });

  const gateNaBackSetup = document.getElementById('gate-na-back-setup');
  const gateNaContinue = document.getElementById('gate-na-continue');

  gateNaBackSetup.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
  });

  gateNaContinue.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('processing');
    processingCopy.textContent = 'ResearchOps is completing the remaining readiness analysis before aggregating the Overall Gate.';
    processingEnvLabel.textContent = 'Completing remaining readiness analysis';
    processingEnvState.textContent = 'Processing';
    setTimeout(() => showScreen('overview'), 1200);
  });

  const pauseBackSetup = document.getElementById('pause-back-setup');

  pauseBackSetup.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
  });

  const proceedBackSetup = document.getElementById('proceed-back-setup');

  proceedBackSetup.addEventListener('click', () => {
    history.replaceState(null, '', location.pathname);
    showScreen('setup');
  });

  function startAssessmentProcessing(){
    configureOverviewForEnvironment();

    if(selectedMode === 'readonly'){
      processingCopy.textContent = 'ResearchOps is combining the authorized environment facts with the resolved target materials.';
      processingEnvLabel.textContent = 'Reading authorized environment facts';
      processingEnvState.textContent = 'Processing';
    }else if(selectedMode === 'snapshot'){
      processingCopy.textContent = 'ResearchOps is combining the uploaded environment snapshot with the resolved target materials.';
      processingEnvLabel.textContent = 'Reading uploaded environment snapshot';
      processingEnvState.textContent = 'Processing';
    }else if(selectedMode === 'manual'){
      processingCopy.textContent = 'ResearchOps is structuring the environment facts you provided and combining them with the resolved target materials.';
      processingEnvLabel.textContent = 'Structuring manual environment input';
      processingEnvState.textContent = 'Processing';
    }else{
      processingCopy.textContent = 'ResearchOps is building the assessment from the available target materials. Environment information was not provided.';
      processingEnvLabel.textContent = 'Environment information';
      processingEnvState.textContent = 'Not provided';
    }

    showScreen('processing');
    setTimeout(() => showScreen('overview'), 1400);
  }

  function continueAfterTargetResolution(){
    if(selectedMode === 'readonly'){
      showScreen('auth');
    }else{
      startAssessmentProcessing();
    }
  }

  overviewBackBtn.addEventListener('click', () => {
    showScreen('setup');
  });

  const dimensionFeedbackBtn = document.getElementById('dimension-feedback-btn');
  const feedbackPanel = document.getElementById('feedback-panel');
  const feedbackBackdrop = document.getElementById('feedback-backdrop');
  const feedbackClose = document.getElementById('feedback-close');
  const feedbackOptions = [...document.querySelectorAll('.feedback-option')];
  const feedbackInputWrap = document.getElementById('feedback-input-wrap');
  const feedbackTextarea = document.getElementById('feedback-textarea');
  const feedbackSubmit = document.getElementById('feedback-submit');
  const feedbackSuccess = document.getElementById('feedback-success');
  const feedbackError = document.getElementById('feedback-error');
  const feedbackKicker = document.getElementById('feedback-kicker');
  const feedbackContextTitle = document.getElementById('feedback-context-title');
  const feedbackCopy = document.getElementById('feedback-copy');

  let selectedFeedbackType = null;
  let feedbackContext = 'finding';

  function openFeedbackPanel(context='finding'){
    feedbackContext = context;
    selectedFeedbackType = null;

    if(context === 'evidence'){
      feedbackKicker.textContent = 'Evidence feedback';
      feedbackContextTitle.textContent = evidenceTitle.textContent;
      feedbackCopy.textContent = 'Feedback applies to this Evidence. It does not directly edit the Finding, Dimension status, or Overall Gate.';
    }else{
      feedbackKicker.textContent = 'Finding feedback';
      feedbackContextTitle.textContent = detailFindingTitle.textContent;
      feedbackCopy.textContent = 'Feedback applies to this Finding and its evidence. It does not directly edit the Dimension status or Overall Gate.';
    }

    feedbackOptions.forEach(btn => btn.classList.remove('active'));
    feedbackOptions.forEach(btn => {
      if(btn.dataset.feedback === 'confirm') btn.textContent = 'Confirm';
      if(btn.dataset.feedback === 'question') btn.textContent = 'Question';
      if(btn.dataset.feedback === 'correct') btn.textContent = 'Correct';
      if(btn.dataset.feedback === 'evidence') btn.textContent = 'Add Evidence';
    });
    feedbackInputWrap.classList.remove('active');
    feedbackTextarea.value = '';
    feedbackSuccess.classList.remove('active');
    feedbackError.classList.remove('active');
    feedbackError.textContent = '';
    feedbackSubmit.disabled = false;
    feedbackSubmit.innerHTML = 'Submit feedback';
    feedbackPanel.classList.add('active');
    feedbackBackdrop.classList.add('active');
    feedbackPanel.setAttribute('aria-hidden','false');
  }

  function closeFeedbackPanel(){
    feedbackPanel.classList.remove('active');
    feedbackBackdrop.classList.remove('active');
    feedbackPanel.setAttribute('aria-hidden','true');
  }

  dimensionFeedbackBtn.addEventListener('click', () => openFeedbackPanel('finding'));
  feedbackClose.addEventListener('click', closeFeedbackPanel);
  feedbackBackdrop.addEventListener('click', closeFeedbackPanel);

  feedbackOptions.forEach(btn => {
    btn.addEventListener('click', () => {
      selectedFeedbackType = btn.dataset.feedback;
      feedbackOptions.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const needsText = selectedFeedbackType !== 'confirm';
      feedbackInputWrap.classList.toggle('active', needsText);
      feedbackSuccess.classList.remove('active');
      feedbackError.classList.remove('active');
      feedbackError.textContent = '';
      feedbackSubmit.disabled = false;
      feedbackSubmit.innerHTML = 'Submit feedback';
    });
  });

  feedbackSubmit.addEventListener('click', () => {
    feedbackError.classList.remove('active');
    feedbackError.textContent = '';
    feedbackSuccess.classList.remove('active');

    if(!selectedFeedbackType){
      feedbackError.textContent = 'Choose a feedback type first.';
      feedbackError.classList.add('active');
      return;
    }

    if(selectedFeedbackType !== 'confirm' && !feedbackTextarea.value.trim()){
      feedbackError.textContent = 'Add a short note before submitting this feedback.';
      feedbackError.classList.add('active');
      feedbackTextarea.focus();
      return;
    }

    feedbackSubmit.disabled = true;
    feedbackSubmit.innerHTML = 'Feedback submitted ✓';
    feedbackSuccess.textContent = feedbackContext === 'evidence'
      ? 'Feedback recorded for this Evidence.'
      : feedbackContext === 'pending'
        ? 'Human decision recorded for this candidate.'
        : 'Feedback recorded for this Finding.';
    feedbackSuccess.classList.add('active');
  });

  const rd01ViewDetails = document.getElementById('rd01-view-details');
  const rd02ViewDetails = document.getElementById('rd02-view-details');
  const rd03ViewDetails = document.getElementById('rd03-view-details');
  const dimensionBackBtn = document.getElementById('dimension-back-btn');
  const dimensionViewEvidence = document.getElementById('dimension-view-evidence');

  const detailDimensionId = document.getElementById('detail-dimension-id');
  const detailDimensionName = document.getElementById('detail-dimension-name');
  const detailStatus = document.getElementById('detail-status');
  const detailStatusCopy = document.getElementById('detail-status-copy');
  const detailGateImpact = document.getElementById('detail-gate-impact');
  const detailFindingCondition = document.getElementById('detail-finding-condition');
  const detailFindingTitle = document.getElementById('detail-finding-title');
  const detailFindingSummary = document.getElementById('detail-finding-summary');
  const detailFindingType = document.getElementById('detail-finding-type');
  const detailCriticalTag = document.getElementById('detail-critical-tag');
  const detailEvidenceTag = document.getElementById('detail-evidence-tag');
  const detailFindingImpact = document.getElementById('detail-finding-impact');
  const detailNextActionTitle = document.getElementById('detail-next-action-title');
  const detailNextActionType = document.getElementById('detail-next-action-type');

  const conditionalDimensionDetailData = {
    rd01: {
      id: 'RD-01',
      name: 'Data & Access Readiness',
      status: 'Unknown',
      statusClass: 'status-chip status-unknown',
      statusCopy: 'Dataset access cannot be confirmed with the evidence currently available.',
      gateImpact: 'Prevents full PROCEED until the access condition is resolved.',
      condition: 'Condition · Dataset access',
      findingTitle: 'Dataset access permission is not confirmed',
      findingSummary: 'Available sources do not establish whether the required dataset can be accessed under the user’s actual reproduction conditions.',
      findingType: 'Finding type · Unknown',
      gateCritical: true,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · Prevents full PROCEED',
      nextAction: 'Confirm whether dataset access can be obtained',
      nextActionType: 'Resolve Gate-critical Unknown'
    },
    rd02: {
      id: 'RD-02',
      name: 'Environment & Dependency Readiness',
      status: 'Warning',
      statusClass: 'status-chip status-warning',
      statusCopy: 'The environment is usable for assessment, but one compatibility risk still needs validation.',
      gateImpact: 'Adds a non-blocking risk to the current CONDITIONAL PROCEED decision.',
      condition: 'Condition · Environment compatibility',
      findingTitle: 'A version compatibility risk still needs validation',
      findingSummary: 'The available environment facts differ from the project’s documented setup in a way that may matter, but current evidence does not establish a hard incompatibility.',
      findingType: 'Finding type · Inference',
      gateCritical: false,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · Non-blocking Warning',
      nextAction: 'Validate the environment against the documented dependency setup',
      nextActionType: 'Mitigate Warning'
    },
    rd03: {
      id: 'RD-03',
      name: 'Weights & Configuration Readiness',
      status: 'Ready',
      statusClass: 'status-chip status-ready',
      statusCopy: 'Required checkpoint and configuration relationships are sufficiently identified for the current assessment.',
      gateImpact: 'No current blocker from weights or configuration.',
      condition: 'Condition · Checkpoint and configuration mapping',
      findingTitle: 'Checkpoint and configuration relationships are sufficiently identified',
      findingSummary: 'The available project materials provide a usable mapping between the required checkpoint and the configuration needed for the current reproduction path.',
      findingType: 'Finding type · Fact',
      gateCritical: false,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · No current blocker',
      nextAction: 'Run a minimum configuration validation before higher-cost reproduction work',
      nextActionType: 'Minimum Validation'
    }
  };

  const pauseDimensionDetailData = {
    rd01: {
      id: 'RD-01',
      name: 'Data & Access Readiness',
      status: 'Blocked',
      statusClass: 'status-chip status-blocked',
      statusCopy: 'Explicit negative evidence shows the required dataset access is unavailable for the current reproduction path.',
      gateImpact: 'This blocking condition triggers the current PAUSE decision.',
      condition: 'Condition · Required dataset access',
      findingTitle: 'Required dataset access is explicitly unavailable',
      findingSummary: 'The current reproduction path has a confirmed negative access result for a required dataset condition.',
      findingType: 'Finding type · Fact',
      gateCritical: true,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · Triggers PAUSE',
      nextAction: 'Resolve or replace the blocked access path',
      nextActionType: 'Resolve Blocker'
    },
    rd02: conditionalDimensionDetailData.rd02,
    rd03: conditionalDimensionDetailData.rd03
  };

  const proceedDimensionDetailData = {
    rd01: {
      id: 'RD-01',
      name: 'Data & Access Readiness',
      status: 'Ready',
      statusClass: 'status-chip status-ready',
      statusCopy: 'Required data and access conditions are sufficiently supported for the current validation path.',
      gateImpact: 'No current blocker from data or access readiness.',
      condition: 'Condition · Data and access requirements',
      findingTitle: 'Required data and access conditions are sufficiently supported',
      findingSummary: 'Available project materials and current access facts are sufficient for the intended validation path.',
      findingType: 'Finding type · Fact',
      gateCritical: false,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · No current blocker',
      nextAction: 'Run the minimum validation before higher-cost reproduction work',
      nextActionType: 'Minimum Validation'
    },
    rd02: {
      id: 'RD-02',
      name: 'Environment & Dependency Readiness',
      status: 'Ready',
      statusClass: 'status-chip status-ready',
      statusCopy: 'Available environment facts are sufficiently aligned with the documented dependency requirements for the current validation path.',
      gateImpact: 'No current blocker from environment or dependency readiness.',
      condition: 'Condition · Environment compatibility',
      findingTitle: 'Environment facts sufficiently support the current validation path',
      findingSummary: 'The available environment facts are sufficiently aligned with the documented dependency requirements for the intended validation step.',
      findingType: 'Finding type · Fact',
      gateCritical: false,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · No current blocker',
      nextAction: 'Run the minimum validation before higher-cost reproduction work',
      nextActionType: 'Minimum Validation'
    },
    rd03: {
      id: 'RD-03',
      name: 'Weights & Configuration Readiness',
      status: 'Ready',
      statusClass: 'status-chip status-ready',
      statusCopy: 'Required checkpoint and configuration relationships are sufficiently identified for the intended validation path.',
      gateImpact: 'No current blocker from weights or configuration.',
      condition: 'Condition · Checkpoint and configuration mapping',
      findingTitle: 'Checkpoint and configuration relationships are sufficiently identified',
      findingSummary: 'Available project materials provide a usable checkpoint and configuration mapping for the intended validation path.',
      findingType: 'Finding type · Fact',
      gateCritical: false,
      evidence: 'Evidence · Available',
      findingImpact: 'Gate impact · No current blocker',
      nextAction: 'Run the minimum validation before higher-cost reproduction work',
      nextActionType: 'Minimum Validation'
    }
  };

  const dimensionDetailDataByScenario = {
    conditional: conditionalDimensionDetailData,
    pause: pauseDimensionDetailData,
    proceed: proceedDimensionDetailData
  };

  let activeDimension = 'rd01';
  let activeScenario = 'conditional';

  function openDimensionDetail(key, scenario='conditional'){
    activeDimension = key;
    activeScenario = scenario;
    const d = dimensionDetailDataByScenario[scenario][key];

    detailDimensionId.textContent = d.id;
    detailDimensionName.textContent = d.name;
    detailStatus.className = d.statusClass;
    detailStatus.textContent = d.status;
    detailStatusCopy.textContent = d.statusCopy;
    detailGateImpact.textContent = d.gateImpact;

    detailFindingCondition.textContent = d.condition;
    detailFindingTitle.textContent = d.findingTitle;
    detailFindingSummary.textContent = d.findingSummary;
    detailFindingType.textContent = d.findingType;
    detailEvidenceTag.textContent = d.evidence;
    detailFindingImpact.textContent = d.findingImpact;
    detailNextActionTitle.textContent = d.nextAction;
    detailNextActionType.textContent = d.nextActionType;
    detailCriticalTag.style.display = d.gateCritical ? 'inline-flex' : 'none';

    showScreen('dimensionDetail');
  }

  rd01ViewDetails.addEventListener('click', () => openDimensionDetail('rd01', 'conditional'));
  rd02ViewDetails.addEventListener('click', () => openDimensionDetail('rd02', 'conditional'));
  rd03ViewDetails.addEventListener('click', () => openDimensionDetail('rd03', 'conditional'));

  const pauseRd01ViewDetails = document.getElementById('pause-rd01-view-details');
  const pauseRd02ViewDetails = document.getElementById('pause-rd02-view-details');
  const pauseRd03ViewDetails = document.getElementById('pause-rd03-view-details');
  const proceedRd01ViewDetails = document.getElementById('proceed-rd01-view-details');
  const proceedRd02ViewDetails = document.getElementById('proceed-rd02-view-details');
  const proceedRd03ViewDetails = document.getElementById('proceed-rd03-view-details');

  pauseRd01ViewDetails.addEventListener('click', () => openDimensionDetail('rd01', 'pause'));
  pauseRd02ViewDetails.addEventListener('click', () => openDimensionDetail('rd02', 'pause'));
  pauseRd03ViewDetails.addEventListener('click', () => openDimensionDetail('rd03', 'pause'));

  proceedRd01ViewDetails.addEventListener('click', () => openDimensionDetail('rd01', 'proceed'));
  proceedRd02ViewDetails.addEventListener('click', () => openDimensionDetail('rd02', 'proceed'));
  proceedRd03ViewDetails.addEventListener('click', () => openDimensionDetail('rd03', 'proceed'));

  dimensionBackBtn.addEventListener('click', () => {
    if(activeScenario === 'pause') showScreen('pause');
    else if(activeScenario === 'proceed') showScreen('proceed');
    else showScreen('overview');
  });

  const evidenceDrawer = document.getElementById('evidence-drawer');
  const evidenceBackdrop = document.getElementById('evidence-backdrop');
  const evidenceClose = document.getElementById('evidence-close');
  const evidenceTitle = document.getElementById('evidence-title');
  const evidenceVerification = document.getElementById('evidence-verification');
  const evidenceSummary = document.getElementById('evidence-summary');
  const evidenceSource = document.getElementById('evidence-source');
  const evidenceLocation = document.getElementById('evidence-location');
  const evidenceMaterialType = document.getElementById('evidence-material-type');
  const evidenceConflict = document.getElementById('evidence-conflict');
  const evidenceOpenSource = document.getElementById('evidence-open-source');

  const evidenceFeedbackBtn = document.getElementById('evidence-feedback-btn');

  let currentEvidenceSourceUrl = '';

  const evidenceConflictCompare = document.getElementById('evidence-conflict-compare');
  const evidenceConflictATitle = document.getElementById('evidence-conflict-a-title');
  const evidenceConflictACopy = document.getElementById('evidence-conflict-a-copy');
  const evidenceConflictBTitle = document.getElementById('evidence-conflict-b-title');
  const evidenceConflictBCopy = document.getElementById('evidence-conflict-b-copy');

  function setEvidenceSourceUrl(url){
    currentEvidenceSourceUrl = url || '';
    evidenceOpenSource.style.display = currentEvidenceSourceUrl ? '' : 'none';
  }

  function resetConflictComparison(){
    evidenceConflictCompare.classList.remove('active');
    evidenceConflictATitle.textContent = '';
    evidenceConflictACopy.textContent = '';
    evidenceConflictBTitle.textContent = '';
    evidenceConflictBCopy.textContent = '';
  }

  function openEvidenceDrawer(){
    // Real Assessment evidence is opened by mvp-api.js.
  }

  function openResourceEvidenceDrawer(){
    // Real Resource Evidence is opened by mvp-api.js.
  }

  function openConflictEvidenceDrawer(){
    // Real Conflict Evidence is opened by mvp-api.js.
  }

  function closeEvidenceDrawer(){
    evidenceDrawer.classList.remove('active');
    evidenceBackdrop.classList.remove('active');
    evidenceDrawer.setAttribute('aria-hidden','true');
  }

  dimensionViewEvidence.addEventListener('click', openEvidenceDrawer);
  evidenceClose.addEventListener('click', closeEvidenceDrawer);
  evidenceBackdrop.addEventListener('click', closeEvidenceDrawer);

  evidenceOpenSource.addEventListener('click', () => {
    if(currentEvidenceSourceUrl){
      window.open(currentEvidenceSourceUrl, '_blank', 'noopener,noreferrer');
    }
  });

  evidenceFeedbackBtn.addEventListener('click', () => {
    openFeedbackPanel('evidence');
  });

  const modeDetails = {
    readonly: document.getElementById('detail-readonly'),
    snapshot: document.getElementById('detail-snapshot'),
    manual: document.getElementById('detail-manual'),
    later: null
  };

  function showModeDetail(mode){
    Object.values(modeDetails).filter(Boolean).forEach(el => el.classList.remove('active'));
    if (modeDetails[mode]) modeDetails[mode].classList.add('active');
  }

  targetTypeEl.addEventListener('change', () => {
    targetResolved = false;
    targetDeferred = false;
    targetResolvedName = '';
    targetResolvedTypeLabel = '';
    clearSetupError();
  });

  targetEntryEl.addEventListener('input', () => {
    targetResolved = false;
    targetDeferred = false;
    targetResolvedName = '';
    targetResolvedTypeLabel = '';
    clearSetupError();
  });

  modes.forEach(mode => {
    mode.addEventListener('click', () => {
      selectedMode = mode.dataset.mode;
      modes.forEach(m => m.classList.remove('active'));
      mode.classList.add('active');
      showModeDetail(selectedMode);
      continueBtn.innerHTML = selectedMode === 'readonly'
        ? 'Continue to authorization <span>→</span>'
        : 'Start readiness assessment <span>→</span>';
    });
  });

  const candidateA = document.getElementById('candidate-a');
  const candidateB = document.getElementById('candidate-b');
  const targetConfirmBtn = document.getElementById('target-confirm-btn');
  const targetSupplementBtn = document.getElementById('target-supplement');
  const targetDeferBtn = document.getElementById('target-defer');

  function selectCandidate(candidate){
    [candidateA, candidateB].forEach(btn => btn.classList.remove('active'));
    candidate.classList.add('active');
    selectedTargetCandidate = candidate === candidateA ? 'a' : 'b';
  }

  candidateA.addEventListener('click', () => selectCandidate(candidateA));
  candidateB.addEventListener('click', () => selectCandidate(candidateB));

  targetConfirmBtn.addEventListener('click', () => {
    targetResolved = true;
    targetDeferred = false;
    const selectedCandidate = selectedTargetCandidate === 'b' ? candidateB : candidateA;
    targetResolvedName = selectedCandidate.querySelector('.candidate-name').textContent;
    targetResolvedTypeLabel = selectedTargetCandidate === 'b' ? 'Related project / repository' : 'Paper';
    prepareTargetIdentified();
  });

  targetSupplementBtn.addEventListener('click', () => {
    showScreen('setup');
    setTimeout(() => {
      targetEntryEl.focus();
      targetEntryEl.scrollIntoView({behavior:'smooth', block:'center'});
    }, 100);
  });

  const skipConfirmBackdrop = document.getElementById('skip-confirm-backdrop');
  const skipConfirmCancel = document.getElementById('skip-confirm-cancel');
  const skipConfirmProceed = document.getElementById('skip-confirm-proceed');

  function openSkipConfirmation(){
    skipConfirmBackdrop.classList.add('active');
    skipConfirmBackdrop.setAttribute('aria-hidden','false');
  }

  function closeSkipConfirmation(){
    skipConfirmBackdrop.classList.remove('active');
    skipConfirmBackdrop.setAttribute('aria-hidden','true');
  }

  targetDeferBtn.addEventListener('click', openSkipConfirmation);

  skipConfirmCancel.addEventListener('click', closeSkipConfirmation);

  skipConfirmBackdrop.addEventListener('click', (e) => {
    if(e.target === skipConfirmBackdrop) closeSkipConfirmation();
  });

  skipConfirmProceed.addEventListener('click', () => {
    targetDeferred = true;
    targetResolved = false;
    closeSkipConfirmation();
    continueAfterTargetResolution();
  });

  function selectEnvironmentMode(modeName){
    selectedMode = modeName;
    modes.forEach(m => {
      const isActive = m.dataset.mode === modeName;
      m.classList.toggle('active', isActive);
    });
    showModeDetail(modeName);
    continueBtn.innerHTML = modeName === 'readonly'
      ? 'Continue to authorization <span>→</span>'
      : 'Start readiness assessment <span>→</span>';
  }

  const authUseSnapshot = document.getElementById('auth-use-snapshot');
  const authUseManual = document.getElementById('auth-use-manual');
  const authNoEnvironment = document.getElementById('auth-no-environment');

  authUseSnapshot.addEventListener('click', () => {
    showScreen('setup');
    selectEnvironmentMode('snapshot');
    setTimeout(() => {
      const panel = document.getElementById('detail-snapshot');
      if (panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  authUseManual.addEventListener('click', () => {
    showScreen('setup');
    selectEnvironmentMode('manual');
    setTimeout(() => {
      const panel = document.getElementById('detail-manual');
      if (panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  authNoEnvironment.addEventListener('click', () => {
    selectedMode = 'later';
    startAssessmentProcessing();
  });

  const authorizeBtn = document.getElementById('authorize-btn');
  const denyAuthorizeBtn = document.getElementById('deny-authorize-btn');
  const authDeniedReview = document.getElementById('auth-denied-review');
  const authDeniedSnapshot = document.getElementById('auth-denied-snapshot');
  const authDeniedManual = document.getElementById('auth-denied-manual');
  const authDeniedNoEnv = document.getElementById('auth-denied-no-env');

  authorizeBtn.addEventListener('click', () => {
    selectedMode = 'readonly';
    startAssessmentProcessing();
  });

  denyAuthorizeBtn.addEventListener('click', () => {
    showScreen('authDenied');
  });

  authDeniedReview.addEventListener('click', () => {
    showScreen('auth');
  });

  authDeniedSnapshot.addEventListener('click', () => {
    showScreen('setup');
    selectEnvironmentMode('snapshot');
    setTimeout(() => {
      const panel = document.getElementById('detail-snapshot');
      if(panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  authDeniedManual.addEventListener('click', () => {
    showScreen('setup');
    selectEnvironmentMode('manual');
    setTimeout(() => {
      const panel = document.getElementById('detail-manual');
      if(panel) panel.scrollIntoView({behavior:'smooth', block:'center'});
    }, 120);
  });

  authDeniedNoEnv.addEventListener('click', () => {
    selectedMode = 'later';
    startAssessmentProcessing();
  });

  const snapshotInput = document.getElementById('snapshot-file');
  const snapshotState = document.getElementById('snapshot-state');
  const snapshotName = document.getElementById('snapshot-name');
  const removeSnapshot = document.getElementById('remove-snapshot');

  snapshotInput.addEventListener('change', () => {
    if(snapshotInput.files && snapshotInput.files[0]){
      snapshotName.textContent = snapshotInput.files[0].name;
      snapshotState.classList.add('active');
    }
  });

  removeSnapshot.addEventListener('click', (e) => {
    e.preventDefault();
    snapshotInput.value = '';
    snapshotState.classList.remove('active');
  });

  continueBtn.addEventListener('click', () => {
    clearSetupError();

    if(!targetEntryEl.value.trim()){
      showSetupError('Add a target entry before starting the assessment.');
      return;
    }

    if(selectedMode === 'snapshot' && !(snapshotInput.files && snapshotInput.files[0])){
      showSetupError('Upload an environment snapshot, choose another environment input mode, or select Not now.');
      return;
    }

    const manualInput = document.querySelector('.manual-textarea');
    if(selectedMode === 'manual' && !manualInput.value.trim()){
      showSetupError('Add the environment facts you know, choose another input mode, or select Not now.');
      return;
    }

    if(targetNeedsConfirmation()){
      prepareTargetConfirmation();
      return;
    }

    if(targetDeferred){
      continueAfterTargetResolution();
      return;
    }

    targetResolved = true;
    targetResolvedName = getTargetDisplayName();
    targetResolvedTypeLabel = targetTypeEl.options[targetTypeEl.selectedIndex].textContent;
    prepareTargetIdentified();
  });

  backBtn.addEventListener('click', () => showScreen('setup'));

  if(location.hash === '#target-identified'){
    targetResolved = true;
    prepareTargetIdentified();
  }else if(location.hash === '#authorization-denied'){
    showScreen('authDenied');
  }else if(location.hash === '#partial-result'){
    showScreen('partialResult');
  }else if(location.hash === '#acquisition-failure'){
    showScreen('acquisitionFailure');
  }else if(location.hash === '#conflict'){
    showScreen('conflict');
  }else if(location.hash === '#gate-not-available'){
    showScreen('gateNotAvailable');
  }else if(location.hash === '#pause'){
    showScreen('pause');
  }else if(location.hash === '#proceed'){
    showScreen('proceed');
  }
