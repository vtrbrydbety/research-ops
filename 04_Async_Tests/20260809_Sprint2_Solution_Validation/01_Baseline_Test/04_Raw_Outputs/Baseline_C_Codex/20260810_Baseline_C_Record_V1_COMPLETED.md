# Baseline Test Record

Template ID: Baseline_Record_Template_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

## 1. Test Identification

Baseline:
Baseline C｜Codex App

Test Date:
2026-08-10

Executor:
本人

Product / Tool / Model:
Codex App / codex-5.6 sol

Displayed Version:
5.6 sol

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
Yes. Codex App opened a local clone of the full FGI repository checked out at frozen commit:
8c9ea77117878924c29dd87bc5e08a239842ed0f

Tool / Command Capability:
Read-only repository inspection, code/file search, local informational commands, and public web search/webpage retrieval. No dependency installation, dataset/model download, training, inference, evaluation, deletion, overwrite, or source-code modification was approved.

Other Relevant Capability:
Codex App used the local repository workspace as its natural code-understanding environment. Repository clone/checkout/open-project time was recorded separately as Pre-test Setup Cost and excluded from Formal Decision Time.

## 3. Timing

Start Time:
14:57:00

End Time:
15:04:00

Total Duration:
7 minutes

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
Codex executed read-only/informational repository commands, repository/file inspection, and public web searches. The visible process included confirming the frozen commit, checking repository status/materials, and searching the BMVC 2024 paper. Exact internal command/search counts were not fully observable.

Waiting / Error / Manual Intervention:
None observed during the formal task.

## 5. Raw Process Record

Formal task started at 14:57:00 after the Codex App project workspace had already been prepared.

Visible process included:
- confirmation that the local repository matched frozen commit 8c9ea77117878924c29dd87bc5e08a239842ed0f;
- read-only repository commands / file inspection;
- public web search for the BMVC 2024 paper;
- inspection and cross-checking of README, dependency information, data preparation, training/testing code, dataset lists, and related reproduction constraints;
- no user follow-up.

Raw Record Path:
04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/04_Raw_Outputs/Baseline_C_Codex/20260810_Baseline_C_Record_V1_COMPLETED.md

Raw Conversation Path:
04_Async_Tests/20260809_Sprint2_Solution_Validation/01_Baseline_Test/04_Raw_Outputs/Baseline_C_Codex/20260810_Baseline_C_Raw_Conversation.txt

Pre-test Setup Cost:
5 minutes (14:50:00–14:55:00), recorded separately in the Time / Interaction Log and excluded from Formal Decision Time.

## 6. Final Output

> 以下内容保持 Codex 正式测试结束时的原始结论，不做事后事实修正或润色。

### 6.1 总体决策

有条件继续。

值得立即开始“环境验证 + 官方权重推理 + 小规模训练”的复现准备，但目前不建议直接投入完整 100 epoch 训练。

继续的必要条件是：在前 6–12 小时内确认数据授权与下载方式、CUDA/PyTorch 可用性，并用少量视频完成端到端冒烟测试。任一项无法通过，应暂停完整复现。

判断理由：
- 仓库已确认处于指定冻结提交 `8c9ea77117878924c29dd87bc5e08a239842ed0f`。
- 3×RTX 2080 Ti、125 GB RAM 原则上具备运行该模型的基础条件；仓库使用 `nn.DataParallel`，能够利用多 GPU。但论文没有报告训练硬件或耗时，因此不能保证 3 天内完成完整训练。
- 仓库提供了预处理、训练、测试、AUC 计算、固定数据名单和官方权重入口，足以形成基线路径。
- 最大障碍不是模型规模，而是数据授权、下载/预处理耗时、磁盘余量及论文—代码参数不一致。

建议将三天目标定义为：
1. 官方权重指标验证；
2. 小规模 DFDC 训练闭环；
3. 若资源实测允许，再启动完整训练。

不要把“完整 100 epoch 且达到论文 AUC”设为三天内必须完成的唯一成功标准。

### 6.2 关键缺失项

- DFDC 是否已获 Kaggle 访问权限：未知。
- FakeAVCeleb 申请是否已获批准：未知。
- 数据是否已下载、存放位置及实际大小：未知。
- NVIDIA 驱动、CUDA 和 PyTorch 状态：未知。
- 11 GB 显存能否承载官方 `batch_size=8`：未知，必须实测。
- 官方权重当前是否可下载、文件名及校验值：未知。
- 完整预处理和 100 epoch 的实测耗时：未知。
- 要复现的目标表格/容差：未知。

### 6.3 主要风险

- 高风险：数据访问和磁盘。
- 高风险：三天内完成完整训练没有证据保障。
- 高风险：论文和仓库默认训练参数不一致。
- 中高风险：旧环境可重建性。
- 中风险：显存。
- 中风险：指标口径混淆。

关键细节包括：
- 正式论文训练参数与冻结代码/README 默认学习率存在差异；
- 预处理会生成多类中间文件，367 GB 峰值空间是否足够未知；
- 仓库使用 `nn.DataParallel`，但三卡实际扩展效率和训练耗时未知；
- Python 3.7 / CUDA 11.6 / PyTorch 1.12.1 等旧软件栈的当前可重建性需要验证；
- 论文不同表格/设置的指标口径需要明确，否则容易把不同实验点混为同一复现目标。

### 6.4 证据出处

- BMVC 2024 正式论文及官方论文页。
- GitHub 固定 commit：
  `8c9ea77117878924c29dd87bc5e08a239842ed0f`
- README.md。
- package-list.txt。
- my_train.py。
- model.py。
- pre-process.py / run_pipeline.py。
- train_real_list.txt / train_fake_list.txt / test_real_list.txt。
- FakeAVCeleb 官方数据下载说明。
- User Constraints 中的 GPU、RAM、367 GB 可用磁盘、Ubuntu 18.04.6 LTS 与 3-day time budget。

Codex 原输出还给出了本地仓库文件的具体行级定位以及 BMVC / GitHub / FakeAVCeleb 的公开页面链接；完整原始引用应保留在 Raw Conversation 中。

### 6.5 未知项

- 作者实际使用的 GPU、GPU 数量、显存和训练耗时。
- 3×2080 Ti 上的吞吐量、显存峰值及 100 epoch 耗时。
- 367 GB 对“当前已有数据 + 下载文件 + 中间文件 + `pytmp`”是否足够。
- 用户是否已经接受 DFDC 竞赛规则、能否通过 Kaggle 下载。
- FakeAVCeleb 申请批准所需时间。
- Google Drive 官方权重是否仍完整可访问以及其哈希值。
- 论文表 2/3 的 `lr` 到底是正文所述 `1e-3`，还是发布权重名称暗示的 `1e-4`。
- 发布结果是否来自单次运行，以及随机种子波动范围。
- 仓库清单中的每个视频是否仍可从当前 DFDC 下载内容逐一恢复。
- 预处理失败视频的处理规则、作者最终实际成功纳入的视频数。
- 可接受的复现误差范围。

### 6.6 前三步行动

1. **先做资源与授权门禁检查。**  
   记录 `nvidia-smi`、驱动版本、三卡可见性、Conda/Python 状态；同时确认 DFDC/FakeAVCeleb 权限、已有文件大小和实际可用磁盘。若数据不可访问或预计峰值空间超过 367 GB，立即暂停全量路线。

2. **用官方权重和极小数据完成端到端冒烟测试。**  
   下载并保存权重校验值；选取少量 real/fake 视频，依次运行预处理、CSV 生成、模型推理和 AUC 脚本。同步测量单样本磁盘膨胀、预处理速度、推理显存，并验证三张 GPU 是否被代码识别。

3. **运行短训练标定，再决定是否全量。**  
   使用小规模 CSV 跑 1–3 epoch，先测试官方 batch 8；记录每卡显存、每 epoch 时间和失败率。建立 `paper-spec` 与 `released-code` 两个显式配置，根据实测耗时外推 100 epoch，只有当完整预处理和训练预计能落在剩余时间、磁盘与显存预算内时才启动全量训练。

## 7. Test Status

Final Status:
COMPLETED

Failure / Interruption Reason:
None

Notes:
- 首轮回答已完整覆盖六个冻结输出字段，User Follow-up Count = 0。
- Formal Decision Time = 7 minutes。
- Pre-test Setup Cost = 5 minutes，单独记录，不计入 Formal Decision Time。
- 本文件为补齐测试元数据后的整理副本；原始上传文件与完整 Raw Conversation 应继续保留。
- 本整理不对 Codex 输出中的技术事实进行事后纠正；事实准确性若需要，应在独立审计阶段处理。
