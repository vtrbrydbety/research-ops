"""Bounded, read-only Hugging Face card collection.

This connector is deliberately narrower than a general web reader: it accepts
only public Hugging Face model or dataset card URLs, calls the corresponding
fixed Hub API endpoint, and returns compact metadata as untrusted material.
It never downloads artifacts, follows arbitrary redirects, or sends a token.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import unquote, urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.schemas import CollectedMaterial


class HuggingFaceMaterialCollectionError(RuntimeError):
    """A public Hugging Face card could not be collected safely."""


@dataclass(frozen=True, slots=True)
class HuggingFaceCardReference:
    """A canonical public Hub card identity accepted by the connector."""

    kind: Literal["model", "dataset"]
    repository_id: str
    canonical_url: str


class HuggingFaceMaterialCollector(Protocol):
    """Read-only connector boundary used by the deterministic tool executor."""

    def collect(self, url: str) -> CollectedMaterial: ...


class PublicHuggingFaceMaterialCollector:
    """Collect one bounded public model or dataset card through a fixed API."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        proxy: str | None = None,
    ) -> None:
        self._owns_client = client is None
        proxy_url = proxy if proxy is not None else os.getenv("RESEARCHOPS_HTTPS_PROXY")
        self.client = client or outbound_client(
            base_url="https://huggingface.co",
            headers={"User-Agent": "ResearchOps-Agent/0.1"},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
            proxy=proxy_url,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def collect(self, url: str) -> CollectedMaterial:
        reference = self.parse_public_card_url(url)
        endpoint = f"/api/{'models' if reference.kind == 'model' else 'datasets'}/{reference.repository_id}"
        try:
            response = self.client.get(endpoint)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HuggingFaceMaterialCollectionError(
                "Public Hugging Face card metadata could not be collected"
            ) from exc
        if not isinstance(payload, dict):
            raise HuggingFaceMaterialCollectionError(
                "Public Hugging Face card metadata has an invalid shape"
            )

        safe_payload = self._bounded_payload(payload, reference)
        source_kind = "Dataset Page" if reference.kind == "dataset" else "Checkpoint-Release"
        path_kind = "datasets" if reference.kind == "dataset" else "models"
        return CollectedMaterial(
            material_type=source_kind,
            title=f"Hugging Face {reference.kind} card: {reference.repository_id}",
            source_path=f".researchops/huggingface/{path_kind}/{reference.repository_id}.json",
            source_url=reference.canonical_url,
            content=json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True),
            access_scope="public",
            priority=94,
        )

    @staticmethod
    def parse_public_card_url(url: str) -> HuggingFaceCardReference:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "huggingface.co",
            "www.huggingface.co",
        }:
            raise HuggingFaceMaterialCollectionError(
                "Only HTTPS huggingface.co model or dataset card URLs are allowed"
            )
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise HuggingFaceMaterialCollectionError(
                "Hugging Face card URL must not contain credentials, query parameters, or fragments"
            )
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if parts[:1] == ["datasets"]:
            kind: Literal["model", "dataset"] = "dataset"
            parts = parts[1:]
        else:
            kind = "model"
        if len(parts) != 2 or any(not _is_safe_segment(part) for part in parts):
            raise HuggingFaceMaterialCollectionError(
                "Hugging Face URL must identify exactly one public owner/repository card"
            )
        repository_id = "/".join(parts)
        prefix = "datasets/" if kind == "dataset" else ""
        return HuggingFaceCardReference(
            kind=kind,
            repository_id=repository_id,
            canonical_url=f"https://huggingface.co/{prefix}{repository_id}",
        )

    @staticmethod
    def _bounded_payload(
        payload: dict[str, object],
        reference: HuggingFaceCardReference,
    ) -> dict[str, object]:
        """Keep metadata useful for evidence while bounding arbitrary card content."""

        card_data = payload.get("cardData")
        return {
            "connector": "huggingface_public_card",
            "kind": reference.kind,
            "repository_id": reference.repository_id,
            "canonical_url": reference.canonical_url,
            "id": _bounded_value(payload.get("id"), 500),
            "sha": _bounded_value(payload.get("sha"), 500),
            "private": payload.get("private") is True,
            "gated": _bounded_value(payload.get("gated"), 100),
            "disabled": payload.get("disabled") is True,
            "tags": _bounded_list(payload.get("tags"), 64, 300),
            "siblings": _bounded_siblings(payload.get("siblings")),
            "card_data": _bounded_json_value(card_data, 12_000),
        }


def _is_safe_segment(value: str) -> bool:
    return bool(value) and all(char.isalnum() or char in {"-", "_", "."} for char in value)


def _bounded_value(value: object, maximum: int) -> object:
    return value[:maximum] if isinstance(value, str) else value


def _bounded_list(value: object, maximum_items: int, maximum_chars: int) -> list[object]:
    if not isinstance(value, list):
        return []
    return [_bounded_value(item, maximum_chars) for item in value[:maximum_items]]


def _bounded_siblings(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, object]] = []
    for item in value[:128]:
        if isinstance(item, dict) and isinstance(item.get("rfilename"), str):
            result.append({"rfilename": item["rfilename"][:500]})
    return result


def _bounded_json_value(value: object, maximum_chars: int) -> object:
    """Bound nested arbitrary metadata without treating it as trusted instruction."""

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(encoded) <= maximum_chars:
        return value
    return {"truncated": True, "preview": encoded[:maximum_chars]}
