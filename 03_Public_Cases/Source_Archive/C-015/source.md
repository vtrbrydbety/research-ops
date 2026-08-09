# C-015 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#1018
- 标题：ImportError: cannot import name _C
- 链接：https://github.com/facebookresearch/detectron2/issues/1018
- 发布日期：2020-03-10
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：运行 PointRend 或 DensePose 示例时无法导入 Detectron2 编译扩展 `_C`。
- 关键回复：维护者指出用户在源码仓库根目录运行，未编译源码遮蔽了已安装包；建议离开该目录并按安装文档确认安装。
- 最终状态：根因和处理方法明确；Issue 已关闭。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
