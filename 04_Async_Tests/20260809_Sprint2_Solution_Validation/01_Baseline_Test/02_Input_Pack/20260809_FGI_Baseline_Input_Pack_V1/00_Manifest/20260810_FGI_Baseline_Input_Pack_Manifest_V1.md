# FGI Baseline Input Pack Manifest

Pack ID: 20260809_FGI_Baseline_Input_Pack_V1
Manifest Version: V1
Manifest Date: 2026-08-10
Status: FREEZE

## 1. Purpose

本 Input Pack 用于 ResearchOps Sprint 2 Baseline 同题测试。

Baseline A｜通用大模型自由对话
Baseline B｜人工现有流程
Baseline C｜Codex

均以本 Input Pack 中冻结的任务对象、基础来源和用户约束作为统一起点。

本 Input Pack 不包含 ResearchOps 已生成的准备度结论、风险排序、准备度卡结果或其他答案性信息。

## 2. Frozen Materials

| ID | 材料 | 冻结对象 | 冻结方式 | 访问方式 | 状态 |
|---|---|---|---|---|---|
| IP-01 | FGI Paper | BMVC 2024 正式论文 | 固定正式发表版本 | 官方来源访问 | Frozen |
| IP-02 | FGI Repository | aseuteurideu/FGI | Repository + Frozen Commit | GitHub 固定版本访问 | Frozen |
| IP-03 | README | IP-02 Frozen Commit 下的 README.md | 随 Repository Commit 固定 | 从固定仓库读取 | Frozen |
| IP-04 | User Constraints | 硬件 / 系统 / 存储 / 网络 / 时间条件 | 与 IP-05 共同冻结在 `20260810_User_Constraints_V1.md` | 文件第 2 节及后续约束字段 | Frozen |
| IP-05 | Reproduction Goal | 复现准备判断目标、决策状态及统一输出重点 | 与 IP-04 共同冻结在 `20260810_User_Constraints_V1.md` | 文件第 1 节 `Reproduction Goal` | Frozen |

### 2.1 IP-04 / IP-05 共同交付物说明

IP-04 User Constraints 与 IP-05 Reproduction Goal 是两个独立的冻结材料项，但不分别建立两个文件。二者共同保存在以下正式交付物中：

`01_User_Constraints/20260810_User_Constraints_V1.md`

其中：

- 第 1 节 `Reproduction Goal` 对应 IP-05，冻结复现准备判断目标、继续 / 有条件继续 / 暂停三类决策状态，以及缺失项、风险、Unknown、证据和前三步行动等统一输出重点；
- 第 2 节及后续约束字段对应 IP-04，冻结用户硬件、系统、存储、网络与时间条件。

因此，IP-05 已作为上述共同交付物中的正式章节完成冻结，不需要另建独立的 Reproduction Goal 文件。

## 3. Paper Record

Material ID: IP-01

Title:
Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies

Publication:
BMVC 2024

Frozen Version:
BMVC 2024 official published version

Source Type:
Official publication source

Access Rule:
Baseline 测试以该正式论文版本作为论文基准。
允许各 Baseline 按其正常能力访问和阅读该固定论文来源。

Local Copy:
Not required

## 4. Repository Record

Material ID: IP-02

Repository:
aseuteurideu/FGI

Branch:
master

Frozen Commit:
8c9ea77117878924c29dd87bc5e08a239842ed0f

Freeze Date:
2026-08-10

README Rule:
README 以该 Frozen Commit 对应版本为准。

Access Rule:
Baseline 测试以该 Commit 对应仓库内容作为代码与仓库基准版本。

Local Copy:
Not required

## 5. External Retrieval Boundary

Paper 和 Repository 是统一冻结的基础对象。

Baseline A / B / C 可按照 Baseline Test Protocol 中各自允许的正常搜索、联网和仓库检索能力获取补充信息。

通过外部搜索获得的信息不自动视为 Input Pack 基础材料，应在对应 Baseline 原始记录中单独记录其来源和获取过程。

不得因为某一 Baseline 表现较差而将其搜索得到的信息补充进其他对象的 Input Pack。

## 6. Information Boundary

Input Pack 不得提前加入：

- ResearchOps 准备度卡结果；
- “已满足 / 阻塞 / 未知”的预判；
- 已整理好的风险优先级；
- ResearchOps 生成的前三步行动；
- 针对某个 Baseline 准备的答案性提示。

现有材料无法确认的信息，应保留为信息缺口，由 Baseline 自行识别。

## 7. Repository Discovery Boundary

除 README 外，不在 Input Pack 中额外预选或复制特定配置、依赖、数据处理、训练或测试脚本。

包括但不限于：

- package-list.txt
- pre-process.py
- write_csv.py
- my_train.py
- my_test.py
- 其他配置、脚本和代码文件

上述文件均保留在 IP-02 所冻结的 Repository 中，由各 Baseline 根据任务需要自行发现、读取和判断其重要性。

本 Input Pack 不提供“关键文件清单”“推荐阅读顺序”或人工整理后的脚本摘要，以避免提前完成本应由 Baseline 完成的信息定位工作。

## 8. GitHub Issue and External Retrieval Boundary

GitHub Issues 不作为预先筛选后的 Input Pack 基础材料。

Baseline 可按照 Baseline Test Protocol 中各自允许的正常信息获取方式，自行搜索 Repository Issues 或其他外部信息源。

不得提前向任一 Baseline 提供人工挑选的“关键 Issue”列表。

通过 GitHub Issue、搜索引擎或其他外部来源获得的信息属于 External Retrieval，应在对应 Baseline 的原始过程记录中保留来源和获取过程。
