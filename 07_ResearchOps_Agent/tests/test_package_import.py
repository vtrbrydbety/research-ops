"""项目 Python 包安装与导入测试。"""


def test_package_import() -> None:
    """验证 researchops 包可以被正常导入并暴露正确版本号。"""
    import researchops

    assert researchops.__version__ == "0.1.0"
