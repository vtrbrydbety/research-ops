# C-006 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：SCLBD/DeepfakeBench
- Issue：#68
- 标题：Error occurred in SBI
- 链接：https://github.com/SCLBD/DeepfakeBench/issues/68
- 发布日期：2024-05-14
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：SBI 数据增强在生成掩膜时出现二维数组按三维索引，以及图像对象为 None 的类型错误。
- 关键回复：社区指出 `random_get_hull` 返回值维度已变化，建议移除 `[:,:,0]` 索引；部分用户继续遇到形状或内存问题。
- 最终状态：部分解决；Issue 已关闭，但修复对不同环境并非完全一致。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
