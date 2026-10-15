"""Deterministic Readiness status, Signal, Gate, and action adjudication.

AI supplies evidence-linked semantic candidates. This module alone maps those
candidates to the frozen product statuses and Overall Gate.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from researchops.schemas.ai_analysis import (
    AIAnalysisDomainProjection,
    EvidenceAreaCoverage,
    ProjectedConflict,
    ProjectedEvidence,
    ProjectedFinding,
    ReadinessCriterionId,
)
from researchops.schemas.readiness import (
    CriterionAdjudication,
    DimensionId,
    EvaluationConflictType,
    EvaluationSignal,
    Finding,
    ReadinessAdjudicationResult,
    ReadinessDimension,
    ResourceSignal,
)
from researchops.services.gate_decision import GateDecisionService


class ReadinessAdjudicationError(RuntimeError):
    """The admitted candidate graph cannot be safely adjudicated."""


DIMENSION_NAMES: dict[DimensionId, str] = {
    "RD-01": "Data & Access Readiness",
    "RD-02": "Environment & Dependency Readiness",
    "RD-03": "Weights & Configuration Readiness",
}

REQUIRED_CRITERIA: dict[DimensionId, tuple[ReadinessCriterionId, ...]] = {
    "RD-01": (
        "rd01.dataset_identity",
        "rd01.dataset_access",
        "rd01.input_contract",
    ),
    "RD-02": (
        "rd02.software_requirements",
        "rd02.dependency_requirements",
        "rd02.environment_compatibility",
    ),
    "RD-03": (
        "rd03.checkpoint_access",
        "rd03.configuration_mapping",
        "rd03.execution_contract",
    ),
}

CRITERION_LABELS: dict[ReadinessCriterionId, str] = {
    "rd01.dataset_identity": "Required dataset identity",
    "rd01.dataset_access": "Dataset acquisition and access",
    "rd01.input_contract": "Dataset split, annotation, path, and input contract",
    "rd02.software_requirements": "Python, framework, CUDA, and runtime requirements",
    "rd02.dependency_requirements": "Dependency set and version requirements",
    "rd02.environment_compatibility": "Project-to-user environment compatibility",
    "rd03.checkpoint_access": "Checkpoint or weight availability and access",
    "rd03.configuration_mapping": "Checkpoint, model, and configuration mapping",
    "rd03.execution_contract": "Required execution command and key parameters",
    "resource.minimum_requirements": "Explicit minimum resource requirements",
    "resource.current_capacity": "Current user resource capacity",
    "evaluation.dataset_split": "Evaluation dataset split",
    "evaluation.metric_definition": "Evaluation metric definition",
    "evaluation.aggregation": "Evaluation aggregation",
    "evaluation.paper_code_setting": "Paper-to-code evaluation setting",
    "evaluation.protocol": "Evaluation protocol",
}

_OUTCOME_PRIORITY = {"blocked": 0, "unknown": 1, "warning": 2, "supported": 3}


@dataclass(frozen=True, slots=True)
class _CriterionResolution:
    decision: CriterionAdjudication
    findings: tuple[Finding, ...]


class DeterministicReadinessAdjudicator:
    """Apply the frozen Evidence → Finding → Status → Gate decision chain."""

    def adjudicate(
        self,
        projection: AIAnalysisDomainProjection,
        *,
        resource_signal: ResourceSignal | None = None,
        evaluation_signal: EvaluationSignal | None = None,
        coverage: list[EvidenceAreaCoverage] | None = None,
    ) -> ReadinessAdjudicationResult:
        """Return the same decision for the same admitted candidate graph."""

        unavailable_reason = self._unavailable_reason(projection)
        if unavailable_reason is not None:
            return ReadinessAdjudicationResult(
                analysis_id=projection.analysis_id,
                bundle_id=projection.bundle_id,
                decision_available=False,
                unavailable_reason=unavailable_reason,
                rule_trace=["Gate unavailable: " + unavailable_reason],
            )

        projected_by_criterion: dict[str, list[ProjectedFinding]] = defaultdict(list)
        for item in projection.findings:
            if item.criterion_id is not None:
                projected_by_criterion[item.criterion_id].append(item)

        # Evidence can be deterministically admitted even when the AI did not
        # draft an admitted Finding for its criterion.  Do not discard that
        # lineage when Rule creates the explicit "missing Fact" Finding: the
        # material is still inspectable context, not proof of the condition.
        evidence_by_criterion: dict[str, list[ProjectedEvidence]] = defaultdict(list)
        for item in projection.evidence:
            if item.criterion_id is not None:
                evidence_by_criterion[item.criterion_id].append(item)

        conflicts_by_criterion: dict[str, list[ProjectedConflict]] = defaultdict(list)
        for item in projection.conflicts:
            if item.criterion_id is not None and not item.criterion_id.startswith("evaluation."):
                conflicts_by_criterion[item.criterion_id].append(item)

        questions_by_criterion = defaultdict(list)
        for item in projection.unresolved_questions:
            if item.criterion_id is not None and not item.criterion_id.startswith(
                ("resource.", "evaluation.")
            ):
                questions_by_criterion[item.criterion_id].append(item)

        criterion_resolutions: list[_CriterionResolution] = []
        dimensions: list[ReadinessDimension] = []
        for dimension_id in ("RD-01", "RD-02", "RD-03"):
            resolutions = [
                self._resolve_criterion(
                    dimension_id,
                    criterion_id,
                    projected_by_criterion[criterion_id],
                    evidence_by_criterion[criterion_id],
                    conflicts_by_criterion[criterion_id],
                    questions_by_criterion[criterion_id],
                )
                for criterion_id in REQUIRED_CRITERIA[dimension_id]
            ]
            criterion_resolutions.extend(resolutions)
            dimensions.append(self._dimension(dimension_id, resolutions))

        resolved_evaluation = evaluation_signal or self._evaluation_signal(projection, coverage)
        resolved_resource = resource_signal or self._resource_unknown_signal(projection, coverage)
        gate = GateDecisionService().resolve(dimensions, resolved_resource, resolved_evaluation)
        trace = [
            f"{item.decision.criterion_id}={item.decision.outcome} "
            f"({','.join(item.decision.trigger_refs)})"
            for item in criterion_resolutions
        ]
        trace.append(f"overall_gate={gate.overall_gate} ({','.join(gate.trigger_refs)})")

        return ReadinessAdjudicationResult(
            analysis_id=projection.analysis_id,
            bundle_id=projection.bundle_id,
            decision_available=True,
            dimensions=dimensions,
            resource_signal=resolved_resource,
            evaluation_signal=resolved_evaluation,
            overall_gate=gate.overall_gate,
            main_risk=gate.main_risk,
            first_next_action=gate.first_next_action,
            trigger_refs=list(gate.trigger_refs),
            criterion_decisions=[item.decision for item in criterion_resolutions],
            rule_trace=trace,
        )

    @staticmethod
    def _unavailable_reason(projection: AIAnalysisDomainProjection) -> str | None:
        if not projection.analysis_source_ids_verified:
            return "The AI analysis source set failed deterministic identity validation."
        return None

    def _resolve_criterion(
        self,
        dimension_id: DimensionId,
        criterion_id: ReadinessCriterionId,
        projected: list[ProjectedFinding],
        contextual_evidence: list[ProjectedEvidence],
        conflicts: list[ProjectedConflict],
        questions: list,
    ) -> _CriterionResolution:
        usable = [
            item
            for item in projected
            if item.primary_dimension_id == dimension_id and item.readiness_effect is not None
        ]
        blocked = [
            item
            for item in usable
            if item.readiness_effect == "condition_not_met"
            and item.finding.finding_type == "Fact"
        ]
        uncertain = [
            item
            for item in usable
            if item.readiness_effect == "insufficient_or_conflicting"
            or item.finding.finding_type != "Fact"
        ]
        warnings = [
            item
            for item in usable
            if item.readiness_effect == "non_blocking_risk"
            and item.finding.finding_type == "Fact"
        ]
        support = [
            item
            for item in usable
            if item.readiness_effect == "condition_supported"
            and item.finding.finding_type == "Fact"
        ]

        if blocked:
            outcome = "blocked"
            selected = blocked
            reason = "Explicit Fact evidence shows this required condition is not met."
        elif conflicts or questions or uncertain:
            outcome = "unknown"
            selected = uncertain
            reason = "The required condition is missing, conflicting, or not supported by Fact evidence."
        elif warnings:
            outcome = "warning"
            selected = warnings
            reason = "Fact evidence establishes a known non-blocking risk."
        elif support:
            outcome = "supported"
            selected = support
            reason = "Fact evidence supports this required condition."
        else:
            outcome = "unknown"
            selected = []
            reason = "No admitted Fact Finding covers this required criterion; no finding is not Ready."

        findings = [self._resolved_finding(item, outcome) for item in selected]
        # These objects passed Rule's locator/quote validation.  They are
        # included only on Rule-generated Unknowns so the drawer can show the
        # precise material that was insufficient; they never upgrade status.
        insufficient_evidence = [
            item.evidence.model_copy(deep=True) for item in contextual_evidence[:5]
        ]
        trigger_refs = [item.finding_candidate_id for item in selected]
        for conflict in conflicts:
            findings.append(self._conflict_unknown_finding(conflict, criterion_id))
            trigger_refs.append(conflict.conflict_candidate_id)
        for question in questions:
            findings.append(
                self._question_unknown_finding(
                    question,
                    criterion_id,
                    evidence=insufficient_evidence,
                )
            )
            trigger_refs.append(question.question_id)
        if not findings:
            missing = self._missing_finding(
                dimension_id,
                criterion_id,
                evidence=insufficient_evidence,
            )
            findings.append(missing)
            trigger_refs.append(missing.finding_id)

        return _CriterionResolution(
            decision=CriterionAdjudication(
                criterion_id=criterion_id,
                dimension_id=dimension_id,
                outcome=outcome,
                reason=reason,
                trigger_refs=trigger_refs,
            ),
            findings=tuple(findings),
        )

    @staticmethod
    def _resolved_finding(item: ProjectedFinding, outcome: str) -> Finding:
        gate_critical = outcome in {"blocked", "unknown"}
        criterion = CRITERION_LABELS[item.criterion_id]
        impacts = {
            "blocked": (
                f"Confirmed Fact evidence shows {criterion.lower()} is not met; "
                "this Dimension cannot proceed."
            ),
            "unknown": (
                f"The available material does not establish {criterion.lower()} as a Fact; "
                "verify this condition before full PROCEED."
            ),
            "warning": (
                f"{criterion} has a known non-blocking risk; mitigate it before "
                "higher-cost reproduction work."
            ),
            "supported": f"Fact evidence supports {criterion.lower()} for the current path.",
        }
        return item.finding.model_copy(
            update={"gate_critical": gate_critical, "readiness_impact": impacts[outcome]},
            deep=True,
        )

    @staticmethod
    def _conflict_unknown_finding(
        item: ProjectedConflict,
        criterion_id: ReadinessCriterionId,
    ) -> Finding:
        return Finding(
            finding_id=f"rule-conflict-{item.conflict_candidate_id}",
            condition=criterion_id,
            title=f"Resolve conflicting evidence for {CRITERION_LABELS[criterion_id]}",
            summary=item.conflict.summary,
            finding_type="Unknown",
            gate_critical=True,
            readiness_impact=(
                f"Conflicting evidence prevents verification of "
                f"{CRITERION_LABELS[criterion_id].lower()}; full PROCEED is withheld."
            ),
            evidence=[e.model_copy(deep=True) for e in item.conflict.sources],
        )

    @staticmethod
    def _question_unknown_finding(
        question,
        criterion_id: ReadinessCriterionId,
        *,
        evidence: list,
    ) -> Finding:
        return Finding(
            finding_id=f"rule-question-{question.question_id}",
            condition=criterion_id,
            title=f"Verify {CRITERION_LABELS[criterion_id]}",
            summary=question.missing_information,
            finding_type="Unknown",
            gate_critical=True,
            readiness_impact=(
                f"{CRITERION_LABELS[criterion_id]} cannot be verified until the "
                "requested information is supplied or collected."
            ),
            evidence=evidence,
        )

    @staticmethod
    def _missing_finding(
        dimension_id: DimensionId,
        criterion_id: ReadinessCriterionId,
        *,
        evidence: list,
    ) -> Finding:
        return Finding(
            finding_id=f"rule-missing-{criterion_id}",
            condition=criterion_id,
            title=f"Verify {CRITERION_LABELS[criterion_id]}",
            summary=(
                f"The currently collected materials contain no admitted Fact establishing "
                f"{CRITERION_LABELS[criterion_id].lower()} for {dimension_id}. "
                "Locate the smallest authoritative source for this condition and provide "
                "an exact source location."
            ),
            finding_type="Unknown",
            gate_critical=True,
            readiness_impact=(
                f"Without a source-bound Fact for {CRITERION_LABELS[criterion_id].lower()}, "
                "this Gate-critical condition remains Unknown."
            ),
            evidence=evidence,
        )

    @staticmethod
    def _dimension(
        dimension_id: DimensionId,
        resolutions: list[_CriterionResolution],
    ) -> ReadinessDimension:
        decisive = min(resolutions, key=lambda item: _OUTCOME_PRIORITY[item.decision.outcome])
        status_by_outcome = {
            "blocked": "Blocked",
            "unknown": "Unknown",
            "warning": "Warning",
            "supported": "Ready",
        }
        status = status_by_outcome[decisive.decision.outcome]
        findings = [
            finding
            for resolution in sorted(
                resolutions, key=lambda item: _OUTCOME_PRIORITY[item.decision.outcome]
            )
            for finding in resolution.findings
        ]
        # The frozen Overview requires a short explanation of this Dimension's
        # actual decisive Finding/Unknown, not the generic Rule condition that
        # produced its status.  The Rule still owns the status and impact.
        summary = decisive.findings[0].summary
        criterion = decisive.decision.criterion_id
        label = CRITERION_LABELS[criterion]
        impacts = {
            "Blocked": f"{label} blocks PROCEED until the confirmed condition is resolved.",
            "Unknown": f"{label} is Gate-critical; full PROCEED waits for its verification.",
            "Warning": f"{label} carries a known non-blocking risk before higher-cost work.",
            "Ready": f"{label} currently has no retained Gate-critical blocker.",
        }
        return ReadinessDimension(
            dimension_id=dimension_id,
            name=DIMENSION_NAMES[dimension_id],
            status=status,
            summary=summary or f"{label} requires a source-bound Finding for {dimension_id}.",
            gate_impact=impacts[status],
            findings=findings,
        )

    @staticmethod
    def _evaluation_signal(
        projection: AIAnalysisDomainProjection,
        coverage: list[EvidenceAreaCoverage] | None = None,
    ) -> EvaluationSignal | None:
        conflicts = [
            item
            for item in projection.conflicts
            if item.criterion_id is not None and item.criterion_id.startswith("evaluation.")
        ]
        questions = [
            item
            for item in projection.unresolved_questions
            if item.criterion_id is not None and item.criterion_id.startswith("evaluation.")
        ]
        coverage_item = next(
            (item for item in coverage or [] if item.area == "evaluation_conditions"), None
        )
        if not conflicts and not questions and (
            coverage_item is None or coverage_item.state == "evidence_found"
        ):
            return None

        unresolved = questions or any(
            item.disposition != "known_difference" for item in conflicts
        )
        status = "Unknown" if unresolved else "Warning"
        criterion_id = (
            conflicts[0].criterion_id if conflicts else questions[0].criterion_id
        )
        assert criterion_id is not None
        evidence = [source for item in conflicts for source in item.conflict.sources]
        summary = (
            questions[0].missing_information
            if questions
            else conflicts[0].conflict.summary
            if conflicts
            else coverage_item.summary
        )
        return EvaluationSignal(
            signal_id=(
                f"signal-{conflicts[0].conflict_candidate_id}"
                if conflicts
                else f"signal-{questions[0].question_id}"
                if questions
                else "signal-evaluation-coverage"
            ),
            status=status,
            conflict_type=DeterministicReadinessAdjudicator._evaluation_conflict_type(
                criterion_id
            ),
            summary=summary,
            evidence_refs=evidence,
            gate_impact=(
                "The authoritative evaluation protocol remains Unknown; this supports "
                "CONDITIONAL PROCEED but cannot independently produce PAUSE."
                if status == "Unknown"
                else "A known evaluation difference supports CONDITIONAL PROCEED but cannot "
                "independently produce PAUSE."
            ),
        )

    @staticmethod
    def _evaluation_conflict_type(criterion_id: str) -> EvaluationConflictType:
        return {
            "evaluation.dataset_split": "Dataset Split",
            "evaluation.metric_definition": "Metric Definition",
            "evaluation.aggregation": "Aggregation",
            "evaluation.paper_code_setting": "Paper-Code Setting",
        }.get(criterion_id, "Other")

    @staticmethod
    def _resource_unknown_signal(
        projection: AIAnalysisDomainProjection,
        coverage: list[EvidenceAreaCoverage] | None = None,
    ) -> ResourceSignal | None:
        evidence_items = [
            item.evidence
            for item in projection.evidence
            if item.criterion_id is not None and item.criterion_id.startswith("resource.")
        ]
        questions = [
            item
            for item in projection.unresolved_questions
            if item.criterion_id is not None and item.criterion_id.startswith("resource.")
        ]
        coverage_item = next(
            (item for item in coverage or [] if item.area == "resource_constraint"), None
        )
        if not evidence_items and not questions and (
            coverage_item is None or coverage_item.state == "evidence_found"
        ):
            return None
        summary = (
            questions[0].missing_information
            if questions
            else "Resource facts were located, but no deterministic minimum-to-current comparison was supplied."
            if evidence_items
            else coverage_item.summary
        )
        return ResourceSignal(
            status="Unknown",
            summary=summary,
            gate_impact=(
                "The resource comparison remains Unknown and supports CONDITIONAL PROCEED; it "
                "cannot justify Resource Blocked without an explicit deterministic shortfall."
            ),
            evidence=evidence_items[0] if evidence_items else None,
        )
