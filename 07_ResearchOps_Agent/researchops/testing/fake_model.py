"""Deterministic fake implementing both material-analysis model boundaries."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from threading import RLock
from uuid import UUID

from researchops.schemas.ai_analysis import (
    AIAnalysisInvocation,
    AIConflictFindingInvocation,
    AIEvidenceExtractionInvocation,
    AIEvidenceFindingDraftInvocation,
    ConflictFindingAnalysisInput,
    EvidenceFindingInput,
    MaterialBundle,
)


class FakeMaterialAnalysisModel:
    """Return queued invocations or errors and record inspected bundle identities."""

    def __init__(self, outcomes: Iterable[AIAnalysisInvocation | Exception]) -> None:
        self._outcomes = deque(outcomes)
        self._lock = RLock()
        self.bundle_ids: list[UUID] = []

    @property
    def call_count(self) -> int:
        return len(self.bundle_ids)

    def analyze(self, bundle: MaterialBundle) -> AIAnalysisInvocation:
        with self._lock:
            self.bundle_ids.append(bundle.bundle_id)
            if not self._outcomes:
                raise AssertionError("FakeMaterialAnalysisModel 没有剩余的预设结果")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome.model_copy(deep=True)

    async def analyze_async(self, bundle: MaterialBundle) -> AIAnalysisInvocation:
        await asyncio.sleep(0)
        return self.analyze(bundle)


class FakeEvidenceFindingDraftModel:
    """Current local-phase fake; queued outputs are isolated across callers."""

    def __init__(self, outcomes: Iterable[AIEvidenceFindingDraftInvocation | Exception]):
        self._outcomes = deque(outcomes)
        self._lock = RLock()
        self.bundle_ids: list[UUID] = []

    def draft_evidence_findings(self, context: EvidenceFindingInput):
        with self._lock:
            self.bundle_ids.append(context.bundle.bundle_id)
            if not self._outcomes:
                raise AssertionError("FakeEvidenceFindingDraftModel has no remaining outcome")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome.model_copy(deep=True)

    async def draft_evidence_findings_async(self, context: EvidenceFindingInput):
        await asyncio.sleep(0)
        return self.draft_evidence_findings(context)


class FakeEvidenceExtractionModel:
    """Evidence-stage fake that cannot return Conflict or Finding output."""

    def __init__(
        self,
        outcomes: Iterable[AIEvidenceExtractionInvocation | Exception],
    ) -> None:
        self._outcomes = deque(outcomes)
        self._lock = RLock()
        self.bundle_ids: list[UUID] = []

    @property
    def call_count(self) -> int:
        return len(self.bundle_ids)

    def extract_evidence(self, bundle: MaterialBundle) -> AIEvidenceExtractionInvocation:
        with self._lock:
            self.bundle_ids.append(bundle.bundle_id)
            if not self._outcomes:
                raise AssertionError("FakeEvidenceExtractionModel 没有剩余的预设结果")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome.model_copy(deep=True)

    async def extract_evidence_async(
        self,
        bundle: MaterialBundle,
    ) -> AIEvidenceExtractionInvocation:
        await asyncio.sleep(0)
        return self.extract_evidence(bundle)


class FakeConflictFindingAnalysisModel:
    """Second-stage fake limited to validated Evidence context."""

    def __init__(
        self,
        outcomes: Iterable[AIConflictFindingInvocation | Exception],
    ) -> None:
        self._outcomes = deque(outcomes)
        self._lock = RLock()
        self.bundle_ids: list[UUID] = []
        self.extraction_ids: list[UUID] = []

    @property
    def call_count(self) -> int:
        return len(self.bundle_ids)

    def analyze_conflicts_findings(
        self,
        context: ConflictFindingAnalysisInput,
    ) -> AIConflictFindingInvocation:
        with self._lock:
            self.bundle_ids.append(context.bundle_id)
            self.extraction_ids.append(context.evidence_extraction_id)
            if not self._outcomes:
                raise AssertionError("FakeConflictFindingAnalysisModel 没有剩余的预设结果")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome.model_copy(deep=True)

    async def analyze_conflicts_findings_async(
        self,
        context: ConflictFindingAnalysisInput,
    ) -> AIConflictFindingInvocation:
        await asyncio.sleep(0)
        return self.analyze_conflicts_findings(context)
