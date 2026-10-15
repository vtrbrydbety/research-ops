"""External URL provenance and deterministic access-probe validation tests."""

from uuid import uuid4

from researchops.schemas import (
    AIAnalysisResult,
    CollectedMaterial,
    EvidenceCandidate,
    ResolvedTarget,
    SourceLocator,
)
from researchops.services import (
    DatasetAccessProbeResult,
    DeterministicEvidenceRuleValidator,
    ExternalAssetProbeResult,
    MaterialBundleBuilder,
)


class _DatasetProbe:
    def __init__(self, state: str) -> None:
        self.state = state
        self.urls: list[str] = []

    def probe(self, url: str) -> DatasetAccessProbeResult:
        self.urls.append(url)
        return DatasetAccessProbeResult(
            source_url=url,
            final_url=url,
            state=self.state,
            detail=f"synthetic dataset probe: {self.state}",
        )


class _AssetProbe:
    def __init__(self, state: str) -> None:
        self.state = state
        self.urls: list[str] = []

    def probe(self, url: str) -> ExternalAssetProbeResult:
        self.urls.append(url)
        return ExternalAssetProbeResult(
            source_url=url,
            final_url=url,
            accessible=self.state == "verified_public",
            state=self.state,
            detail=f"synthetic checkpoint probe: {self.state}",
        )


def _target() -> ResolvedTarget:
    return ResolvedTarget(
        target_type="repository",
        source_entry="https://github.com/example/project",
        display_name="example/project",
        canonical_id="github:example/project",
        canonical_url="https://github.com/example/project",
        resolution_method="direct_url",
    )


def _validate(
    *,
    source_text: str,
    quote: str,
    claim: str,
    condition_key: str,
    dataset_state: str = "public_download",
    asset_state: str = "verified_public",
    access_scope: str = "public",
    criterion_id: str | None = None,
):
    bundle = (
        MaterialBundleBuilder()
        .build(
            _target(),
            [
                CollectedMaterial(
                    material_type="README",
                    title="README",
                    source_path="README.md",
                    content=source_text,
                    access_scope=access_scope,
                    priority=100,
                )
            ],
        )
        .bundle
    )
    source = bundle.sources[0]
    candidate = EvidenceCandidate(
        candidate_id="evidence-external-access",
        condition_key=condition_key,
        criterion_id=criterion_id,
        dimension_ids=["RD-01" if "data" in condition_key else "RD-03"],
        evidence_type="Fact",
        claim=claim,
        locator=SourceLocator(
            source_id=source.source_id,
            location="README.md line 1",
            line_start=1,
            line_end=1,
        ),
        quote=quote,
        confidence=0.9,
        rationale="The model interpreted a documented external entry.",
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One external entry was proposed.",
        examined_source_ids=[source.source_id],
        evidence_candidates=[candidate],
    )
    dataset_probe = _DatasetProbe(dataset_state)
    asset_probe = _AssetProbe(asset_state)
    result = (
        DeterministicEvidenceRuleValidator(
            dataset_probe=dataset_probe,
            asset_probe=asset_probe,
        )
        .validate(bundle, analysis)
        .evidence_results[0]
    )
    return result, dataset_probe, asset_probe


def test_public_dataset_download_is_accepted_with_probe_trace() -> None:
    url = "https://zenodo.org/records/123/files/data.zip"
    result, probe, _ = _validate(
        source_text=f"Dataset: {url}",
        quote=f"Dataset: {url}",
        claim=f"The dataset is publicly downloadable from {url}",
        condition_key="dataset.access",
    )

    assert result.decision == "accepted"
    assert result.url_membership_verified is True
    assert result.external_verifications[0].state == "verified_public"
    assert probe.urls == [url]


def test_public_dataset_page_does_not_prove_artifact_access() -> None:
    url = "https://zenodo.org/records/123"
    result, _, _ = _validate(
        source_text=f"Dataset: {url}",
        quote=f"Dataset: {url}",
        claim=f"The dataset is publicly downloadable from {url}",
        condition_key="dataset.access",
        dataset_state="public_page",
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Unknown"
    assert result.external_verifications[0].state == "public_page_only"
    assert result.issues[0].code == "external_access_unconfirmed"


def test_dataset_transport_failure_stays_distinct_from_inaccessibility() -> None:
    url = "https://zenodo.org/records/123/files/data.zip"
    result, _, _ = _validate(
        source_text=f"Dataset: {url}",
        quote=f"Dataset: {url}",
        claim=f"The dataset is publicly downloadable from {url}",
        condition_key="dataset.access",
        dataset_state="unreachable",
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Unknown"
    assert result.external_verifications[0].state == "acquisition_failure"
    assert result.issues[0].code == "external_acquisition_failure"


def test_confirmed_inaccessible_dataset_rejects_public_access_claim() -> None:
    url = "https://zenodo.org/records/missing"
    result, _, _ = _validate(
        source_text=f"Dataset: {url}",
        quote=f"Dataset: {url}",
        claim=f"The dataset is publicly downloadable from {url}",
        condition_key="dataset.access",
        dataset_state="verified_inaccessible",
    )

    assert result.decision == "rejected"
    assert result.external_verifications[0].state == "verified_inaccessible"
    assert result.issues[0].code == "external_access_inaccessible"


def test_confirmed_inaccessible_checkpoint_rejects_public_access_claim() -> None:
    url = "https://drive.google.com/file/d/checkpoint-id/view"
    result, _, probe = _validate(
        source_text=f"Checkpoint: {url}",
        quote=f"Checkpoint: {url}",
        claim=f"The checkpoint is publicly accessible from {url}",
        condition_key="checkpoint.access",
        asset_state="verified_inaccessible",
    )

    assert result.decision == "rejected"
    assert result.external_verifications[0].state == "verified_inaccessible"
    assert result.issues[0].code == "external_access_inaccessible"
    assert probe.urls == [url]


def test_unsupported_checkpoint_host_is_unknown_without_network_probe() -> None:
    url = "https://example.org/checkpoint.bin"
    result, _, probe = _validate(
        source_text=f"Checkpoint: {url}",
        quote=f"Checkpoint: {url}",
        claim=f"The checkpoint is publicly accessible from {url}",
        condition_key="checkpoint.access",
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Unknown"
    assert result.external_verifications[0].state == "unsupported"
    assert result.issues[0].code == "external_probe_unsupported"
    assert probe.urls == []


def test_url_claim_not_present_in_collected_material_is_rejected() -> None:
    documented = "https://zenodo.org/records/123"
    invented = "https://zenodo.org/records/999"
    result, probe, _ = _validate(
        source_text=f"Dataset: {documented}",
        quote=f"Dataset: {documented}",
        claim=f"The dataset is publicly downloadable from {invented}",
        condition_key="dataset.access",
    )

    assert result.decision == "rejected"
    assert result.url_membership_verified is False
    assert result.issues[0].code == "url_not_in_collected_sources"
    assert probe.urls == []


def test_customer_dataset_access_confirmation_is_accepted_without_public_probe() -> None:
    statement = "I can access the dataset required for this assessment."
    result, dataset_probe, _ = _validate(
        source_text=statement,
        quote=statement,
        claim="The customer confirms access to the required dataset.",
        condition_key="dataset.access",
        access_scope="user_provided",
        criterion_id="rd01.dataset_access",
    )

    assert result.decision == "accepted"
    assert result.resulting_type == "Fact"
    assert result.external_verifications == []
    assert dataset_probe.urls == []


def test_customer_public_access_claim_still_requires_deterministic_probe() -> None:
    statement = "The required dataset is publicly accessible."
    result, dataset_probe, _ = _validate(
        source_text=statement,
        quote=statement,
        claim="The required dataset is publicly accessible.",
        condition_key="dataset.access",
        access_scope="user_provided",
        criterion_id="rd01.dataset_access",
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Unknown"
    assert result.issues[0].code == "external_access_unconfirmed"
    assert dataset_probe.urls == []
