# Time / Interaction Log

Log ID: 20260810_Baseline_B_Time_Interaction_Log_V1
Source Template ID: Time_Interaction_Log_V1
Version: V1
Test Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

> Post-test completion note: 本文件依据原始事件记录补齐时间、计数与成本字段；事件内容未新增外部事实。

Baseline:
Baseline B｜人工现有流程

## Timing

Start Time:
17:32:00

End Time:
18:28:00

Total Duration:
56 minutes

Timeout:
No

## Interaction

User Follow-up Count:
N/A

Search Count:
4（按显式 Search 事件计数：17:37、17:43、17:51、17:56）

Material Switch Count:
3（按显式 Switch 事件计数：17:45、17:47、17:53）

Repository Search / File Lookup Count:
10（按事件日志中涉及 GitHub Repository / Repository 文件查看的记录计数）

Tool / Command Count:
0（未执行命令；仅人工浏览、搜索与阅读）

## Event Log

| Time | Event Type | Action / Material | Result | Notes |
|---|---|---|---|---|
| 17:32 | Start | Baseline B 正式开始 | 开始计时 | - |
| 17:37 | Search | 搜索 FGI BMVC 2024 paper | 找到官方论文页面 | - |
| 17:42 | Read | FGI Paper | 开始阅读论文 | - |
| 17:43 | Search | GitHub Repository | 开始查看仓库 | - |
| 17:45 | Switch | GitHub Repository | 开始查看 README | - |
| 17:47 | Switch | GitHub Repository | 开始查看环境依赖包 | 找到 package-list.txt | - |
| 17:51 | Search | GitHub Repository | 开始查看 DFDC 数据获取方式 | - | - |
| 17:53 | Switch | GitHub Repository | 查看实验使用的 DFDC 数据列表、数据预处理方式和命令脚本 | - | - |
| 17:56 | Search | DFDC 官方 Kaggle 页面 | 查看 DFDC 数据集下载方式 | 需要登录/注册 Kaggle 账号，并参加竞赛后下载 | Unknown |
| 18:00 | Read | Kaggle | 查看下载页面 | 发现总数据集大小 | - |
| 18:02 | Compare | Kaggle | 对比总数据集分块 | 不确定论文训练集来自哪一个分块，且训练集大小未知 | Unknown |
| 18:08 | Compare | Kaggle + User Constraints | 评估下载数据集可行性 | 记录总数据集约 471.84 GB；当前可用磁盘 367 GB | 不能装下整个数据集 |
| 18:08 | Read | GitHub Repository | 评估数据预处理后大概占多大空间 | 无法确认 | Unknown |
| 18:12 | Read | GitHub Repository | 查看 FakeAVCeleb 数据集获取方式 | 需联系作者获取下载脚本 | Unknown |
| 18:15 | Read | GitHub Repository | 查看 FakeAVCeleb 数据集预处理方式 | 有预处理脚本 | - |
| 18:18 | Read | GitHub Repository | 查看实验训练脚本 | README 有训练脚本使用方式；部分训练参数需由论文补充 | - |
| 18:19 | Read | FGI Paper | 核对实验训练参数与仓库描述 | 论文补充了仓库中未明确的训练参数信息 | - |
| 18:22 | Read | FGI Paper + GitHub Repository | 查看实验测试脚本 | README 有测试脚本使用方式；论文提供测试参数 | - |
| 18:28 | Decision | 20260810_Baseline_B_Record_V1.md | 形成最终决策 | 有条件继续 |

## Cost Notes

明显等待：
None recorded

报错：
None recorded

人工干预：
None recorded

其他摩擦：
- DFDC 原始数据分块与论文实际训练集之间的映射关系未能确认。
- 训练集实际大小未能确认。
- 数据预处理后的额外存储占用未能确认。
- 部分训练参数需要在论文与仓库之间来回核对，单靠仓库信息不足。

## Counting Note

- Search Count 仅统计原日志中显式标记为 `Search` 的事件。
- Material Switch Count 仅统计原日志中显式标记为 `Switch` 的事件，因此不会把所有实际跨页面/跨材料行为都计算进去。
- Repository Search / File Lookup Count 为根据现有事件日志事后汇总的近似计数，用于效率分析，不改变原始事件记录。
