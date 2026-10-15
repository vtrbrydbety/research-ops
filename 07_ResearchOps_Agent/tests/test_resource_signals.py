"""Resource Constraint Signal 冻结规则测试。"""

from researchops.services import EnvironmentFacts, RepositoryTextFile, ResourceSignalService


def readme(text: str) -> RepositoryTextFile:
    return RepositoryTextFile(
        path="README.md",
        text=text,
        html_url="https://github.com/example/project/blob/main/README.md",
        size=len(text.encode()),
    )


def test_known_current_resources_without_project_minimum_remain_unknown() -> None:
    """当前资源已知但项目最低要求未知时不能判 Warning 或 Blocked。"""

    facts = EnvironmentFacts(
        source_mode="readonly",
        gpu="NVIDIA GeForce GTX 1650",
        vram_gb=4,
        available_disk_gb=200.5,
    )
    signal = ResourceSignalService().create(
        readme("Run training for 100 epochs."),
        facts,
        repository_url="https://github.com/example/project",
    )

    assert signal.status == "Unknown"
    assert signal.items[0].current == "NVIDIA GeForce GTX 1650 / 4 GB VRAM"
    assert signal.items[0].required == "Not confirmed"
    assert signal.items[1].current == "200.5 GB available"


def test_confirmed_resource_shortfall_is_blocked() -> None:
    """明确最低要求且当前容量不足时才形成 Resource Blocked Signal。"""

    facts = EnvironmentFacts(
        source_mode="manual",
        gpu="Example GPU",
        vram_gb=8,
        available_disk_gb=300,
    )
    signal = ResourceSignalService().create(
        readme("Requires a GPU with at least 12 GB VRAM and at least 500 GB disk."),
        facts,
        repository_url="https://github.com/example/project",
    )

    assert signal.status == "Blocked"
    assert "8 GB is below required 12 GB" in signal.summary
    assert "300 GB is below required 500 GB" in signal.summary


def test_narrow_confirmed_resource_margin_is_warning() -> None:
    """满足明确最低值但余量很小时形成非阻塞 Warning。"""

    facts = EnvironmentFacts(source_mode="snapshot", vram_gb=13)
    signal = ResourceSignalService().create(
        readme("Minimum 12 GB VRAM required."),
        facts,
        repository_url="https://github.com/example/project",
    )

    assert signal.status == "Warning"
    assert "close to required" in signal.summary


def test_confirmed_time_budget_shortfall_is_blocked() -> None:
    material = readme("The minimum validation takes 12 hours.\n")
    facts = EnvironmentFacts(source_mode="manual", time_budget="8 hours")

    signal = ResourceSignalService().create(
        material,
        facts,
        repository_url="https://github.com/example/project",
    )

    assert signal.status == "Blocked"
    assert signal.items[2].current == "8 hours"
    assert signal.items[2].required == ">= 12 hours"
    assert "Time budget 8 hours is below required 12 hours" in signal.summary
