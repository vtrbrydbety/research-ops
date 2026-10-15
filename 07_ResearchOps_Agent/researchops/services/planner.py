"""论文复现计划生成服务。

该模块定义稳定的 PlannerService 抽象接口，并提供 Day 1 使用的
RuleBasedPlanner。未来接入大模型时，只需新增 LLMPlanner，而不需要
修改 LangGraph 节点对规划服务的调用方式。
"""

from abc import ABC, abstractmethod

from researchops.schemas import PlanStep, ReproductionPlan


class PlannerService(ABC):
    """论文复现计划生成服务的抽象接口。

    LangGraph 节点只依赖该抽象接口，不直接依赖具体规则规划器或大模型，
    从而保持业务逻辑可测试、可替换。
    """

    @abstractmethod
    def generate_plan(
        self,
        normalized_request: str,
    ) -> ReproductionPlan:
        """根据标准化用户需求生成结构化复现计划。

        Args:
            normalized_request: 经过清理和标准化的用户任务描述。

        Returns:
            包含目标、前置条件、步骤、风险和产物的复现计划。

        Raises:
            ValueError: 当标准化请求为空时抛出。
        """


class RuleBasedPlanner(PlannerService):
    """不依赖网络和大模型 API 的规则规划器。

    Day 1 的目标是验证工程主干，而不是验证大模型规划能力。因此，
    该实现使用固定但结构完整的六步模板，保证项目能够离线运行和测试。
    """

    def generate_plan(
        self,
        normalized_request: str,
    ) -> ReproductionPlan:
        """为论文复现需求生成固定结构的六步执行计划。"""
        request = normalized_request.strip()

        if not request:
            raise ValueError("标准化请求不能为空。")

        # ReproductionPlan.objective 最长为 1000 个字符。
        # 这里只保留请求前 700 个字符，避免异常长输入导致模型校验失败。
        objective_request = request[:700]

        return ReproductionPlan(
            objective=(
                "为以下需求准备一份可执行、可验证且包含人工审批边界的"
                f"论文复现计划：{objective_request}"
            ),
            assumptions=[
                "当前阶段只生成复现计划，不直接执行任何外部命令。",
                "论文、代码仓库、数据集和 checkpoint 将在后续阶段真实接入。",
                "所有可能改变外部环境的操作必须经过人工审批。",
            ],
            prerequisites=[
                "论文正文、README 或其他方法说明文档",
                "项目代码仓库地址",
                "数据集获取与目录结构说明",
                "预训练 checkpoint 获取与加载说明",
                "可用于后续复现的 Python 运行环境",
            ],
            steps=[
                PlanStep(
                    step_id=1,
                    title="收集论文与仓库资产",
                    description=(
                        "确认论文、代码仓库、README、配置文件以及预训练权重说明是否完整可用。"
                    ),
                    tool="asset_collector",
                    approval_required=False,
                    expected_output="论文复现所需资产的结构化清单。",
                ),
                PlanStep(
                    step_id=2,
                    title="分析运行环境依赖",
                    description=(
                        "整理 Python、深度学习框架、CUDA、系统工具和"
                        "第三方依赖要求，但当前阶段不安装或修改环境。"
                    ),
                    tool="environment_inspector",
                    approval_required=False,
                    expected_output="包含版本与兼容性要求的环境依赖清单。",
                ),
                PlanStep(
                    step_id=3,
                    title="检查数据集与 checkpoint",
                    description=(
                        "检查数据集名称、目录结构、预处理要求、checkpoint 文件及其加载方式。"
                    ),
                    tool="artifact_inspector",
                    approval_required=False,
                    expected_output="数据集与 checkpoint 可用性检查结果。",
                ),
                PlanStep(
                    step_id=4,
                    title="生成预训练推理命令",
                    description=(
                        "根据项目文档生成候选推理命令和参数说明，但不在当前步骤实际运行命令。"
                    ),
                    tool="command_builder",
                    approval_required=False,
                    expected_output="等待人工审核的候选推理命令。",
                ),
                PlanStep(
                    step_id=5,
                    title="人工审批执行方案",
                    description=(
                        "由用户检查数据路径、checkpoint、设备、命令参数"
                        "和预期资源消耗，确认后才能进入执行阶段。"
                    ),
                    tool="human_approval",
                    approval_required=True,
                    expected_output="明确的批准、拒绝或修改意见。",
                ),
                PlanStep(
                    step_id=6,
                    title="执行推理并生成结果报告",
                    description=(
                        "在获得人工批准后执行预训练模型推理，收集日志、指标、异常信息和复现结论。"
                    ),
                    tool="shell",
                    approval_required=True,
                    expected_output="推理日志、评估指标和结构化复现报告。",
                ),
            ],
            risks=[
                "论文代码可能依赖过期或相互冲突的软件版本。",
                "数据集或 checkpoint 可能无法公开获取。",
                "实际推理可能需要 CUDA、GPU 和较大磁盘空间。",
                "仓库文档中的命令可能包含错误路径或不安全参数。",
            ],
            final_outputs=[
                "论文与代码资产清单",
                "环境依赖与兼容性报告",
                "数据集和 checkpoint 检查结果",
                "经过人工审批的推理命令",
                "推理日志、评估结果与复现报告",
            ],
        )
