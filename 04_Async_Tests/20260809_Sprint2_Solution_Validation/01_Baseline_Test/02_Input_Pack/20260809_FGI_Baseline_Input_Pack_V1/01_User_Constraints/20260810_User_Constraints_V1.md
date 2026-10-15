# User Constraints and Reproduction Goal

Version: V1
Date: 2026-08-10
Status: FREEZE

## 1. Reproduction Goal

判断当前条件是否值得开始 FGI 复现，并尽快形成一个可用于后续基线实验的可执行复现路径。

测试对象需要回答：

当前是否适合开始复现 FGI？

最终决策使用以下三类状态：

- 继续
- 有条件继续
- 暂停

本次准备度判断应重点识别：

- 当前关键缺失项；
- 主要复现风险；
- 无法确认的未知项；
- 支撑关键判断的证据；
- 下一步最重要的三项行动。

## 2. User Hardware Constraints

GPU Model:
NVIDIA GeForce RTX 2080 Ti

GPU VRAM:
11 GB per GPU

GPU Count:
3

System RAM:
125 GB

Available Disk Space:
367 GB

Storage Location:
DATACENTER3\

Linux Mount Path:
Unknown

Storage Writable:
Yes


## 3. System Constraints

Operating System:
Ubuntu 18.04.6 LTS

CUDA:
Unknown

Python:
Unknown

Deep Learning Framework:
Unknown


## 4. Network / Data Access Constraints

Internet Access:
Yes

Large-file Download:
Allowed

Dataset Access / Permission:
Unknown unless explicitly confirmed.

Existing Environment:
No assumption unless explicitly provided.

## 5. Time Constraint
Available Time Budget:
3 days

The goal is to obtain a minimally runnable FGI baseline within this time budget, or to determine before substantial execution that the current conditions are insufficient and the reproduction plan should be adjusted or paused.
该时间预算用于判断当前是否值得进入复现，以及是否需要先调整复现范围或准备顺序。

## 6. Information Boundary

若某项硬件、软件环境或依赖信息未在本文件中明确提供，则应视为当前未知信息。

测试对象不得自行假设未提供的系统条件已经满足。

所有 Baseline A / B / C 均使用完全相同的 User Constraints 和 Reproduction Goal。