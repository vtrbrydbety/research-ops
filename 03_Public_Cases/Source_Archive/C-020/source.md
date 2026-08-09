# C-020 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#810
- 标题：How do I compute validation loss during training?
- 链接：https://github.com/facebookresearch/detectron2/issues/810
- 发布日期：2020-02-05
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：自定义 Hook 使用默认测试 DataLoader 计算验证损失时缺少 ground truth，切换 loader 后又因调用方式错误失败。
- 关键回复：维护者说明默认测试 mapper 会移除 ground truth，应通过 `mapper=` 构建保留标注的数据加载器；用户修正复制错误后确认可用。
- 最终状态：已解决。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
