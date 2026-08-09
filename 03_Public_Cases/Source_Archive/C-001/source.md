# C-001 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：SCLBD/DeepfakeBench
- Issue：#110
- 标题：[HELP!] Loading image error
- 链接：https://github.com/SCLBD/DeepfakeBench/issues/110
- 发布日期：2024-09-28
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：用户按 README 启动 Xception 训练时出现图片加载错误。
- 关键回复：社区排错发现配置为 `lmdb=true`，但输入路径指向 PNG 原图，建议改为 `false`。
- 最终状态：用户确认修改后程序正常运行。
- 身份说明：关键建议来自社区回复，不标记为维护者回复。

## 归档文件

- issue.png

