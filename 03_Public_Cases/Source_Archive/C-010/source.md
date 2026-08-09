# C-010 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#670
- 标题：RuntimeError training SlowFast with custom AVA classes
- 链接：https://github.com/open-mmlab/mmaction2/issues/670
- 发布日期：2021-03-03
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：自定义 AVA 数据训练 SlowFast 时，时间维度经采样后变为 0；增大 clip length 后又触发 CUDA 显存不足。
- 关键回复：回复建议降低 resample rate 或增大 clip length，同时通过降低采样参数、batch 或更换 GPU 处理 OOM，并检查自定义类别配置。
- 最终状态：部分解决；给出可行调参方向，但存在精度与资源权衡。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
