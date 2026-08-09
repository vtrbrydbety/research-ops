# C-011 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#414
- 标题：ONNX to TensorRT conversion error
- 链接：https://github.com/open-mmlab/mmaction2/issues/414
- 发布日期：2020-12-03
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：模型可导出并通过 ONNX 验证，但 TensorRT 转换因 PyTorch 1.7 生成不支持的 ONNX `If` 节点失败。
- 关键回复：维护者建议降级 PyTorch；用户在 PyTorch 1.5 环境中得到 `squeeze` 节点并成功完成 TensorRT 转换。
- 最终状态：已解决。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
