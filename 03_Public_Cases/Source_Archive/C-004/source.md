# C-004 Source Information

## 来源

- 类型：GitHub Issue 回复链
- 仓库：SCLBD/DeepfakeBench
- Issue：#109
- 标题：[HELP!] The published weights fail to reproduce the results in the Readme Table.
- 链接：https://github.com/SCLBD/DeepfakeBench/issues/109
- 发布日期：2024-09-27
- 访问日期：2026-08-05

## 关键证据

- 回复链问题：用户使用约 90 GB 内存评测 DFDC 等大数据集时仍发生内存溢出，进程被系统终止。
- 关键回复：社区建议移除 `test_one_dataset` 中持续累积的 feature list 内容。
- 最终状态：报告者和另一名用户均确认修改后能够测试。
- 语境说明：这是 #109 内的子讨论，不是 Issue 标题所指的主问题。

## 归档文件

- issue.png

