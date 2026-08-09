# C-003 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：SCLBD/DeepfakeBench
- Issue：#79
- 标题：[BUG] Mismatched pretrained model architectures in efficientnetb4.py
- 链接：https://github.com/SCLBD/DeepfakeBench/issues/79
- 发布日期：2024-06-10
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：发布的 detector checkpoint 与 EfficientNetB4 初始化结构不匹配。
- 关键报错：`Missing key(s) in state_dict`、`Unexpected key(s) in state_dict`，并存在 `backbone.`、`resnet.` 前缀差异。
- 关键回复：发起者提出先调整模型结构，再以 `strict=False` 加载。
- 最终状态：社区用户称绕行方案已验证；Issue 仍开放，未确认仓库级修复。

## 归档文件

- issue.png

