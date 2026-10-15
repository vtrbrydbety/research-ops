"""Deterministic, bounded construction of model-readable material bundles."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from researchops.core.config import Settings, get_settings
from researchops.schemas.ai_analysis import (
    CollectedMaterial,
    MaterialBuildOmission,
    MaterialBundle,
    MaterialBundleBuildReport,
    MaterialBundleBuildResult,
    MaterialSource,
)
from researchops.schemas.readiness import MaterialType, ResolvedTarget
from researchops.services.environment_facts import EnvironmentFacts
from researchops.services.paper_materials import PaperMaterials
from researchops.services.repository_materials import RepositoryMaterials, RepositoryTextFile


class MaterialContextError(RuntimeError):
    """No valid bounded context could be built from the supplied materials."""


@dataclass(frozen=True, slots=True)
class _ContentChunk:
    content: str
    index: int
    count: int
    line_start: int
    line_end: int


_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_LABELED_SECRET_PATTERN = re.compile(
    r"(?im)(?P<prefix>\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)"
    r"\b\s*[:=]\s*[\"']?)(?P<value>[^\s\"'#]+)(?P<suffix>[\"']?)"
)
_BEARER_PATTERN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{12,}")
_KNOWN_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})(?![A-Za-z0-9])"
)
_URL_IN_TEXT_PATTERN = re.compile(r"https?://[^\s)\]}>\"']+")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "key",
    "password",
    "sig",
    "signature",
    "token",
}


class MaterialBundleBuilder:
    """Convert connector output into a deterministic, auditable MaterialBundle."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        max_total_chars: int | None = None,
        max_source_chars: int | None = None,
        max_sources: int | None = None,
        max_candidate_chars: int | None = None,
    ) -> None:
        config = settings or get_settings()
        self.max_total_chars = (
            max_total_chars if max_total_chars is not None else config.llm_context_max_total_chars
        )
        self.max_source_chars = (
            max_source_chars
            if max_source_chars is not None
            else config.llm_context_max_source_chars
        )
        self.max_sources = (
            max_sources if max_sources is not None else config.llm_context_max_sources
        )
        self.max_candidate_chars = (
            max_candidate_chars
            if max_candidate_chars is not None
            else config.llm_context_max_candidate_chars
        )
        if not 1 <= self.max_total_chars <= 500_000:
            raise ValueError("max_total_chars 必须在 1 到 500000 之间")
        if not 1 <= self.max_source_chars <= 100_000:
            raise ValueError("max_source_chars 必须在 1 到 100000 之间")
        if not 1 <= self.max_sources <= 64:
            raise ValueError("max_sources 必须在 1 到 64 之间")
        if not 1 <= self.max_candidate_chars <= 2_000_000:
            raise ValueError("max_candidate_chars 必须在 1 到 2000000 之间")

    def build(
        self,
        target: ResolvedTarget,
        materials: Iterable[CollectedMaterial],
    ) -> MaterialBundleBuildResult:
        """Filter, chunk, deduplicate, bound, hash, and identify supplied sources."""
        candidates = list(materials)
        ordered = sorted(
            candidates,
            key=lambda item: (-item.priority, item.source_path.casefold(), item.title.casefold()),
        )
        sources: list[MaterialSource] = []
        omissions: list[MaterialBuildOmission] = []
        truncated_source_ids: list[str] = []
        redacted_source_ids: list[str] = []
        seen_content_hashes: set[str] = set()
        included_chars = 0
        included_material_count = 0
        generated_chunk_count = 0
        omitted_chunk_count = 0

        for candidate in ordered:
            if len(candidate.content) > self.max_candidate_chars:
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason="oversized")
                )
                continue
            if self._looks_binary(candidate.content):
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason="binary")
                )
                continue

            normalized = self._normalize_content(candidate.content)
            if not normalized.strip():
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason="empty")
                )
                continue

            original_hash = self._hash(normalized)
            if original_hash in seen_content_hashes:
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason="duplicate")
                )
                continue
            seen_content_hashes.add(original_hash)

            filtered, redaction_count = self._redact_sensitive_content(normalized)
            if not filtered.strip():
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason="empty")
                )
                continue
            chunks = self._chunk_content(filtered, self.max_source_chars)
            generated_chunk_count += len(chunks)
            included_for_material = 0

            for chunk in chunks:
                if len(sources) >= self.max_sources:
                    break
                remaining = self.max_total_chars - included_chars
                if remaining <= 0:
                    break

                bounded_content = self._bounded_prefix(chunk.content, remaining).strip()
                if not bounded_content.strip():
                    break

                is_truncated = len(bounded_content) < len(filtered) or len(chunks) > 1
                source_id = self._source_id(candidate, original_hash, chunk.index)
                source = MaterialSource(
                    source_id=source_id,
                    material_type=candidate.material_type,
                    title=self._sanitize_local_paths(candidate.title),
                    source_path=self._sanitize_local_paths(candidate.source_path),
                    source_url=self._sanitize_url(candidate.source_url),
                    content=bounded_content,
                    content_sha256=self._hash(bounded_content),
                    original_content_sha256=original_hash,
                    original_char_count=len(normalized),
                    is_truncated=is_truncated,
                    is_redacted=redaction_count > 0,
                    redaction_count=redaction_count,
                    chunk_index=chunk.index,
                    chunk_count=chunk.count,
                    line_start=chunk.line_start,
                    line_end=self._bounded_line_end(chunk.line_start, bounded_content),
                    access_scope=candidate.access_scope,
                )
                sources.append(source)
                included_for_material += 1
                included_chars += len(bounded_content)
                if is_truncated:
                    truncated_source_ids.append(source_id)
                if redaction_count:
                    redacted_source_ids.append(source_id)

            omitted_chunk_count += len(chunks) - included_for_material
            if included_for_material:
                included_material_count += 1
            else:
                reason = "source_limit" if len(sources) >= self.max_sources else "total_limit"
                omissions.append(
                    MaterialBuildOmission(source_path=candidate.source_path, reason=reason)
                )

        if not sources:
            raise MaterialContextError("没有可用于模型分析的非空有界材料。")

        bundle = MaterialBundle(
            bundle_id=uuid4(),
            target=target,
            assembled_at=self._assembled_at(),
            sources=sources,
        )
        report = MaterialBundleBuildReport(
            candidate_source_count=len(candidates),
            included_source_count=len(sources),
            included_material_count=included_material_count,
            generated_chunk_count=generated_chunk_count,
            omitted_chunk_count=omitted_chunk_count,
            included_char_count=included_chars,
            truncated_source_ids=truncated_source_ids,
            redacted_source_ids=redacted_source_ids,
            omissions=omissions,
        )
        return MaterialBundleBuildResult(bundle=bundle, report=report)

    def from_repository(
        self,
        target: ResolvedTarget,
        materials: RepositoryMaterials,
        *,
        environment_facts: EnvironmentFacts | None = None,
    ) -> MaterialBundleBuildResult:
        """Adapt existing GitHub collector output without another network request."""
        collected: list[CollectedMaterial] = []
        if materials.readme is not None:
            collected.append(self._repository_file(materials.readme, "README", priority=100))

        collected.append(
            CollectedMaterial(
                material_type="Repository",
                title="Repository material manifest",
                source_path=".researchops/repository-material-manifest.json",
                source_url=materials.repository_url,
                content=self._repository_manifest(materials),
                access_scope="public",
                priority=95,
            )
        )
        collected.extend(
            self._repository_file(item, "Config", priority=90)
            for item in materials.dependency_files
        )
        collected.extend(
            self._repository_file(item, "Config", priority=80)
            for item in materials.evaluation_files
        )
        if environment_facts is not None:
            collected.append(self._environment_material(environment_facts))
        return self.build(target, collected)

    def from_paper(
        self,
        target: ResolvedTarget,
        materials: PaperMaterials,
        *,
        environment_facts: EnvironmentFacts | None = None,
    ) -> MaterialBundleBuildResult:
        """Adapt public paper or project-page metadata into one traceable source."""
        collected_materials = [self._paper_material(materials)]
        if environment_facts is not None:
            collected_materials.append(self._environment_material(environment_facts))
        return self.build(target, collected_materials)

    def from_paper_and_repository(
        self,
        target: ResolvedTarget,
        paper: PaperMaterials,
        repository: RepositoryMaterials,
        *,
        environment_facts: EnvironmentFacts | None = None,
    ) -> MaterialBundleBuildResult:
        """Build one bounded bundle when a paper explicitly links a public Repository."""

        collected = [self._paper_material(paper, priority=110)]
        if repository.readme is not None:
            collected.append(self._repository_file(repository.readme, "README", priority=100))
        collected.append(
            CollectedMaterial(
                material_type="Repository",
                title="Repository material manifest",
                source_path=".researchops/repository-material-manifest.json",
                source_url=repository.repository_url,
                content=self._repository_manifest(repository),
                access_scope="public",
                priority=95,
            )
        )
        collected.extend(
            self._repository_file(item, "Config", priority=90)
            for item in repository.dependency_files
        )
        collected.extend(
            self._repository_file(item, "Config", priority=80)
            for item in repository.evaluation_files
        )
        if environment_facts is not None:
            collected.append(self._environment_material(environment_facts))
        return self.build(target, collected)

    def from_environment(
        self,
        target: ResolvedTarget,
        facts: EnvironmentFacts,
    ) -> MaterialBundleBuildResult:
        """Build a bundle from authorized or user-supplied environment facts."""
        return self.build(target, [self._environment_material(facts)])

    @staticmethod
    def _paper_material(
        materials: PaperMaterials,
        *,
        priority: int = 100,
    ) -> CollectedMaterial:
        repository_lines = "\n".join(f"- {url}" for url in materials.repository_urls) or "- none"
        content = (
            f"Title: {materials.title}\n"
            f"Identifier: {materials.identifier}\n"
            f"Publisher: {materials.publisher}\n"
            "Abstract or visible text:\n"
            f"{materials.abstract or '[not available]'}\n"
            "Repository URLs:\n"
            f"{repository_lines}"
        )
        return CollectedMaterial(
            material_type=materials.material_type,
            title=materials.title,
            source_path=(
                f"metadata/{MaterialBundleBuilder._safe_path_component(materials.identifier)}.txt"
            ),
            source_url=materials.source_url,
            content=content,
            access_scope="public",
            priority=priority,
        )

    @staticmethod
    def _repository_file(
        material: RepositoryTextFile,
        material_type: MaterialType,
        *,
        priority: int,
    ) -> CollectedMaterial:
        return CollectedMaterial(
            material_type=material_type,
            title=material.path,
            source_path=material.path,
            source_url=material.html_url,
            content=material.text,
            access_scope="public",
            priority=priority,
        )

    @staticmethod
    def _repository_manifest(materials: RepositoryMaterials) -> str:
        payload: dict[str, Any] = {
            "repository_url": materials.repository_url,
            "default_branch": materials.default_branch,
            "relevant_paths": list(materials.relevant_paths),
            "external_asset_references": [
                {
                    "url": item.url,
                    "source_path": item.source_path,
                    "line_number": item.line_number,
                    "excerpt": item.excerpt,
                }
                for item in materials.external_asset_references
            ],
            "dataset_references": [
                {
                    "name": item.name,
                    "url": item.url,
                    "source_path": item.source_path,
                    "line_number": item.line_number,
                    "excerpt": item.excerpt,
                }
                for item in materials.dataset_references
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    @staticmethod
    def _environment_material(facts: EnvironmentFacts) -> CollectedMaterial:
        access_scope = "authorized_local" if facts.source_mode == "readonly" else "user_provided"
        return CollectedMaterial(
            material_type="Other",
            title="Current environment facts",
            source_path=".researchops/environment-facts.json",
            content=json.dumps(asdict(facts), ensure_ascii=False, indent=2, sort_keys=True),
            access_scope=access_scope,
            priority=99,
        )

    @staticmethod
    def _normalize_content(content: str) -> str:
        return content.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()

    @staticmethod
    def _bounded_prefix(content: str, limit: int) -> str:
        if len(content) <= limit:
            return content
        prefix = content[:limit]
        last_newline = prefix.rfind("\n")
        if last_newline >= max(1, limit // 2):
            return prefix[:last_newline].rstrip()
        return prefix.rstrip()

    @staticmethod
    def _source_id(material: CollectedMaterial, original_hash: str, chunk_index: int) -> str:
        type_slug = re.sub(r"[^a-z0-9]+", "-", material.material_type.casefold()).strip("-")
        identity = f"{material.source_path.casefold()}\0{original_hash}\0{chunk_index}".encode()
        identity_hash = sha256(identity).hexdigest()[:16]
        return f"src-{type_slug or 'material'}-{identity_hash}"

    @staticmethod
    def _chunk_content(content: str, limit: int) -> list[_ContentChunk]:
        provisional: list[tuple[str, int, int]] = []
        start = 0
        while start < len(content):
            end = min(start + limit, len(content))
            if end < len(content):
                newline = content.rfind("\n", start, end)
                if newline >= start + max(1, limit // 2):
                    end = newline + 1
            chunk_content = content[start:end]
            line_start = content.count("\n", 0, start) + 1
            line_end = MaterialBundleBuilder._bounded_line_end(line_start, chunk_content)
            provisional.append((chunk_content, line_start, line_end))
            start = end

        count = len(provisional)
        return [
            _ContentChunk(
                content=chunk_content,
                index=index,
                count=count,
                line_start=line_start,
                line_end=line_end,
            )
            for index, (chunk_content, line_start, line_end) in enumerate(provisional, start=1)
        ]

    @staticmethod
    def _bounded_line_end(line_start: int, content: str) -> int:
        if not content:
            return line_start
        return line_start + content.count("\n", 0, len(content) - 1)

    @staticmethod
    def _looks_binary(content: str) -> bool:
        if "\x00" in content:
            return True
        if not content:
            return False
        control_count = sum(
            1 for character in content if ord(character) < 32 and character not in "\t\n\r"
        )
        replacement_count = content.count("\ufffd")
        return (control_count + replacement_count) / len(content) > 0.05

    @staticmethod
    def _redact_sensitive_content(content: str) -> tuple[str, int]:
        redaction_count = 0

        def private_key_replacement(match: re.Match[str]) -> str:
            nonlocal redaction_count
            redaction_count += 1
            return "[REDACTED:PRIVATE_KEY]" + "\n" * match.group(0).count("\n")

        def labeled_replacement(match: re.Match[str]) -> str:
            nonlocal redaction_count
            redaction_count += 1
            return f"{match.group('prefix')}[REDACTED:SECRET]{match.group('suffix')}"

        def bearer_replacement(match: re.Match[str]) -> str:
            nonlocal redaction_count
            redaction_count += 1
            return f"{match.group(1)}[REDACTED:TOKEN]"

        def token_replacement(_: re.Match[str]) -> str:
            nonlocal redaction_count
            redaction_count += 1
            return "[REDACTED:TOKEN]"

        def url_replacement(match: re.Match[str]) -> str:
            nonlocal redaction_count
            original = match.group(0)
            sanitized = MaterialBundleBuilder._sanitize_url(original) or original
            if sanitized != original:
                redaction_count += 1
            return sanitized

        filtered = _PRIVATE_KEY_PATTERN.sub(private_key_replacement, content)
        filtered = _LABELED_SECRET_PATTERN.sub(labeled_replacement, filtered)
        filtered = _BEARER_PATTERN.sub(bearer_replacement, filtered)
        filtered = _KNOWN_TOKEN_PATTERN.sub(token_replacement, filtered)
        filtered = _URL_IN_TEXT_PATTERN.sub(url_replacement, filtered)
        return filtered, redaction_count

    @staticmethod
    def _sanitize_local_paths(value: str) -> str:
        home = str(Path.home())
        sanitized = re.sub(re.escape(home), "%USERPROFILE%", value, flags=re.IGNORECASE)
        sanitized = re.sub(
            r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s]+",
            "%USERPROFILE%",
            sanitized,
        )
        return re.sub(r"/home/[^/\s]+", "$HOME", sanitized)

    @staticmethod
    def _sanitize_url(value: object | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(str(value))
        hostname = parts.hostname or ""
        netloc = hostname
        if parts.port is not None:
            netloc = f"{netloc}:{parts.port}"
        query = urlencode(
            [
                (key, "[REDACTED]" if key.casefold() in _SENSITIVE_QUERY_KEYS else item_value)
                for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
            ]
        )
        return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))

    @staticmethod
    def _safe_path_component(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
        return normalized[:200] or "material"

    @staticmethod
    def _hash(content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _assembled_at() -> datetime:
        return datetime.now(UTC)
