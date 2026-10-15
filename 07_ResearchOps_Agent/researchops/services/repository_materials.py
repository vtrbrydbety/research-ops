"""公开 GitHub Repository 的受限只读材料采集。"""

import base64
import binascii
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import quote, unquote, urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.schemas import ResolvedTarget

GITHUB_ID_PATTERN = re.compile(
    r"^github:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repository>[A-Za-z0-9_.-]+)$"
)
DEPENDENCY_FILE_NAMES = {
    "dockerfile",
    "environment.yml",
    "environment.yaml",
    "package-list.txt",
    "pipfile",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
}
RELEVANT_PATH_TERMS = (
    "checkpoint",
    "config",
    "data",
    "environment",
    "license",
    "package",
    "readme",
    "requirement",
    "weight",
)
URL_PATTERN = re.compile(r"https://[^\s)>\]]+", re.IGNORECASE)
WEIGHT_REFERENCE_TERMS = ("checkpoint", "model weight", "pretrained", "weight file")
DATASET_REFERENCE_TERMS = ("dataset", "download data", "prepare data")
EVALUATION_FILE_EXTENSIONS = {".cfg", ".ini", ".json", ".py", ".toml", ".txt", ".yaml", ".yml"}
EVALUATION_PATH_TERMS = (
    "config",
    "csv",
    "dataset",
    "eval",
    "metric",
    "split",
    "test",
)


class RepositoryCollectionError(RuntimeError):
    """Repository 无法在既定只读边界内完成采集。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RepositoryTextFile:
    """从 Repository 中读取的一份有界文本材料。"""

    path: str
    text: str
    html_url: str
    size: int


@dataclass(frozen=True, slots=True)
class ExternalAssetReference:
    """Repository 文档中与模型资产有关的外部入口。"""

    url: str
    source_path: str
    line_number: int
    excerpt: str


@dataclass(frozen=True, slots=True)
class DatasetReference:
    """Repository 文档中可定位的数据集入口。"""

    name: str
    url: str
    source_path: str
    line_number: int
    excerpt: str


@dataclass(frozen=True, slots=True)
class RepositoryMaterials:
    """生成 Readiness Evidence 所需的最小 Repository 材料集。"""

    repository_url: str
    default_branch: str
    readme: RepositoryTextFile | None
    dependency_files: tuple[RepositoryTextFile, ...]
    relevant_paths: tuple[str, ...]
    fetched_at: datetime
    evaluation_files: tuple[RepositoryTextFile, ...] = ()
    external_asset_references: tuple[ExternalAssetReference, ...] = ()
    dataset_references: tuple[DatasetReference, ...] = ()


class RepositoryMaterialCollector(Protocol):
    """Assessment Service 依赖的只读 Repository 采集接口。"""

    def collect(self, target: ResolvedTarget) -> RepositoryMaterials:
        """返回生成 Assessment 所需的有界材料。"""
        ...


class GitHubFileMaterialReader(Protocol):
    """Read one explicit public GitHub blob URL within the repository boundary."""

    def read_file_url(self, url: str) -> RepositoryTextFile | None:
        """Return bounded text only; never list directories or execute repository content."""
        ...


class GitHubRepositoryMaterialCollector:
    """通过 GitHub REST API 只读采集 README、依赖文件和相关路径。"""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_file_bytes: int = 250_000,
        max_dependency_files: int = 6,
        max_evaluation_files: int = 8,
        max_relevant_paths: int = 100,
        cache_ttl_seconds: float = 300.0,
        github_token: str | None = None,
    ) -> None:
        self._owns_client = client is None
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ResearchOps-Agent/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = github_token if github_token is not None else os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = client or outbound_client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(8.0, connect=4.0),
            follow_redirects=False,
            trust_env=False,
        )
        self.max_file_bytes = max_file_bytes
        self.max_dependency_files = max_dependency_files
        self.max_evaluation_files = max_evaluation_files
        self.max_relevant_paths = max_relevant_paths
        self.cache_ttl_seconds = cache_ttl_seconds
        self._json_cache: dict[
            tuple[str, tuple[tuple[str, str], ...]], tuple[float, dict[str, object]]
        ] = {}

    def close(self) -> None:
        """关闭由 Collector 自己创建的 HTTP Client。"""

        if self._owns_client:
            self.client.close()

    def collect(self, target: ResolvedTarget) -> RepositoryMaterials:
        """采集一个已解析 GitHub Repository 的受限文本材料。"""

        match = GITHUB_ID_PATTERN.fullmatch(target.canonical_id)
        if target.target_type != "repository" or match is None:
            raise RepositoryCollectionError("只允许采集已规范化的 GitHub Repository 目标。")

        owner = match.group("owner")
        repository = match.group("repository")
        repository_path = f"/repos/{owner}/{repository}"
        metadata = self._get_json(repository_path)
        default_branch = self._required_string(metadata, "default_branch", repository_path)
        repository_url = self._required_string(metadata, "html_url", repository_path)

        readme = self._collect_readme(repository_path)
        tree = self._get_json(
            f"{repository_path}/git/trees/{quote(default_branch, safe='')}",
            params={"recursive": "1"},
        )
        entries = tree.get("tree")
        if not isinstance(entries, list):
            raise RepositoryCollectionError("GitHub tree 响应缺少文件列表。")

        blob_paths = sorted(
            entry["path"]
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("type") == "blob"
            and isinstance(entry.get("path"), str)
        )
        dependency_paths = [path for path in blob_paths if self._is_dependency_file(path)][
            : self.max_dependency_files
        ]
        dependency_files = tuple(
            material
            for path in dependency_paths
            if (material := self._collect_text_file(repository_path, default_branch, path))
            is not None
        )
        evaluation_paths = sorted(
            (
                path
                for path in blob_paths
                if path not in dependency_paths and self._is_evaluation_file(path)
            ),
            key=lambda path: (-self._evaluation_priority(path), path.casefold()),
        )[: self.max_evaluation_files]
        evaluation_files = self._collect_optional_text_files(
            repository_path,
            default_branch,
            evaluation_paths,
        )
        relevant_paths = tuple(
            path
            for path in blob_paths
            if any(term in path.casefold() for term in RELEVANT_PATH_TERMS)
        )[: self.max_relevant_paths]
        external_asset_references = self._extract_external_asset_references(readme)
        dataset_references = self._extract_dataset_references(readme)

        return RepositoryMaterials(
            repository_url=repository_url,
            default_branch=default_branch,
            readme=readme,
            dependency_files=dependency_files,
            evaluation_files=evaluation_files,
            relevant_paths=relevant_paths,
            fetched_at=datetime.now(UTC),
            external_asset_references=external_asset_references,
            dataset_references=dataset_references,
        )

    def read_file_url(self, url: str) -> RepositoryTextFile | None:
        """Read one allowlisted GitHub blob URL requested by the research planner."""
        owner, repository, branch, path = self._parse_github_blob_url(url)
        payload = self._get_json(
            f"/repos/{owner}/{repository}/contents/{quote(path, safe='/')}",
            params={"ref": branch},
        )
        return self._decode_content_payload(payload)

    @staticmethod
    def _extract_external_asset_references(
        readme: RepositoryTextFile | None,
    ) -> tuple[ExternalAssetReference, ...]:
        if readme is None:
            return ()

        references: list[ExternalAssetReference] = []
        for line_number, line in enumerate(readme.text.splitlines(), start=1):
            normalized = line.strip()
            if not any(term in normalized.casefold() for term in WEIGHT_REFERENCE_TERMS):
                continue
            for url in URL_PATTERN.findall(normalized):
                references.append(
                    ExternalAssetReference(
                        url=url.rstrip(".,;"),
                        source_path=readme.path,
                        line_number=line_number,
                        excerpt=normalized[:1000],
                    )
                )
        return tuple(references)

    @staticmethod
    def _extract_dataset_references(
        readme: RepositoryTextFile | None,
    ) -> tuple[DatasetReference, ...]:
        if readme is None:
            return ()

        references: list[DatasetReference] = []
        for line_number, line in enumerate(readme.text.splitlines(), start=1):
            normalized = line.strip()
            if not any(term in normalized.casefold() for term in DATASET_REFERENCE_TERMS):
                continue
            name_match = re.search(r"(?i)\b([A-Za-z0-9_-]+)\s+dataset\b", normalized)
            name = name_match.group(1) if name_match else "Dataset entry"
            for url in URL_PATTERN.findall(normalized):
                references.append(
                    DatasetReference(
                        name=name,
                        url=url.rstrip(".,;"),
                        source_path=readme.path,
                        line_number=line_number,
                        excerpt=normalized[:1000],
                    )
                )
        return tuple(references)

    def _collect_readme(self, repository_path: str) -> RepositoryTextFile | None:
        try:
            payload = self._get_json(f"{repository_path}/readme")
        except RepositoryCollectionError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._decode_content_payload(payload)

    def _collect_text_file(
        self,
        repository_path: str,
        default_branch: str,
        path: str,
    ) -> RepositoryTextFile | None:
        payload = self._get_json(
            f"{repository_path}/contents/{quote(path, safe='/')}",
            params={"ref": default_branch},
        )
        return self._decode_content_payload(payload)

    def _collect_optional_text_files(
        self,
        repository_path: str,
        default_branch: str,
        paths: list[str],
    ) -> tuple[RepositoryTextFile, ...]:
        """可选 Signal 材料单文件失败时继续保留已取得的核心材料。"""

        collected: list[RepositoryTextFile] = []
        for path in paths:
            try:
                material = self._collect_text_file(repository_path, default_branch, path)
            except RepositoryCollectionError:
                continue
            if material is not None:
                collected.append(material)
        return tuple(collected)

    def _decode_content_payload(self, payload: dict[str, object]) -> RepositoryTextFile | None:
        size = payload.get("size")
        content = payload.get("content")
        encoding = payload.get("encoding")
        path = payload.get("path") or payload.get("name")
        html_url = payload.get("html_url")
        if (
            not isinstance(size, int)
            or size > self.max_file_bytes
            or not isinstance(content, str)
            or encoding != "base64"
            or not isinstance(path, str)
            or not isinstance(html_url, str)
        ):
            return None

        try:
            raw = base64.b64decode(content, validate=False)
        except (ValueError, binascii.Error) as exc:
            raise RepositoryCollectionError(f"无法解码 Repository 文本文件：{path}") from exc
        if len(raw) > self.max_file_bytes:
            return None

        return RepositoryTextFile(
            path=path,
            text=raw.decode("utf-8", errors="replace"),
            html_url=html_url,
            size=len(raw),
        )

    def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        cache_key = (path, tuple(sorted((params or {}).items())))
        now = time.monotonic()
        cached = self._json_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            response = self.client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RepositoryCollectionError(
                f"GitHub API 返回 HTTP {exc.response.status_code}：{path}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise RepositoryCollectionError(f"无法访问 GitHub API：{exc}") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise RepositoryCollectionError(f"GitHub API 返回了无效 JSON：{path}") from exc
        if not isinstance(payload, dict):
            raise RepositoryCollectionError(f"GitHub API 返回了无效 JSON：{path}")
        if self.cache_ttl_seconds > 0:
            self._json_cache[cache_key] = (now + self.cache_ttl_seconds, payload)
        return payload

    @staticmethod
    def _required_string(payload: dict[str, object], key: str, path: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise RepositoryCollectionError(f"GitHub API 响应缺少 {key}：{path}")
        return value

    @staticmethod
    def _parse_github_blob_url(url: str) -> tuple[str, str, str, str]:
        parsed = urlparse(url)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or len(parts) < 5
            or parts[2] != "blob"
        ):
            raise RepositoryCollectionError("只允许读取明确的公开 GitHub blob 文件 URL。")
        owner, repository, _marker, branch, *path_parts = parts
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", item) for item in (owner, repository, branch)):
            raise RepositoryCollectionError(
                "GitHub blob URL 包含不受支持的 owner、repository 或 branch。"
            )
        path = "/".join(path_parts)
        if not path or any(part in {".", ".."} for part in path_parts):
            raise RepositoryCollectionError("GitHub blob URL 缺少安全的文件路径。")
        return owner, repository, branch, path

    @staticmethod
    def _is_dependency_file(path: str) -> bool:
        name = path.rsplit("/", 1)[-1].casefold()
        return (
            name in DEPENDENCY_FILE_NAMES
            or name.startswith("requirements-")
            or name.startswith("environment-")
        )

    @staticmethod
    def _is_evaluation_file(path: str) -> bool:
        normalized = path.casefold()
        name = normalized.rsplit("/", 1)[-1]
        extension = f".{name.rsplit('.', 1)[-1]}" if "." in name else ""
        return extension in EVALUATION_FILE_EXTENSIONS and any(
            term in normalized for term in EVALUATION_PATH_TERMS
        )

    @staticmethod
    def _evaluation_priority(path: str) -> int:
        normalized = path.casefold()
        name = normalized.rsplit("/", 1)[-1]
        extension = f".{name.rsplit('.', 1)[-1]}" if "." in name else ""
        score = 3 if extension in {".cfg", ".ini", ".json", ".py", ".toml", ".yaml", ".yml"} else 0
        score += (
            2
            if any(term in normalized for term in ("config", "csv", "dataset", "eval", "metric"))
            else 0
        )
        score += 1 if any(term in normalized for term in ("split", "test")) else 0
        return score
