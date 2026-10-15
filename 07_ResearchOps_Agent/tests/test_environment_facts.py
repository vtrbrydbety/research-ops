"""授权环境事实获取与 RD-02 比较规则测试。"""

from researchops.services import EnvironmentFacts, EnvironmentFactService

PACKAGE_LIST = """\
cudatoolkit=11.6.0=hecad31d_10
python=3.7.16=h7a1cb2a_0
torch=1.12.1+cu116=pypi_0
"""


def test_unprovided_environment_remains_unknown() -> None:
    """只有项目依赖、没有当前环境事实时不得误判 Warning。"""

    service = EnvironmentFactService()
    requirements = service.extract_requirements(PACKAGE_LIST)
    comparison = service.compare(requirements, None)

    assert requirements.python == "3.7.16"
    assert requirements.framework == "1.12.1+cu116"
    assert requirements.cuda == "11.6.0"
    assert comparison.status == "Unknown"


def test_known_version_difference_is_warning() -> None:
    """所有关键事实均可比较且存在差异时形成已知非阻塞风险。"""

    service = EnvironmentFactService()
    requirements = service.extract_requirements(PACKAGE_LIST)
    facts = EnvironmentFacts(
        source_mode="manual",
        python="3.11.8",
        framework="2.2.0",
        cuda="12.1",
    )

    comparison = service.compare(requirements, facts)

    assert comparison.status == "Warning"
    assert comparison.finding_type == "Inference"
    assert "Python" in comparison.finding_summary


def test_aligned_versions_support_ready() -> None:
    """Python、Framework、CUDA 均按声明版本对齐时可支持 Ready。"""

    service = EnvironmentFactService()
    requirements = service.extract_requirements(PACKAGE_LIST)
    facts = EnvironmentFacts(
        source_mode="snapshot",
        python="3.7.12",
        framework="1.12.9+cu116",
        cuda="11.6",
    )

    comparison = service.compare(requirements, facts)

    assert comparison.status == "Ready"
    assert comparison.finding_type == "Fact"


def test_readonly_mode_requires_explicit_authorization() -> None:
    """未携带授权标记时不得读取本机环境。"""

    class GuardedEnvironmentFactService(EnvironmentFactService):
        def _read_local_environment(self) -> EnvironmentFacts:
            raise AssertionError("local environment must not be read")

    facts = GuardedEnvironmentFactService().acquire(
        "readonly",
        authorized=False,
        supplied_text=None,
    )

    assert facts is None


def test_manual_environment_text_is_structured_without_execution() -> None:
    """Manual Input 只解析已提供的环境字段。"""

    facts = EnvironmentFactService().acquire(
        "manual",
        authorized=False,
        supplied_text=(
            "OS: Ubuntu 22.04\n"
            "Python: 3.10.13\n"
            "PyTorch: 2.1.0\n"
            "CUDA: 12.1\n"
            "Driver: 535.104\n"
            "GPU: RTX 4090\n"
            "Available disk: 367 GB\n"
        ),
    )

    assert facts is not None
    assert facts.python == "3.10.13"
    assert facts.framework == "2.1.0"
    assert facts.cuda == "12.1"
    assert facts.available_disk_gb == 367
