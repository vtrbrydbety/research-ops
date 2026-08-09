# C-008 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#904
- 标题：Optical flow inference requests nonexistent frame
- 链接：https://github.com/open-mmlab/mmaction2/issues/904
- 发布日期：2021-06-04
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：对光流帧执行单视频推理时，工具错误计算总帧数并请求不存在的文件；简单修改 `start_index` 无效。
- 关键回复：讨论确认 `inference_recognizer` 对光流总帧数计算有缺陷；用户以文件数除以 2 绕过，贡献者提出按文件名和模态计算的修复。
- 最终状态：已解决；用户确认修复方向有效。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
