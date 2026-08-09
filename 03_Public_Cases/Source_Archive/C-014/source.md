# C-014 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#4487
- 标题：ImportError: is_fx_tracing in official Colab demo
- 链接：https://github.com/facebookresearch/detectron2/issues/4487
- 发布日期：2022-08-18
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：官方 Colab 示例突然无法从 `torch.fx._symbolic_trace` 导入 `is_fx_tracing`。
- 关键回复：社区提供临时注释代码的绕过方法，也有人通过安装匹配的 Detectron2 发布版本恢复运行。
- 最终状态：部分解决；有社区绕过方案，无统一维护者结论。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
