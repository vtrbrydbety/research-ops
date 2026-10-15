# Time / Interaction Log

Template ID: Time_Interaction_Log_V1
Version: V1
Date: 2026-08-10
Status: FREEZE

Baseline:
<Baseline B>

Test Date:
<填写>

## Timing

Start Time:
<17:32:00>

End Time:
<填写>

Total Duration:
<分钟>

Timeout:
<Yes / No>


## Interaction

User Follow-up Count:
<填写>

Search Count:
<填写>

Material Switch Count:
<填写>

Repository Search / File Lookup Count:
<能记录则填写，否则 Unknown>

Tool / Command Count:
<填写或 N/A>


## Event Log

| Time | Event Type | Action / Material | Result | Notes |
|---|---|---|---|---|
| | Start | | | |
| | Read | | | |
| | Search | | | |
| | Switch | | | |
| | Follow-up | | | |
| | Tool | | | |
| | Error | | | |
| | Decision | | | |

17:32 | Start | Baseline B 正式开始 | -

17:37 | Search | 搜索 FGI BMVC 2024 paper | 找到官方论文页面 | -

17:42 | Read | FGI Paper | 开始阅读论文 | -

17:43 | Search | GitHub Repository | 开始查看仓库 | -

17:45 | Switch | GitHub Repository | 开始查看 README | -

17:47 | Switch | GitHub Repository | 开始查看环境依赖包 | package-list.txt

17:51 | Search | GitHub Repository | 开始查看 DFDC数据获取方式 | -

17:53 | Switch | GitHub Repository | 开始查看实验使用的DFDC数据列表以及数据预处理方式和命令脚本 | -

17:56 | Search | DFDC官方www.kaggle.com | 开始查看DFDC数据集下载方式 | 需要登录注册kaggle账号,需要参加竞赛才能下载数据集 | Unknown

18:00 | Read | www.kaggle.com | 查看下载页面 | 发现总数据集大小

18:02 | 对比 | www.kaggle.com | 总数据集分块 | 不确定论文数据集来自哪一个模块，且不知训练集有多大 | Unknown

18:08 | 对比 | 评估下载数据集的可行性 | 数据集总大小约为 471.84GB，当前磁盘空间为367 GB | 不能装下整个数据集

18:08 | Read | GitHub Repository | 评估数据集预处理后大概占多大空间 | Unknown

18:12 | Read | GitHub Repository | 查看FakeAVCeleb数据集获取方式 | 需联系作者获取下载脚本 | Unknown

18:15 | Read | GitHub Repository | 查看FakeAVCeleb数据集预处理方式 | 有预处理脚本

18:18 | Read | GitHub Repository | 查看实验训练脚本 | 有相关脚本，且作者在README中说明了训练脚本的使用方式，但训练脚本中没有提供训练参数，论文中有提供训练参数

18:19 | Read | FGI Paper | 查看实验训练参数与论文实验设置描述是否一致 | 论文描述了仓库中没有的训练参数，补充了仓库信息

18:22 | Read | FGI Paper GitHub Repository | 查看实验测试脚本 | 有相关脚本，且作者在README中说明了脚本的使用方式，且论文中有提供测试参数

18:28 | write | 20260810_Baseline_B_Record_V1.md | 做最终决策 | 有条件继续



## Cost Notes

明显等待：
<None / 填写>

报错：
<None / 填写>

人工干预：
<None / 填写>

其他摩擦：
<None / 填写>