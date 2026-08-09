# C-009 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#421
- 标题：Single GPU training hangs
- 链接：https://github.com/open-mmlab/mmaction2/issues/421
- 发布日期：2020-12-06
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：单 GPU 训练停在数据加载阶段，没有继续输出；将 `workers_per_gpu` 设为 0 后恢复。
- 关键回复：回复将问题定位为多进程 DataLoader 的共享内存不足，建议降低 worker 数；用户确认设为 0 可运行。
- 最终状态：已解决。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
