# Baseline Test Record

Template ID: Baseline_Record_Template_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

## 1. Test Identification

Baseline:
Baseline A｜通用大模型自由对话

Test Date:
2026-08-10

Executor:
本人

Product / Tool / Model:
GPT-5.6 Sol

Displayed Version:
GPT-5.6 Sol

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
Yes. 能够通过正常联网/网页读取能力访问冻结 FGI Repository 及固定 Commit 下的公开文件。

Tool / Command Capability:
Built-in web search and webpage/source-code retrieval. 未执行依赖安装、数据下载、训练、推理、评测或代码修改。

Other Relevant Capability:
模型自主检索公开 Web 与 Repository。根据可见工具说明，约有 20 个网页/源码来源被搜索或核对；精确内部搜索次数不可完全观察。

## 3. Timing

Start Time:
23:04:00

End Time:
23:09:00

Total Duration:
5 minutes

Timeout:
No

## 4. Interaction Record

User Follow-up Count:
0

Search Count:
Unknown / Not fully observable

Material Switch Count:
Unknown / Not fully observable

Tool / Command Usage:
使用内置 Web 搜索及网页/源码读取能力；未执行实际复现。

Waiting / Error / Manual Intervention:
None observed

## 5. Raw Process Record

Baseline A 在干净的通用大模型新对话中执行，使用冻结 Input Pack 与 Same-task Prompt V1。

可见执行过程显示模型自主检索公开网页与固定 FGI Repository。工具说明显示约 20 个网页/源码来源被搜索或核对，包括 BMVC 论文、固定 Commit、README、package-list.txt、训练/测试脚本、数据加载与预处理脚本、数据划分列表等。

User follow-up rounds:
0

Raw Record Path:
04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/04_Raw_Outputs/Baseline_A_General_LLM/

Raw conversation preservation note:
完整原始对话应单独原样保留，不用本整理副本覆盖。

## 6. Final Output

### 6.1 总体决策
有条件继续。

建议现在开始 FGI 复现准备，但不要立即投入全量 100 epoch 训练；先验证固定 Commit、环境、少量 DFDC 数据预处理、官方权重推理与 AUC 流程是否跑通。

### 6.2 关键缺失项
- NVIDIA Driver 版本未知。
- DFDC Kaggle 数据访问权限未知。
- 当前 Python / Conda / PyTorch / CUDA 状态未知。
- 11 GB/GPU 下 batch size=8 的真实峰值显存未知。
- 数据预处理后的实际磁盘占用未知。
- 单个视频预处理速度、单 epoch 时间及三天内完成完整训练的可行性未知。

### 6.3 主要风险
1. 数据与磁盘风险：367 GB 可用空间是否足够容纳原始数据与预处理中间文件未知。
2. 论文与固定 Commit 的训练学习率存在不一致：论文写 1e-3，而公开代码/权重路径指向 1e-4。
3. README 与代码的数据 CSV 流程存在潜在文件名不一致。
4. 三张 GPU 可用于训练，但固定仓库不会自动将三张 GPU 用于预处理。
5. 三天内是否能完成完整下载、预处理、100 epoch 训练和测试无法确认。

### 6.4 证据出处
- BMVC 2024 正式论文。
- FGI GitHub 固定 Commit: 8c9ea77117878924c29dd87bc5e08a239842ed0f。
- 固定 Commit 下的 README.md、package-list.txt、my_train.py、dataset_3d.py、write_csv.py、pre-process.py、run_pipeline.py。
- train_real_list.txt / train_fake_list.txt / test_real_list.txt / test_fake_list.txt。
- DFDC Kaggle 官方页面。
- User Constraints 中的 GPU、RAM、367 GB 可用磁盘、Ubuntu 18.04.6 LTS 与 3-day time budget。

### 6.5 未知项
1. DFDC Kaggle 权限是否已经获得。
2. NVIDIA Driver 具体版本。
3. 当前 CUDA toolkit / runtime 状态。
4. 当前 Python、Conda、PyTorch 状态。
5. package-list.txt 是否能在当前机器一次性成功重建。
6. 11 GB/GPU 下 batch=8 的实际峰值显存。
7. RTX 2080 Ti ×3 上的单 epoch 时间。
8. 作者固定训练/测试视频对应的实际原始数据体积。
9. 完整预处理后的 pytmp 体积。
10. 预处理期间的峰值磁盘占用。
11. 全数据预处理所需时间。
12. 三天内能否完成完整 100 epoch。
13. 严格复现时应以论文 LR=1e-3 还是公开代码/权重 LR=1e-4 为准。
14. 官方权重文件的完整性、文件大小与校验值。

### 6.6 前三步行动
1. 环境 Gate：核对 Driver、Python、Conda、CUDA、PyTorch 以及三张 GPU 的可见性，不先下载大数据。
2. 数据与磁盘 Gate：确认 DFDC 权限和官方 checkpoint 可获得性，并用极少量样本测量预处理后的磁盘膨胀与耗时。
3. 最小 baseline 闭环：固定 Commit → 正确环境 → 少量 DFDC 视频 → preprocessing → CSV → 官方 checkpoint → inference/test → AUC/output；闭环通过后再决定是否进入完整训练。

## 7. Test Status

Final Status:
COMPLETED

Failure / Interruption Reason:
None

Notes:
- 首轮回答已完整覆盖六个冻结字段，未使用追问。
- 模型自主进行了较广泛的 Web / Repository 检索。
- 约 20 个网页/源码来源被报告为搜索或核对，但精确 Search Count 与 Material Switch Count 不可完全观察。
- 本文件为补齐元数据后的整理副本；原始上传记录和完整原始对话应继续保留。
