# C-017 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#2365
- 标题：CUDA device-side assert during custom dataset training
- 链接：https://github.com/facebookresearch/detectron2/issues/2365
- 发布日期：2020-12-10
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：自定义数据训练出现 CUDA device-side assert，异步堆栈难以直接定位。
- 关键回复：维护者建议设置 `CUDA_LAUNCH_BLOCKING=1` 获取准确位置，随后发现数据中存在 333，而模型只预期 0～2。
- 最终状态：已定位并解决根因。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
