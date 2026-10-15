"""授权环境事实的只读采集、文本解析与项目要求比较。"""

import importlib.metadata
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

EnvironmentMode = Literal["readonly", "snapshot", "manual", "later"]


@dataclass(frozen=True, slots=True)
class EnvironmentFacts:
    """RD-02 判断使用的最小环境事实。"""

    source_mode: EnvironmentMode
    os: str | None = None
    python: str | None = None
    framework: str | None = None
    cuda: str | None = None
    driver: str | None = None
    gpu: str | None = None
    vram_gb: float | None = None
    available_disk_gb: float | None = None
    time_budget: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectEnvironmentRequirements:
    """依赖文件中可确定的关键项目环境要求。"""

    python: str | None = None
    framework: str | None = None
    cuda: str | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentComparison:
    """项目要求与当前环境事实的保守比较结果。"""

    status: Literal["Ready", "Warning", "Unknown"]
    summary: str
    finding_title: str
    finding_summary: str
    finding_type: Literal["Fact", "Inference", "Unknown"]
    readiness_impact: str
    excerpt: str


class EnvironmentFactService:
    """从授权本机或用户文本中获取事实，并执行确定性版本比较。"""

    def acquire(
        self,
        mode: EnvironmentMode,
        *,
        authorized: bool,
        supplied_text: str | None,
    ) -> EnvironmentFacts | None:
        """按输入模式获取环境事实；未授权的 readonly 不读取本机。"""

        if mode == "readonly":
            from researchops.core.access_context import current_access
            from researchops.services.access_store import AccessError

            if current_access.get():
                raise AccessError("ENVIRONMENT_DISABLED", "公网不支持服务器环境探测。", 403)
            return self._read_local_environment() if authorized else None
        if mode in {"snapshot", "manual"} and supplied_text:
            return self._parse_supplied_text(mode, supplied_text)
        return None

    def extract_requirements(self, dependency_text: str | None) -> ProjectEnvironmentRequirements:
        """从 Conda/Pip 风格依赖文本提取 Python、Torch 和 CUDA 版本。"""

        if not dependency_text:
            return ProjectEnvironmentRequirements()
        return ProjectEnvironmentRequirements(
            python=self._package_version(dependency_text, "python"),
            framework=(
                self._package_version(dependency_text, "torch")
                or self._package_version(dependency_text, "pytorch")
            ),
            cuda=(
                self._package_version(dependency_text, "cudatoolkit")
                or self._package_version(dependency_text, "cuda")
            ),
        )

    def compare(
        self,
        requirements: ProjectEnvironmentRequirements,
        facts: EnvironmentFacts | None,
    ) -> EnvironmentComparison:
        """按冻结状态规则输出 RD-02 Ready、Warning 或 Unknown。"""

        project_values = {
            "Python": requirements.python,
            "Framework": requirements.framework,
            "CUDA": requirements.cuda,
        }
        current_values = {
            "Python": facts.python if facts else None,
            "Framework": facts.framework if facts else None,
            "CUDA": facts.cuda if facts else None,
        }
        required_keys = [key for key, value in project_values.items() if value]
        missing_project = not required_keys
        missing_current = [key for key in required_keys if not current_values[key]]
        excerpt = self._comparison_excerpt(project_values, current_values, facts)

        if missing_project:
            return EnvironmentComparison(
                status="Unknown",
                summary="Project environment requirements are not sufficiently identified.",
                finding_title="Project environment requirements remain unknown",
                finding_summary=(
                    "No supported dependency material established the key Python, framework, or "
                    "CUDA requirements needed for comparison."
                ),
                finding_type="Unknown",
                readiness_impact="Readiness Unknown",
                excerpt=excerpt,
            )
        if facts is None or missing_current:
            missing_label = ", ".join(missing_current) if missing_current else "environment facts"
            return EnvironmentComparison(
                status="Unknown",
                summary=(
                    "Project requirements are available, but current environment facts are "
                    "insufficient for compatibility comparison."
                ),
                finding_title="Current environment facts are incomplete",
                finding_summary=f"Missing comparable current values: {missing_label}.",
                finding_type="Unknown",
                readiness_impact="Readiness Unknown",
                excerpt=excerpt,
            )

        differences = [
            key
            for key in required_keys
            if not self._versions_align(project_values[key], current_values[key])
        ]
        if differences:
            return EnvironmentComparison(
                status="Warning",
                summary=(
                    "Current environment facts differ from the documented project setup and need "
                    "compatibility validation."
                ),
                finding_title="A version compatibility risk needs validation",
                finding_summary=(
                    "Known version differences were found for: " + ", ".join(differences) + "."
                ),
                finding_type="Inference",
                readiness_impact="Non-blocking Warning",
                excerpt=excerpt,
            )

        return EnvironmentComparison(
            status="Ready",
            summary=(
                "Available environment facts align with the documented dependency requirements "
                "for the current validation path."
            ),
            finding_title="Environment facts support the current validation path",
            finding_summary="Python, framework, and CUDA values align at the declared version level.",
            finding_type="Fact",
            readiness_impact="No current blocker",
            excerpt=excerpt,
        )

    @staticmethod
    def _package_version(text: str, package: str) -> str | None:
        pattern = re.compile(rf"(?im)^\s*{re.escape(package)}\s*(?:==|=|:)\s*([^\s=,;]+)")
        match = pattern.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _versions_align(project: str | None, current: str | None) -> bool:
        if not project or not current:
            return False
        project_numbers = re.findall(r"\d+", project)
        current_numbers = re.findall(r"\d+", current)
        return project_numbers[:2] == current_numbers[:2]

    @staticmethod
    def _comparison_excerpt(
        project: dict[str, str | None],
        current: dict[str, str | None],
        facts: EnvironmentFacts | None,
    ) -> str:
        project_text = ", ".join(f"{key}={value or 'unknown'}" for key, value in project.items())
        current_text = ", ".join(f"{key}={value or 'unknown'}" for key, value in current.items())
        source = facts.source_mode if facts else "not provided"
        return f"Project: {project_text} | Current ({source}): {current_text}"

    def _read_local_environment(self) -> EnvironmentFacts:
        framework = self._installed_version("torch")
        gpu, vram_gb, driver = self._nvidia_facts()
        cuda = self._cuda_version() or self._cuda_from_framework(framework)
        disk = shutil.disk_usage(Path.cwd()).free / (1024**3)
        return EnvironmentFacts(
            source_mode="readonly",
            os=platform.platform(),
            python=platform.python_version(),
            framework=framework,
            cuda=cuda,
            driver=driver,
            gpu=gpu,
            vram_gb=vram_gb,
            available_disk_gb=round(disk, 1),
        )

    @staticmethod
    def _installed_version(package: str) -> str | None:
        try:
            return importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            return None

    @staticmethod
    def _nvidia_facts() -> tuple[str | None, float | None, str | None]:
        executable = shutil.which("nvidia-smi")
        if not executable:
            return None, None, None
        try:
            result = subprocess.run(
                [
                    executable,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=4,
            )
        except (OSError, subprocess.SubprocessError):
            return None, None, None
        first_line = (
            result.stdout.splitlines()[0] if result.returncode == 0 and result.stdout else ""
        )
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) != 3:
            return None, None, None
        try:
            vram_gb = round(float(parts[1]) / 1024, 1)
        except ValueError:
            vram_gb = None
        return parts[0] or None, vram_gb, parts[2] or None

    @staticmethod
    def _cuda_version() -> str | None:
        executable = shutil.which("nvcc")
        if not executable:
            return None
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=4,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        match = re.search(r"release\s+(\d+(?:\.\d+)*)", result.stdout, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _cuda_from_framework(framework: str | None) -> str | None:
        if not framework:
            return None
        match = re.search(r"\+cu(?P<major>\d{2})(?P<minor>\d)", framework)
        if not match:
            return None
        return f"{int(match.group('major'))}.{match.group('minor')}"

    def _parse_supplied_text(self, mode: EnvironmentMode, text: str) -> EnvironmentFacts:
        normalized = text[:50_000]
        return EnvironmentFacts(
            source_mode=mode,
            os=self._labeled_value(normalized, ("OS", "Operating System")),
            python=self._labeled_value(normalized, ("Python",)),
            framework=self._labeled_value(normalized, ("PyTorch", "Torch", "Framework")),
            cuda=self._labeled_value(normalized, ("CUDA", "CUDA Toolkit")),
            driver=self._labeled_value(normalized, ("Driver", "NVIDIA Driver")),
            gpu=self._labeled_value(normalized, ("GPU",)),
            vram_gb=self._numeric_gb(normalized, ("VRAM",)),
            available_disk_gb=self._numeric_gb(normalized, ("Available disk", "Disk")),
            time_budget=self._labeled_value(normalized, ("Time budget", "Available time")),
        )

    @staticmethod
    def _labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
        for label in labels:
            match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*([^\r\n]+)", text)
            if match:
                value = match.group(1).strip()
                if value.casefold() not in {"unknown", "n/a", "none", "not provided"}:
                    return value[:300]
        return None

    @staticmethod
    def _numeric_gb(text: str, labels: tuple[str, ...]) -> float | None:
        for label in labels:
            match = re.search(
                rf"(?im){re.escape(label)}[^\r\n]*?([0-9]+(?:\.[0-9]+)?)\s*GB",
                text,
            )
            if match:
                return float(match.group(1))
        return None
