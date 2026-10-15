"""Evaluation Conflict Signal 的设计规则与证据保留测试。"""

from datetime import UTC, datetime
from pathlib import Path

from researchops.schemas import EvaluationSignal
from researchops.services import (
    EvaluationConflictService,
    RepositoryMaterials,
    RepositoryTextFile,
)

REPOSITORY_URL = "https://github.com/example/project"


def material(path: str, text: str) -> RepositoryTextFile:
    return RepositoryTextFile(
        path=path,
        text=text,
        html_url=f"{REPOSITORY_URL}/blob/main/{path}",
        size=len(text.encode()),
    )


def repository_materials(*evaluation_files: RepositoryTextFile) -> RepositoryMaterials:
    return RepositoryMaterials(
        repository_url=REPOSITORY_URL,
        default_branch="main",
        readme=material("README.md", "Run the documented evaluation command.\n"),
        dependency_files=(),
        relevant_paths=tuple(item.path for item in evaluation_files),
        fetched_at=datetime.now(UTC),
        evaluation_files=evaluation_files,
    )


def test_dataset_split_filename_mismatch_is_preserved_as_unknown() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(
        material(
            "write_csv.py",
            "write_list(test_set, os.path.join(root, 'test_split.csv'))\n",
        ),
        material(
            "dataset_3d.py",
            "split = os.path.join(root, 'test_imbalance_split.csv')\n"
            "video_info = pd.read_csv(split, header=None)\n",
        ),
    )

    signal, conflicts = service.create(materials)

    assert signal.status == "Unknown"
    assert signal.conflict_type == "Dataset Split"
    assert len(conflicts) == 1
    assert conflicts[0].condition_key == "evaluation.dataset_split.mapping.test"
    assert [item.source for item in conflicts[0].sources] == [
        "write_csv.py",
        "dataset_3d.py",
    ]
    assert "test_split.csv" in signal.summary
    assert "test_imbalance_split.csv" in signal.summary
    assert "not yet" in signal.summary


def test_dataset_split_conflict_rule_has_no_fgi_specific_filename_preference() -> None:
    source = Path("researchops/services/evaluation_conflicts.py").read_text(encoding="utf-8")

    assert '"fakeavceleb" not in item.value' not in source
    assert "source_b = unmatched_required[0]" in source


def test_metric_definition_conflict_is_detected_across_files() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(
        material("configs/eval.yaml", "metric: auc\n"),
        material("configs/test.yaml", "eval_metric = accuracy\n"),
    )

    signal, conflicts = service.create(materials)

    assert signal.status == "Unknown"
    assert signal.conflict_type == "Metric Definition"
    assert conflicts[0].condition_key == "evaluation.metric"
    assert len(signal.evidence_refs) == 2


def test_paper_code_setting_difference_is_warning() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(
        material("paper_notes.txt", "evaluation threshold: 0.5\n"),
        material("configs/eval.yaml", "threshold = 0.7\n"),
    )

    signal, conflicts = service.create(materials)

    assert signal.status == "Warning"
    assert signal.conflict_type == "Paper-Code Setting"
    assert conflicts[0].condition_key == "evaluation.setting.threshold"


def test_aggregation_uses_canonical_field_dictionary_value() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(
        material("configs/eval.yaml", "aggregation: macro\n"),
        material("configs/test.yaml", "average = micro\n"),
    )

    signal, conflicts = service.create(materials)

    assert signal.conflict_type == "Aggregation"
    assert conflicts[0].condition_key == "evaluation.aggregation"


def test_other_remains_available_in_public_contract() -> None:
    signal = EvaluationSignal(
        signal_id="evaluation-other",
        status="Unknown",
        conflict_type="Other",
        summary="A different evaluation condition requires review.",
        gate_impact="Does not independently produce PAUSE.",
    )

    assert signal.conflict_type == "Other"


def test_no_conflicting_pair_remains_unknown_without_inventing_none_state() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(material("configs/eval.yaml", "metric: auc\n"))

    signal, conflicts = service.create(materials)

    assert signal.status == "Unknown"
    assert conflicts == []
    assert "do not establish a conflicting pair" in signal.summary
    assert signal.evidence_refs[0].verification_status == "Located Only"


def test_multiple_independent_conflicts_are_all_preserved() -> None:
    service = EvaluationConflictService()
    materials = repository_materials(
        material(
            "configs/eval.yaml",
            "metric: auc\naggregation: macro\n",
        ),
        material(
            "configs/test.yaml",
            "eval_metric = accuracy\naverage = micro\n",
        ),
        material("paper_notes.txt", "evaluation threshold: 0.5\n"),
        material("configs/threshold.yaml", "threshold = 0.7\n"),
    )

    signal, conflicts = service.create(materials)

    assert signal.status == "Unknown"
    assert len(conflicts) == 3
    assert {conflict.condition_key for conflict in conflicts} == {
        "evaluation.metric",
        "evaluation.aggregation",
        "evaluation.setting.threshold",
    }
    assert len(signal.evidence_refs) == 6
    assert signal.summary.startswith("3 unresolved evaluation conflicts")
