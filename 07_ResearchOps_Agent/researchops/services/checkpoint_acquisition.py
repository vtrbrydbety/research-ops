"""Deterministic authorization and ordering for checkpoint acquisition.

The model may identify a missing checkpoint, but it may not choose an arbitrary
download URL.  This policy accepts only a release asset belonging to the
collected official repository, or an exact external URL that the collected
README explicitly declares as a weight/checkpoint entry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from researchops.schemas import MaterialBundle, ToolRequest

CheckpointAcquisitionKind = Literal["official_release", "readme_external", "denied"]


@dataclass(frozen=True, slots=True)
class CheckpointAcquisitionAuthorization:
    """Rule-owned authorization of one checkpoint probe request."""

    kind: CheckpointAcquisitionKind
    detail: str

    @property
    def priority(self) -> int:
        return {"official_release": 0, "readme_external": 1, "denied": 2}[self.kind]


class OfficialCheckpointAcquisitionPolicy:
    """Validate official checkpoint origins from collected repository material."""

    manifest_path = ".researchops/repository-material-manifest.json"

    def authorize(
        self,
        bundle: MaterialBundle,
        request: ToolRequest,
    ) -> CheckpointAcquisitionAuthorization:
        if request.tool_name != "probe_checkpoint_access" or request.url is None:
            raise ValueError("Checkpoint acquisition policy only accepts checkpoint probe requests")

        url = str(request.url)
        repositories, readme_references = self._collected_origins(bundle)
        if self._is_official_github_release(url, repositories):
            return CheckpointAcquisitionAuthorization(
                "official_release",
                "Authorized as an official GitHub Release asset of the collected repository.",
            )
        if url in readme_references:
            return CheckpointAcquisitionAuthorization(
                "readme_external",
                "Authorized only because this exact URL is a locatable checkpoint entry in the collected README.",
            )
        return CheckpointAcquisitionAuthorization(
            "denied",
            "Checkpoint probe denied: the URL is neither an official repository Release asset nor an exact collected README checkpoint link.",
        )

    def _collected_origins(self, bundle: MaterialBundle) -> tuple[set[tuple[str, str]], set[str]]:
        repositories: set[tuple[str, str]] = set()
        readme_references: set[str] = set()
        for source in bundle.sources:
            if source.source_path != self.manifest_path:
                continue
            try:
                manifest = json.loads(source.content)
            except json.JSONDecodeError:
                continue
            repository_url = manifest.get("repository_url")
            repository = self._github_repository(repository_url)
            if repository is not None:
                repositories.add(repository)
            for reference in manifest.get("external_asset_references", []):
                if not isinstance(reference, dict):
                    continue
                url = reference.get("url")
                path = reference.get("source_path")
                line = reference.get("line_number")
                if not (
                    isinstance(url, str)
                    and isinstance(path, str)
                    and path.casefold().startswith("readme")
                    and isinstance(line, int)
                    and self._readme_reference_is_locatable(bundle, path, line, url)
                ):
                    continue
                readme_references.add(url)
        # A repository target remains a safe first-party origin even before the
        # manifest source is included in a narrowly-built bundle.
        target_repository = self._github_repository(str(bundle.target.canonical_url))
        if bundle.target.target_type == "repository" and target_repository is not None:
            repositories.add(target_repository)
        return repositories, readme_references

    @staticmethod
    def _github_repository(url: object) -> tuple[str, str] | None:
        if not isinstance(url, str):
            return None
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.scheme != "https" or parsed.hostname != "github.com" or len(parts) < 2:
            return None
        return parts[0].casefold(), parts[1].casefold()

    @classmethod
    def _is_official_github_release(
        cls,
        url: str,
        repositories: set[tuple[str, str]],
    ) -> bool:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or len(parts) < 6
            or parts[2:4] != ["releases", "download"]
        ):
            return False
        return (parts[0].casefold(), parts[1].casefold()) in repositories

    @staticmethod
    def _readme_reference_is_locatable(
        bundle: MaterialBundle,
        source_path: str,
        line_number: int,
        url: str,
    ) -> bool:
        return any(
            source.source_path == source_path
            and source.line_start <= line_number <= source.line_end
            and url in source.content
            for source in bundle.sources
        )
