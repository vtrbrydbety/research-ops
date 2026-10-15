# Baseline Test Record

Record ID: 20260810_Baseline_B_Record_V1
Source Template ID: Baseline_Record_Template_V1
Version: V1
Test Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

> Post-test completion note: 本文件是在不改写原始六字段结论的前提下，根据已记录的 Time / Interaction Log 补齐测试元数据。原始结论内容保持不变。

## 1. Test Identification

Baseline:
Baseline B｜人工现有流程

Test Date:
2026-08-10

Executor:
本人

Product / Tool / Model:
人工现有流程（Google Scholar / GitHub / Kaggle）

Displayed Version:
N/A（人工流程）

Frozen Material Versions:
- Paper: BMVC 2024 official published version
- Repository: aseuteurideu/FGI
- Frozen Commit: 8c9ea77117878924c29dd87bc5e08a239842ed0f

Baseline Test Protocol:
20260809_Baseline_Test_Protocol_V1

Input Pack:
20260809_FGI_Baseline_Input_Pack_V1

Same-task Prompt:
Same-task Prompt V1

Rubric:
Baseline Rubric V1

## 2. Test Environment

Search / Internet Available:
Yes

Repository Access:
Yes（人工浏览、读取与搜索）

Tool / Command Capability:
仅进行浏览器人工搜索、阅读与跨材料核对；未执行安装、数据下载、训练、推理或环境修改命令。

Other Relevant Capability:
可在论文、README、GitHub Repository 与 Kaggle 页面之间人工切换并进行信息比对。

## 3. Timing

Start Time:
17:32:00

End Time:
18:28:00

Total Duration:
56 minutes

Timeout:
No

## 4. Interaction Record

User Follow-up Count:
N/A

Search Count:
4（按事件日志中显式标记为 Search 的事件计数）

Material Switch Count:
3（仅按事件日志中显式标记为 Switch 的事件计数；其他跨材料阅读未追加计数）

Tool / Command Usage:
无命令执行；使用浏览器进行 Google Scholar / GitHub / Kaggle 人工搜索与阅读。

Waiting / Error / Manual Intervention:
None recorded

## 5. Raw Process Record

Baseline B 实际过程见对应 Time / Interaction Log。记录包含论文定位、仓库与 README 阅读、依赖文件查看、DFDC 数据获取方式核对、Kaggle 数据页面查看、训练/测试脚本与论文参数比对，以及最终人工决策。

Raw Record Path:
04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/04_Raw_Outputs/Baseline_B_Manual_Workflow/20260810_Baseline_B_Record_V1_COMPLETED.md

Time / Interaction Log Path:
04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/04_Raw_Outputs/Baseline_B_Manual_Workflow/20260810_Baseline_B_Time_Interaction_Log_V1_COMPLETED.md

## 6. Final Output

> 以下六字段保持测试结束时的原始结论，不做事后润色。

### 6.1 总体决策
有条件继续

### 6.2 关键缺失项
论文实际训练集大小未知，虽有训练集名单但原始数据集分块，不知道训练集是从哪一个分块获得。

### 6.3 主要风险
总数据集大小超出当前存储空间，可能影响后续的实验和分析。

### 6.4 证据出处
官方 www.kaggle.com 以及 User Hardware Constraints：Available Disk Space。

### 6.5 未知项
训练集的具体分块信息和大小尚不明确。

### 6.6 前三步行动
1. 查看是否能知道训练集的具体分块信息和大小。
2. 调整磁盘大小腾出空间下载整个数据集。
3. 从原始数据集中提取训练集并进行预处理，确保数据集完整性和可用性。

## 7. Test Status

Final Status:
COMPLETED

Failure / Interruption Reason:
None

Notes:
- 在 60 分钟上限内完成六字段输出并形成“有条件继续”决策。
- 测试结束时仍保留训练集具体分块信息、训练集大小及预处理后存储占用等未知项。
- 本文件仅补齐元数据；未将事后发现或评分阶段判断写回原始六字段结果。
