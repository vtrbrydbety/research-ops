# C-012 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：open-mmlab/mmaction2
- Issue：#732
- 标题：SlowFast custom data mAP remains zero
- 链接：https://github.com/open-mmlab/mmaction2/issues/732
- 发布日期：2021-03-16
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：受硬件限制将 clip length 调低后，自定义 SlowFast 训练多轮 mAP 始终为 0，并伴随类别数断言和显存约束。
- 关键回复：回复建议核对配置，使用更轻的 SlowOnly，设置较小 batch；若恢复 clip length，应同步降低 batch 和学习率。
- 最终状态：未确认；获得诊断和配置建议，但没有用户最终成功记录。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
