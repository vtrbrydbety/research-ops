"""Resource Constraint Signal 的保守计算。"""

import re
from dataclasses import dataclass

from researchops.schemas import Evidence, ResourceItem, ResourceSignal
from researchops.services.environment_facts import EnvironmentFacts
from researchops.services.repository_materials import RepositoryTextFile


@dataclass(frozen=True, slots=True)
class ProjectResourceRequirements:
    """公开项目材料中明确声明的最低资源要求。"""

    minimum_vram_gb: float | None = None
    minimum_disk_gb: float | None = None
    minimum_time_hours: float | None = None


class ResourceSignalService:
    """将项目最低要求与已授权资源事实转换为附加 Signal。"""

    def create(
        self,
        readme: RepositoryTextFile | None,
        facts: EnvironmentFacts | None,
        *,
        repository_url: str,
    ) -> ResourceSignal:
        """按冻结规则计算 Blocked、Warning 或 Unknown。"""

        requirements = self._extract_requirements(readme.text if readme else "")
        shortfalls: list[str] = []
        narrow_margins: list[str] = []

        self._compare_capacity(
            "GPU / VRAM",
            facts.vram_gb if facts else None,
            requirements.minimum_vram_gb,
            shortfalls,
            narrow_margins,
            unit="GB",
        )
        self._compare_capacity(
            "Disk",
            facts.available_disk_gb if facts else None,
            requirements.minimum_disk_gb,
            shortfalls,
            narrow_margins,
            unit="GB",
        )
        current_time_hours = self._time_hours(facts.time_budget if facts else None)
        self._compare_capacity(
            "Time budget",
            current_time_hours,
            requirements.minimum_time_hours,
            shortfalls,
            narrow_margins,
            unit="hours",
        )

        if shortfalls:
            status = "Blocked"
            summary = "Confirmed resource shortfall: " + "; ".join(shortfalls) + "."
            gate_impact = "Confirmed Resource Blocked Signal triggers PAUSE."
        elif narrow_margins:
            status = "Warning"
            summary = "Known resource margin risk: " + "; ".join(narrow_margins) + "."
            gate_impact = "Adds a non-blocking resource risk to CONDITIONAL PROCEED."
        else:
            status = "Unknown"
            summary = (
                "Available resource facts are known, but the project's explicit minimum "
                "requirements are not fully confirmed."
            )
            gate_impact = (
                "This Unknown can contribute to CONDITIONAL PROCEED, but it does not justify "
                "Resource Blocked without an explicit minimum requirement and a confirmed shortfall."
            )

        items = [
            ResourceItem(
                resource="GPU / VRAM",
                current=self._gpu_current(facts),
                required=self._required_capacity(requirements.minimum_vram_gb),
            ),
            ResourceItem(
                resource="Disk",
                current=(
                    f"{facts.available_disk_gb:g} GB available"
                    if facts and facts.available_disk_gb is not None
                    else "Not provided"
                ),
                required=self._required_capacity(requirements.minimum_disk_gb),
            ),
            ResourceItem(
                resource="Time budget",
                current=facts.time_budget if facts and facts.time_budget else "Not provided",
                required=self._required_time(requirements.minimum_time_hours),
            ),
        ]

        source_label = facts.source_mode if facts else "environment not acquired"
        evidence_summary = (
            f"Current GPU/VRAM: {items[0].current}; current disk: {items[1].current}; "
            f"project minimum VRAM: {items[0].required}; project minimum disk: "
            f"{items[1].required}; project minimum time: {items[2].required}."
        )
        return ResourceSignal(
            status=status,
            summary=summary,
            gate_impact=gate_impact,
            items=items,
            evidence=Evidence(
                evidence_type="Fact" if shortfalls or narrow_margins else "Unknown",
                verification_status=(
                    "Corroborated"
                    if shortfalls or narrow_margins
                    else "Located Only"
                    if facts or readme
                    else "Unverifiable"
                ),
                source_type="User Context",
                summary=evidence_summary,
                source=f"Environment:{source_label} + Repository README",
                location="Authorized environment facts + explicit resource requirement scan",
                excerpt=evidence_summary,
                source_url=readme.html_url if readme else repository_url,
            ),
        )

    @staticmethod
    def _extract_requirements(text: str) -> ProjectResourceRequirements:
        vram = ResourceSignalService._minimum_capacity(
            text,
            resource=r"(?:VRAM|GPU\s+memory)",
        )
        disk = ResourceSignalService._minimum_capacity(
            text,
            resource=r"(?:disk|storage)",
        )
        minimum_time_hours = ResourceSignalService._minimum_time_hours(text)
        return ProjectResourceRequirements(
            minimum_vram_gb=vram,
            minimum_disk_gb=disk,
            minimum_time_hours=minimum_time_hours,
        )

    @staticmethod
    def _minimum_capacity(text: str, *, resource: str) -> float | None:
        patterns = (
            rf"(?im)(?:minimum|at\s+least|requires?|needs?)[^\r\n]{{0,50}}?"
            rf"(?P<value>\d+(?:\.\d+)?)\s*(?:GB|GiB)\s*{resource}",
            rf"(?im)(?P<value>\d+(?:\.\d+)?)\s*(?:GB|GiB)\s*{resource}"
            rf"[^\r\n]{{0,20}}?(?:minimum|required)",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group("value"))
        return None

    @staticmethod
    def _compare_capacity(
        label: str,
        current: float | None,
        required: float | None,
        shortfalls: list[str],
        narrow_margins: list[str],
        *,
        unit: str,
    ) -> None:
        if current is None or required is None:
            return
        if current < required:
            shortfalls.append(f"{label} {current:g} {unit} is below required {required:g} {unit}")
        elif current < required * 1.2:
            narrow_margins.append(
                f"{label} {current:g} {unit} is close to required {required:g} {unit}"
            )

    @staticmethod
    def _minimum_time_hours(text: str) -> float | None:
        pattern = re.compile(
            r"(?im)(?:minimum|at\s+least|requires?|needs?|takes?|estimated(?:\s+runtime)?)"
            r"[^\r\n]{0,50}?(?P<value>\d+(?:\.\d+)?)\s*"
            r"(?P<unit>hours?|hrs?|days?)\b"
        )
        match = pattern.search(text)
        if not match:
            return None
        value = float(match.group("value"))
        return value * 24 if match.group("unit").casefold().startswith("day") else value

    @staticmethod
    def _time_hours(value: str | None) -> float | None:
        if not value:
            return None
        match = re.search(
            r"(?i)(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|days?)\b",
            value,
        )
        if not match:
            return None
        amount = float(match.group("value"))
        return amount * 24 if match.group("unit").casefold().startswith("day") else amount

    @staticmethod
    def _gpu_current(facts: EnvironmentFacts | None) -> str:
        if facts is None or (not facts.gpu and facts.vram_gb is None):
            return "Not provided"
        if facts.gpu and facts.vram_gb is not None:
            return f"{facts.gpu} / {facts.vram_gb:g} GB VRAM"
        return facts.gpu or f"{facts.vram_gb:g} GB VRAM"

    @staticmethod
    def _required_capacity(value: float | None) -> str:
        return f">= {value:g} GB" if value is not None else "Not confirmed"

    @staticmethod
    def _required_time(value: float | None) -> str:
        return f">= {value:g} hours" if value is not None else "Not confirmed"
