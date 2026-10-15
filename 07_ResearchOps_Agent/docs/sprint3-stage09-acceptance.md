# Sprint 3 Stage 09 Acceptance Record

## Scope and decision

This record verifies Sprint 3 stage 09 against the read-only source schedule `ResearchOps_Sprint3.docx` (SHA-256 `9D89E73B64213EA09CE393154936351226C95409E90C913C996CCE684DC9B272`). The source document and the frozen V3.6 revision HTML were not modified.

Stage 09 decision: **PASS**. The automated suite covers the principal success and exception paths, critical conclusions retain Evidence or remain Unknown, Gate-unavailable results do not invent business statuses, and the runtime boundary remains read-only. Response-scoped Trace is sufficient for the MVP workflow; durable cross-request audit storage is explicitly deferred.

## Verification commands

| Check | Expected | Result |
| --- | --- | --- |
| `python -m pytest -q --tb=short` | All tests pass | PASS, 105 tests collected and passed |
| `python -m ruff check . --output-format concise` | No lint violations | PASS |
| `python -m ruff format --check .` | No formatting drift | PASS after formatting 13 files |
| `git diff --check` | No whitespace errors | PASS |

## Exception acceptance matrix

| Area | Adversarial or exception case | Required observable behavior | Evidence | Result |
| --- | --- | --- | --- | --- |
| Target resolution | Blank or malformed input | Reject with the stable validation/error contract; do not start an Assessment | `test_assessment_endpoint_rejects_unresolved_repository`, schema validation tests | PASS |
| Target resolution | Paper title returns multiple plausible identities | Return candidates and require explicit confirmation; do not fabricate one identity | `test_paper_title_resolution_requests_candidate_confirmation`, `test_paper_title_assessment_requires_candidate_confirmation` | PASS |
| Target resolution | Similar but wrong title or empty metadata result | Discard irrelevant candidates or remain unresolved | `test_crossref_discards_topically_similar_but_wrong_title`, `test_empty_crossref_result_is_unresolved_without_technical_failure` | PASS |
| Target resolution | Transient arXiv lookup failure | Retry within a finite bound; preserve failure if retries do not resolve it | `test_arxiv_title_search_retries_a_transient_connection_failure` | PASS |
| Repository acquisition | Repository material collection fails | Return `partial` plus `acquisition_failure`; leave all Dimension statuses and Overall Gate unavailable | `test_repository_collection_failure_returns_valid_partial_assessment`, `test_assessment_withholds_gate_when_repository_collection_fails` | PASS |
| Repository acquisition | An optional evaluation file fails | Preserve the main Assessment and available materials; do not fail the whole request | `test_optional_evaluation_file_failure_does_not_abort_collection` | PASS |
| Repository acquisition | Unsupported/non-GitHub resolved target reaches the GitHub collector | Reject at the collector boundary | `test_collector_rejects_non_github_resolved_target` | PASS |
| RD-01 | Dataset entry exists but account, terms, or approval remains unresolved | Keep Data & Access `Unknown` and attach the source entry as Evidence | `test_kaggle_competition_entry_preserves_account_and_terms_unknown`, `test_multiple_restricted_entries_remain_gate_critical_unknown` | PASS |
| RD-01 | Direct public dataset artifact is confirmed | Allow RD-01 `Ready` without claiming download or local availability | `test_direct_public_artifact_can_support_ready` | PASS |
| RD-02 | Project requirements or comparable local facts are incomplete | Return `Unknown`, not Warning or Ready | `test_unprovided_environment_remains_unknown`, `test_repository_statuses_follow_frozen_readiness_rules` | PASS |
| RD-02 | Complete declared versions differ | Return `Warning`; do not escalate a version difference to Blocked | `test_known_version_difference_is_warning` | PASS |
| RD-02 | Complete declared versions align | Allow `Ready` at the declared-version comparison level | `test_aligned_versions_support_ready`, `test_manual_environment_input_can_support_rd02_ready` | PASS |
| RD-02 | Dependency materials disagree | Preserve both sources as an Evidence Conflict and keep readiness `Unknown` | `test_conflicting_dependency_materials_are_preserved_for_rd02` | PASS |
| Environment authorization | Read-only inspection is not authorized, token is forged, or grant has expired | Do not inspect the local environment; return a safe authorization error where applicable | `test_readonly_mode_requires_explicit_authorization`, `test_readonly_environment_rejects_forged_authorization_token`, authorization lifetime tests | PASS |
| Environment input | Snapshot/manual text contains arbitrary content | Parse no more than the bounded text limit and never execute its contents | `test_manual_environment_text_is_structured_without_execution` | PASS |
| RD-03 | Checkpoint entry and testing configuration are both confirmed | Allow `Ready` while explicitly avoiding any claim that the artifact was downloaded or loaded | `test_all_checkpoint_references_are_probed_and_preserved_for_rd03`, public Drive probe tests | PASS |
| RD-03 | Checkpoint reference is absent, access is not proven, or configuration mapping is incomplete | Keep RD-03 `Unknown` with the relevant repository Evidence | `test_repository_statuses_follow_frozen_readiness_rules` and RD-03 contract tests | PASS |
| External asset | Drive request times out or fails technically | Retry finitely; report `acquisition_failure`, not verified inaccessibility | `test_transient_timeout_is_retried_before_public_result`, `test_repeated_timeout_is_an_acquisition_failure_not_inaccessibility` | PASS |
| External asset | Drive returns a generic success page or redirects to another resource | Do not treat the response as proof that the named checkpoint is public | `test_generic_drive_success_page_does_not_confirm_checkpoint_identity`, `test_drive_redirect_to_different_resource_is_not_confirmed` | PASS |
| External asset | A recent identical probe previously succeeded | Reuse only the short-lived successful result; do not turn a failed result into success | `test_recent_success_is_reused_from_short_term_cache` | PASS |
| External asset | Host is outside the allowlist | Reject the probe | `test_external_asset_probe_rejects_unapproved_hosts` | PASS |
| Evaluation Conflict | Dataset split, metric, threshold, or other values conflict across materials | Preserve every independent conflict and both Evidence sources; keep conflict separate from input type | evaluation conflict tests and `test_evidence_conflict_is_input_agnostic_and_can_span_dimensions` | PASS |
| Evaluation Conflict | No supported conflicting pair is found | Keep the signal `Unknown`; do not invent `None detected` or `No conflict details` fields | `test_no_conflicting_pair_remains_unknown_without_inventing_none_state`, frontend contract test | PASS |
| Resource signal | Minimum project requirement is absent | Keep Resource Constraint `Unknown` | `test_known_current_resources_without_project_minimum_remain_unknown` | PASS |
| Resource signal | Confirmed resource or time shortfall exists | Mark the signal Blocked and resolve Overall Gate to `PAUSE` | resource signal blocked tests and `test_confirmed_resource_shortfall_triggers_pause` | PASS |
| Resource signal | Confirmed but narrow capacity margin exists | Return a non-blocking Warning | `test_narrow_confirmed_resource_margin_is_warning` | PASS |
| Gate precedence | Core Blocked, gate-critical Unknown, Warning, and all-Ready paths compete | Apply precedence `PAUSE` > `CONDITIONAL PROCEED` > `PROCEED`; keep the result in the Overview contract | gate decision tests and frontend routing assertions | PASS |
| API failure | Unexpected exception escapes the domain services | Return a sanitized 500 response and log the internal exception | `test_assessment_endpoint_returns_safe_error_for_unexpected_failure` | PASS |
| Frontend integrity | Dynamic connector needs a state not present in the frozen design | Populate existing V3.6 surfaces; do not add fabricated conflict labels or separate Gate result pages | `test_mvp_frontend_is_served_by_fastapi` plus browser exploratory verification | PASS |

## Safety audit

| Boundary | Audit result |
| --- | --- |
| Shell | No `shell=True`, `os.system`, command shell, or user-supplied command execution exists in the Readiness path. The only child-process calls are fixed, read-only `nvidia-smi` and `nvcc --version` diagnostics with `shell=False` and four-second timeouts. |
| Filesystem | The Assessment path reads bounded public/local facts and disk capacity. It does not write, delete, overwrite, rename, or generate repository/user files. |
| Docker and packages | No Docker invocation, package installation, or environment mutation exists in the Readiness path. |
| GPU and training | No model load, CUDA compute, training, evaluation run, or reproduction run occurs. The optional NVIDIA diagnostic only queries device metadata. |
| Network | Repository, metadata, dataset, and checkpoint access is read-only, bounded, host-validated where required, and failure-preserving. Project Page collection rejects private/non-global destinations. |

## Trace audit

| Trace requirement | Implementation evidence | Result |
| --- | --- | --- |
| Target identity | Trace records target type and canonical identity after normalization; `resolved_target` retains canonical URL and method | PASS |
| Workflow order | Trace records `resolve_target`, conditional repository acquisition, `build_assessment`, and `validate_output` in order | PASS |
| Material acquisition | Trace records branch, README presence, bounded dependency/evaluation counts, and read-only repository acquisition | PASS |
| Dataset/checkpoint probes | Trace records the number of documented dataset entries and checkpoint public-readability results without downloading artifacts | PASS |
| Environment boundary | Trace records selected acquisition mode and whether comparable facts were acquired | PASS |
| Conflicts | Trace records the number of preserved unresolved Evidence Conflicts; each conflict carries its source Evidence | PASS |
| Gate derivation | Trace records the Overall Gate and trigger-reference count; the response carries the exact `trigger_refs`, `main_risk`, and first next action | PASS |
| Partial acquisition | Trace records the failed acquisition phase and reason; business statuses and Gate remain unavailable | PASS |
| Output validation | The final Trace event confirms schema validation of the stable frontend response contract | PASS |

Trace is intentionally response-scoped for MVP Alpha. It is not yet a persistent, queryable audit-log subsystem with correlation IDs, retention rules, or redaction policy; that is an operational hardening item rather than a stage 09 blocker.

## First-principles and adversarial conclusion

The implementation now distinguishes three fundamentally different facts: evidence that is positively verified, evidence that is contradicted or risky, and evidence that is unavailable or technically unverified. Network success alone is not treated as resource identity, missing facts are not converted into warnings, and technical acquisition failure does not become a business conclusion. Gate precedence is derived from those facts rather than from a demo scenario.

The main remaining risk is external-service variability in a live demo: GitHub, Crossref, arXiv, Kaggle, or Drive may throttle, redirect, or time out. The current behavior fails safely to Unknown or Partial and preserves the reason. This does not block stage 09, but stage 10 should capture a known-good FGI demo run and document the live-service limitation.
