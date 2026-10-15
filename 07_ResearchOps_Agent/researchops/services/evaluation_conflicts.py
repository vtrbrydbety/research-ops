"""P06-light Evaluation Conflict 的保守证据比较。"""

import re
from dataclasses import dataclass

from researchops.schemas import EvaluationSignal, Evidence, EvidenceConflict
from researchops.services.repository_materials import RepositoryMaterials, RepositoryTextFile

CSV_NAME_PATTERN = re.compile(
    r"(?P<name>(?:train|test|val|valid|validation)[A-Za-z0-9_.-]*\.csv)",
    re.IGNORECASE,
)
EXPLICIT_SETTING_PATTERNS = (
    (
        "Metric Definition",
        "evaluation.metric",
        re.compile(
            r"(?i)\b(?:evaluation[_\s-]*metric|eval[_\s-]*metric|metric)\b"
            r"\s*[:=]\s*['\"]?(?P<value>[A-Za-z][A-Za-z0-9_.-]*)"
        ),
    ),
    (
        "Aggregation",
        "evaluation.aggregation",
        re.compile(
            r"(?i)\b(?:aggregation|averaging|average)\b\s*[:=]\s*['\"]?"
            r"(?P<value>macro|micro|weighted|mean|max|sum)"
        ),
    ),
)
PAPER_CODE_SETTING_PATTERN = re.compile(
    r"(?i)\b(?P<key>threshold|test[_\s-]*batch[_\s-]*size|"
    r"eval[_\s-]*batch[_\s-]*size|clip[_\s-]*length|num[_\s-]*frames)\b"
    r"\s*[:=]\s*['\"]?(?P<value>[A-Za-z0-9_.-]+)"
)


@dataclass(frozen=True, slots=True)
class LocatedValue:
    """一条带来源位置的显式评测值。"""

    value: str
    material: RepositoryTextFile
    line_number: int
    excerpt: str


class EvaluationConflictService:
    """只在相同条件存在两个显式、不一致值时建立冲突。"""

    def create(
        self,
        materials: RepositoryMaterials,
    ) -> tuple[EvaluationSignal, list[EvidenceConflict]]:
        """返回设计定义的 Warning / Unknown Signal 与可追溯冲突。"""

        conflicts = [
            *self._find_dataset_split_conflicts(materials),
            *self._find_explicit_setting_conflicts(materials),
            *self._find_paper_code_setting_conflicts(materials),
        ]

        if conflicts:
            primary = conflicts[0]
            conflict_types = [self._conflict_type(conflict) for conflict in conflicts]
            conflict_type = conflict_types[0]
            status = (
                "Warning"
                if all(item == "Paper-Code Setting" for item in conflict_types)
                else "Unknown"
            )
            summary = (
                primary.summary
                if len(conflicts) == 1
                else f"{len(conflicts)} unresolved evaluation conflicts were preserved. "
                f"Highest-priority conflict: {primary.summary}"
            )
            return (
                EvaluationSignal(
                    signal_id=f"signal-{primary.conflict_id}",
                    status=status,
                    conflict_type=conflict_type,
                    summary=summary,
                    evidence_refs=[
                        evidence for conflict in conflicts for evidence in conflict.sources
                    ],
                    gate_impact=(
                        "This unresolved Evaluation Conflict supports CONDITIONAL PROCEED while "
                        "the authoritative evaluation protocol remains unknown. It does not "
                        "independently produce a P0 Blocked state or PAUSE."
                        if status == "Unknown"
                        else "This known evaluation difference may affect comparability and supports "
                        "CONDITIONAL PROCEED, but it does not independently produce PAUSE."
                    ),
                ),
                conflicts,
            )

        evidence = self._scan_evidence(materials)
        return (
            EvaluationSignal(
                signal_id="evaluation-conflict-scan",
                status="Unknown",
                conflict_type="Paper-Code Setting",
                summary=(
                    "The bounded Repository evaluation materials do not establish a conflicting "
                    "pair, but paper evidence has not been acquired, so paper-code evaluation "
                    "alignment cannot be determined."
                ),
                evidence_refs=[evidence],
                gate_impact=(
                    "This Unknown preserves the unverified evaluation relationship and can support "
                    "CONDITIONAL PROCEED. It does not independently produce PAUSE."
                ),
            ),
            [],
        )

    def _find_dataset_split_conflicts(
        self,
        materials: RepositoryMaterials,
    ) -> list[EvidenceConflict]:
        writers: dict[str, list[LocatedValue]] = {}
        readers: dict[str, list[LocatedValue]] = {}
        conflicts: list[EvidenceConflict] = []

        for material in materials.evaluation_files:
            folded_text = material.text.casefold()
            is_writer = any(
                marker in folded_text for marker in ("write_list(", "to_csv(", "csv.writer")
            )
            is_reader = "read_csv(" in folded_text
            if not is_writer and not is_reader:
                continue

            for line_number, line in enumerate(material.text.splitlines(), start=1):
                for match in CSV_NAME_PATTERN.finditer(line):
                    name = match.group("name").casefold()
                    split = self._split_kind(name)
                    located = LocatedValue(
                        value=name,
                        material=material,
                        line_number=line_number,
                        excerpt=line.strip()[:1000],
                    )
                    if is_writer:
                        writers.setdefault(split, []).append(located)
                    if is_reader:
                        readers.setdefault(split, []).append(located)

        for split in ("test", "validation", "train"):
            produced = writers.get(split, [])
            required = readers.get(split, [])
            if not produced or not required:
                continue
            produced_names = {item.value for item in produced}
            required_names = {item.value for item in required}
            unmatched_produced = [item for item in produced if item.value not in required_names]
            unmatched_required = [item for item in required if item.value not in produced_names]
            if not unmatched_produced or not unmatched_required:
                continue

            source_a = next(
                (item for item in unmatched_produced if "small" not in item.value),
                unmatched_produced[0],
            )
            # Preserve source order rather than preferring around names from a
            # historical FGI demo. Any producer/loader mismatch is evaluated
            # by the same generic rule for every repository.
            source_b = unmatched_required[0]
            summary = (
                f"Potential Dataset Split mapping conflict: the split producer writes "
                f"'{source_a.value}', while the dataset loader expects '{source_b.value}' for "
                f"the {split} path. This proves a producer-loader filename mismatch, but not yet "
                "that the sample composition or evaluation protocol differs."
            )
            conflicts.append(
                EvidenceConflict(
                    conflict_id=f"evaluation-dataset-split-{split}",
                    condition_key=f"evaluation.dataset_split.mapping.{split}",
                    dimension_ids=["RD-01"],
                    summary=summary,
                    gate_critical=False,
                    sources=[
                        self._evidence(source_a, "Dataset split filename produced"),
                        self._evidence(source_b, "Dataset split filename required by loader"),
                    ],
                )
            )
        return conflicts

    def _find_explicit_setting_conflicts(
        self,
        materials: RepositoryMaterials,
    ) -> list[EvidenceConflict]:
        all_materials = tuple(
            material
            for material in (materials.readme, *materials.evaluation_files)
            if material is not None
        )
        conflicts: list[EvidenceConflict] = []
        for conflict_type, condition_key, pattern in EXPLICIT_SETTING_PATTERNS:
            located: list[LocatedValue] = []
            for material in all_materials:
                for line_number, line in enumerate(material.text.splitlines(), start=1):
                    match = pattern.search(line)
                    if match:
                        located.append(
                            LocatedValue(
                                value=match.group("value").casefold(),
                                material=material,
                                line_number=line_number,
                                excerpt=line.strip()[:1000],
                            )
                        )

            for index, source_a in enumerate(located):
                source_b = next(
                    (
                        candidate
                        for candidate in located[index + 1 :]
                        if candidate.material.path != source_a.material.path
                        and candidate.value != source_a.value
                    ),
                    None,
                )
                if source_b is None:
                    continue
                slug = conflict_type.casefold().replace(" ", "-")
                conflicts.append(
                    EvidenceConflict(
                        conflict_id=f"evaluation-{slug}",
                        condition_key=condition_key,
                        dimension_ids=["RD-03"],
                        summary=(
                            f"Two collected sources specify different {conflict_type.casefold()} "
                            f"values: '{source_a.value}' and '{source_b.value}'. The authoritative "
                            "evaluation definition is not established."
                        ),
                        gate_critical=False,
                        sources=[
                            self._evidence(source_a, f"{conflict_type} source A"),
                            self._evidence(source_b, f"{conflict_type} source B"),
                        ],
                    )
                )
                break
        return conflicts

    def _find_paper_code_setting_conflicts(
        self,
        materials: RepositoryMaterials,
    ) -> list[EvidenceConflict]:
        all_materials = tuple(
            material
            for material in (materials.readme, *materials.evaluation_files)
            if material is not None
        )
        values_by_key: dict[str, list[LocatedValue]] = {}
        for material in all_materials:
            for line_number, line in enumerate(material.text.splitlines(), start=1):
                match = PAPER_CODE_SETTING_PATTERN.search(line)
                if not match:
                    continue
                key = re.sub(r"[_\s-]+", "_", match.group("key").casefold())
                values_by_key.setdefault(key, []).append(
                    LocatedValue(
                        value=match.group("value").casefold(),
                        material=material,
                        line_number=line_number,
                        excerpt=line.strip()[:1000],
                    )
                )

        conflicts: list[EvidenceConflict] = []
        for key, located in values_by_key.items():
            paper_values = [item for item in located if self._is_paper_material(item.material)]
            code_values = [item for item in located if not self._is_paper_material(item.material)]
            for source_a in paper_values:
                source_b = next(
                    (item for item in code_values if item.value != source_a.value),
                    None,
                )
                if source_b is None:
                    continue
                conflicts.append(
                    EvidenceConflict(
                        conflict_id=f"evaluation-paper-code-{key}",
                        condition_key=f"evaluation.setting.{key}",
                        dimension_ids=["RD-03"],
                        summary=(
                            f"Paper material specifies {key}='{source_a.value}', while code material "
                            f"specifies '{source_b.value}'. The difference may affect result "
                            "comparability."
                        ),
                        gate_critical=False,
                        sources=[
                            self._evidence(source_a, "Paper evaluation setting"),
                            self._evidence(source_b, "Code evaluation setting"),
                        ],
                    )
                )
                break
        return conflicts

    @staticmethod
    def _split_kind(name: str) -> str:
        if name.startswith("train"):
            return "train"
        if name.startswith(("val", "valid", "validation")):
            return "validation"
        return "test"

    @staticmethod
    def _evidence(value: LocatedValue, summary: str) -> Evidence:
        return Evidence(
            evidence_type="Fact",
            verification_status="Located Only",
            source_type="Material",
            material_type="Config",
            summary=summary,
            source=value.material.path,
            location=f"{value.material.path}:line {value.line_number}",
            excerpt=value.excerpt,
            source_url=value.material.html_url,
        )

    @staticmethod
    def _conflict_type(conflict: EvidenceConflict) -> str:
        if "dataset_split" in conflict.condition_key:
            return "Dataset Split"
        if "metric" in conflict.condition_key:
            return "Metric Definition"
        if "aggregation" in conflict.condition_key:
            return "Aggregation"
        return "Paper-Code Setting"

    @staticmethod
    def _is_paper_material(material: RepositoryTextFile) -> bool:
        normalized = material.path.casefold()
        return any(marker in normalized for marker in ("paper", "appendix", "project page"))

    @staticmethod
    def _scan_evidence(materials: RepositoryMaterials) -> Evidence:
        paths = [material.path for material in materials.evaluation_files]
        located = bool(paths)
        return Evidence(
            evidence_type="Unknown",
            verification_status="Located Only" if located else "Unverifiable",
            source_type="Material",
            material_type="Repository",
            summary=(
                "Repository evaluation-related files were scanned, but no two explicit, "
                "incompatible values for the same condition were established."
                if located
                else "No bounded evaluation-related file was collected for comparison."
            ),
            source="Bounded Repository evaluation scan",
            location=f"branch:{materials.default_branch}",
            excerpt=(", ".join(paths) if paths else "No evaluation material path was collected.")[
                :2000
            ],
            source_url=materials.repository_url,
        )
