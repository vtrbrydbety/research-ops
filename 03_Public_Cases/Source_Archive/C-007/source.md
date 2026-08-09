# C-007 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#806
- 标题：FileNotFoundError for AVA dataset
- 链接：https://github.com/open-mmlab/mmaction2/issues/806
- 发布日期：2021-04-13
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：生成 AVA long-term feature bank 时读取不存在的帧文件，不同视频实际提取帧数低于流程预期。
- 关键回复：维护者和用户将差异定位到抽帧方式，建议重新裁剪视频并使用 ffmpeg 抽帧，避免 OpenCV 产生帧数偏差。
- 最终状态：部分解决；根因和建议明确，原用户表示将改用 ffmpeg。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
