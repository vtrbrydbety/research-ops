# ResearchOps — Safety Boundary V1

**Document ID:** 20260826_Safety_Boundary_V1  
**Version:** V1  
**Date:** 2026-08-26  
**Status:** COMPLETED FOR SPRINT 2 DAY 4

---

## 1. 目的与边界

本文件定义 ResearchOps MVP 在复现准备度评估阶段的安全与控制边界，明确 AI、Rule 与 Human 的职责分工，以及当前系统允许读取、分析、判断和建议的范围。

当前 V1 的核心边界是：

> ResearchOps 提供基于 Evidence 的复现准备度决策支持，但不取得写入、执行、高成本投入或不可逆操作的控制权。

本文件不建设完整企业级权限系统、审批流、审计平台或运行后自动修复体系；这些均不属于当前 MVP。

---

## 2. Responsibility Boundary

| Role | 当前职责 | 不得解释为 |
|---|---|---|
| **AI** | 关联材料发现与理解、信息关联、Evidence 定位、风险 / 冲突提示、Finding 草拟 | 最终确定性事实裁决；高风险动作授权；最终投入决策 |
| **Rule** | Ready / Warning / Blocked / Unknown 计算、Overall Gate 聚合、Next Action 优先级、安全规则与字段一致性 | 替代人工判断所有复杂事实；在证据不足时强行生成确定结论 |
| **Human** | Target / Source 歧义确认、访问授权、Evidence 纠错、最终是否投入完整复现；若未来引入高风险 / 不可逆能力，则负责相应审批与确认 | 被动接受系统结论；放弃最终控制权 |

AI、Rule、Human 不是三级审批链：

```text
AI
发现 / 整理 / 草拟
        ↓
Rule
按冻结规则约束判断
        ↓
Human
在真实歧义、授权、纠错与最终投入等关键控制点介入
```

AI 不负责最终裁决复杂事实；Rule 不创造事实；Human 不需要逐条确认系统的每一个普通分析步骤。

---

## 3. 四条最高安全原则

### SB-01｜Evidence before certainty

证据不足、冲突或 Gate-critical 输入缺失时，不得通过 AI 猜测或 Rule 强行补成确定结论。

系统应保留 Fact / Inference / Unknown 的区别，并按真实依赖关系处理 Unknown。

### SB-02｜Authorized read-only only in current MVP

当前 MVP 的系统访问能力**仅限用户明确授权范围内的只读读取**。

Read-only 表示系统可以读取、解析和结构化已授权信息，但不得改变：

- 目标材料；
- 项目文件；
- 执行环境；
- 权限状态；
- 项目运行状态。

当前 V1 不存在 Read-only 的写入 / 执行例外。

### SB-03｜Confirmation ≠ Authorization

Target / Source Confirmation 解决：

> “系统分析的是不是正确对象？”

Authorization 解决：

> “系统是否被允许读取？”

两者必须独立处理，不得因为用户确认了目标对象，就默认系统已经获得读取授权。

### SB-04｜Decision support ≠ Execution authority

Overall Gate 与 Next Action 仅提供决策支持。

它们不授予 ResearchOps：

- 写入权限；
- 环境修改权限；
- 高成本训练权限；
- 不可逆动作权限；
- 代替用户作最终投入决策的权限。

---

## 4. Allowed Actions

当前 MVP 可以：

- 经用户授权，只读读取并整理目标材料。
- 经用户授权，只读读取实际执行环境事实。
- 接收 Environment Snapshot 或 Manual Input。
- 发现并组织 Paper / Repository / README / Config / Issue 等关联材料。
- 定位、摘要并展示 Evidence 与来源冲突。
- 草拟 Finding / Unknown。
- 按冻结 Rule 形成 RD-01 / RD-02 / RD-03 的业务 Status。
- 形成 Resource Constraint Signal 与 Evaluation Conflict Signal。
- 输出阶段性 Overall Gate。
- 生成排序后的 Next Action。
- 接收用户对 Finding / Evidence 的确认、质疑、纠正或补充。

允许“读取环境事实”不等于允许“修改环境”。

例如：

```text
读取 Python / CUDA / Driver / GPU / VRAM / Disk 事实
→ Allowed

安装依赖 / 升级 CUDA / 修改 Driver / 改写项目文件
→ Not Allowed
```

---

## 5. Prohibited Actions

当前 MVP 不提供：

- 申请访问权限。
- 绕过访问权限。
- 下载受限数据。
- 代替用户接受 License / Terms。
- 安装或卸载依赖。
- 修改 Python / Framework / CUDA / Driver 或其他执行环境。
- 写入项目 / 环境文件。
- 删除或覆盖关键文件。
- 通过文件写入或环境修改实施自动修复。
- 自动执行完整复现。
- 自动执行高成本训练。
- 将 Overall Gate 或 Next Action 解释为系统自动执行授权。

以上均属于当前 V1 明确边界，不因 Figma 页面完整性或 Agent 能力展示而升级为 P0。

---

## 6. Confirmation & Authorization Rules

### 6.1 Target / Source Confirmation

当 Paper / Repository / Project 或关键 Material 存在真实映射歧义时，系统应显式请求用户确认，而不是静默选择候选对象。

Target / Source Confirmation 只回答：

> 当前分析对象是否正确？

确认对象正确本身不会改变任何 Readiness Status，也不会产生系统读取授权。

### 6.2 Read-only Authorization

读取用户实际执行环境或其他需要授权的资源前，必须取得用户授权。

当前 MVP：

```text
access_mode = Read-only
```

Authorization 只回答：

> 系统是否被允许读取指定范围？

当前授权状态与业务 Readiness Status 分离。

### 6.3 Environment Input Fallback

当 Read-only Detection 未授权、失败或不可用时，可以使用：

- `Snapshot`
- `Manual Input`

这些是替代输入方式，不代表系统获得额外执行权限。

因此：

```text
Read-only Detection unavailable
        ↓
Snapshot / Manual Input
        ↓
继续补充事实
```

而不是：

```text
Read-only Detection unavailable
        ↓
获得写入 / 执行权限
```

### 6.4 Data Access Permission 与 System Authorization 分离

ResearchOps 可以记录和评估：

- 数据集访问权限是否已取得；
- checkpoint 是否可获得；
- 其他可能影响 RD-01 / RD-03 的访问事实。

这些属于 Readiness Evidence / User Context。

但 ResearchOps 不得：

- 代替用户申请权限；
- 代替用户接受访问条款；
- 绕过权限；
- 下载受限数据。

因此：

> “用户是否拥有数据访问权限”是可被评估的业务条件；“ResearchOps 是否被允许读取某个系统 / 环境”是系统 Authorization。二者不得混淆。

---

## 7. Failure / Unknown Handling

安全状态、权限状态或技术获取状态不得直接改写为业务 Readiness Status。

### 7.1 Authorization Denied

```text
Authorization = Denied
```

不等于：

```text
RD-02 = Blocked
```

正确路径：

```text
Authorization Denied
        ↓
自动读取不可用
        ↓
Snapshot / Manual Input
        ↓
若 Gate-critical 事实仍不足
        ↓
相关业务判断进入 Unknown
```

“系统不能读取”与“用户环境不满足复现条件”是两件不同的事。

### 7.2 Acquisition Failure

SSH、API、自动环境检测等技术获取失败首先属于：

```text
Acquisition Failure
```

而不是：

```text
Warning / Blocked / PAUSE
```

只有完成当前可用信息分析后，仍因真实业务依赖缺失而无法判断，才形成对应业务 `Unknown`。

### 7.3 Not Provided / Insufficient Information

`Not Provided` 与 `Insufficient Information` 均不自动等于 `Blocked`。

只有明确负向 Evidence 证明必要条件不满足时，才允许形成 Blocked。

Unknown 只在真实业务依赖存在、且当前证据确实不足或冲突时产生。

---

## 8. Overall Gate & Execution Boundary

Overall Gate 是：

```text
Rule-generated decision support
```

不是：

```text
AI command
```

也不是：

```text
execution permission
```

三种 Gate 的安全含义保持如下：

| Overall Gate | 当前含义 | 执行边界 |
|---|---|---|
| `PROCEED` | 当前 Evidence 支持继续投入下一阶段 | 不保证复现成功；不授权系统自动执行 |
| `CONDITIONAL PROCEED` | 无 confirmed Blocker，但仍存在关键 Warning / Unknown | 仅支持低成本、可逆核验或准备；关键 Unknown 解决前不进入高成本复现 |
| `PAUSE` | 当前路径存在需要优先解除的阻塞 | 不等于永久否决项目 |

Gate 尚未形成由 `gate_available = false` 表达，不增加第四种 Overall Gate。

### 8.1 Next Action 仍是建议

包括：

```text
Higher-cost Reproduction
```

在内的 Next Action 均属于行动建议。

即使满足进入高成本复现的条件，当前 MVP 也只能：

> 建议用户进入 Higher-cost Reproduction。

不能：

> 自动开始完整训练或完整复现。

最终是否继续投入、是否接受风险、是否执行高成本或不可逆操作，由用户决定。

---

## 9. Future Capability Boundary

若后续版本引入以下能力：

- 文件写入；
- 环境修改；
- 命令执行；
- 高成本训练；
- 删除 / 覆盖；
- 其他不可逆或高风险操作；

必须另行建立：

1. 分级权限；
2. 明确的 Human Confirmation；
3. 与动作风险相匹配的授权范围。

本 V1 不预设未来角色体系、审批工作流、回滚机制或企业级审计实现。

这些未来能力不得通过当前 Safety Boundary 的措辞被默认为已经存在。

---

## 10. Cross-document Audit

本文件冻结前完成以下交叉审计。

### 10.1 PRD V0.9

审计对象：

`20260826_PRD_V0.9.docx`

| Audit Item | Result |
|---|---|
| AI / Rule / Human 职责模型一致 | PASS |
| 当前 MVP 仅授权后只读访问 | PASS |
| 不提供写入 / 安装 / 环境修改 / 删除覆盖 / 训练执行 | PASS |
| 不申请 / 绕过权限，不代接受 License / Terms | PASS |
| Overall Gate 为决策支持，不是强制指令 | PASS |
| 最终高成本 / 不可逆投入由用户决定 | PASS |

### 10.2 Field Dictionary V1

审计对象：

`20260826_Field_Dictionary_V1.md`

| Audit Item | Result |
|---|---|
| Confirmation 与 Authorization 独立 | PASS |
| `AccessMode = Read-only` 边界未突破 | PASS |
| Read-only Detection / Snapshot / Manual Input 与本文件一致 | PASS |
| Unauthorized / Fetch Failed 不直接等于 Blocked | PASS |
| `CONDITIONAL PROCEED` 低成本、可逆边界一致 | PASS |
| `Higher-cost Reproduction` 仅作为 Next Action 类型保留 | PASS |

### 10.3 Output Schema V1

审计对象：

`20260826_Output_Schema_V1.json`

| Audit Item | Result |
|---|---|
| `interaction_state.confirmation` 与 `authorization` 分离 | PASS |
| `user_context.input_mode` / `acquisition_state` 可承接输入与获取状态 | PASS |
| `gate_available` 与 `gate_value` 分离 | PASS |
| Schema 未引入写入 / 训练 / execution permission 字段 | PASS |

### 10.4 Event Tracking Plan V1

审计对象：

`20260826_Event_Tracking_Plan_V1.md`

| Audit Item | Result |
|---|---|
| `input_mechanism_understood` 覆盖 Target Confirmation / 环境输入 / Read-only Authorization | PASS |
| `decision_recorded` 仅为 Concept Test 记录事件 | PASS |
| Event Plan 不要求新增“确认决策”按钮 | PASS |
| Event Plan 未引入训练、写入或环境修改执行事件 | PASS |

### 10.5 审计中完成的最终修正

交叉审计后对初稿做了以下收敛：

1. 将 `SB-02｜Read-only by default` 收紧为 `Authorized read-only only in current MVP`，避免“默认只读但可能存在当前例外”的误解。
2. 将 Human 的高风险 / 不可逆动作确认明确限定为“未来若引入该能力时”，避免与当前 MVP 不具备执行能力发生冲突。
3. 将禁止边界明确为“禁止文件写入；删除 / 覆盖关键文件”，完整继承 PRD 的写入禁区。
4. 明确 `decision_recorded` 与 Overall Gate 均不产生执行权限，保持与 Event Tracking / Output Schema 一致。

**Cross-document Audit Result：PASS**

未发现需要重开 Readiness Dimension、Status、Overall Gate、P0 / P1 / P2 或当前 MVP 权限边界的冲突。

---

## 11. 验收清单

- [x] AI / Rule / Human 职责与 PRD 一致。
- [x] 当前 MVP 明确限定为用户授权后的 Read-only。
- [x] Read-only 不存在当前版本的写入 / 执行例外。
- [x] Target / Source Confirmation 与 Authorization 已分离。
- [x] 数据访问条件与系统读取 Authorization 未混淆。
- [x] Unauthorized / Acquisition Failure 未被直接映射为 Blocked。
- [x] Snapshot / Manual Input 仅作为替代输入，不扩展执行权限。
- [x] Overall Gate 保持决策支持，不被解释为执行授权。
- [x] `gate_available = false` 未被扩展为第四种 Gate。
- [x] `CONDITIONAL PROCEED` 未突破低成本、可逆核验边界。
- [x] Higher-cost Reproduction 可被建议，但当前系统不执行。
- [x] Event Tracking 未创造当前 MVP 不存在的执行能力。
- [x] 当前 V1 未引入企业级权限治理与审批体系。
- [x] PRD + Field Dictionary + Output Schema + Event Tracking 交叉审计已通过。

---

## 12. 当前状态

**COMPLETED FOR SPRINT 2 DAY 4 — FROZEN FOR MVP CONCEPT DESIGN**

本文件已完成 PRD、Field Dictionary、Output Schema 与 Event Tracking 的交叉审计，可作为 D5 Figma Handoff 与 Concept Test 安全边界输入。

下游不得静默扩大系统权限，不得将 Readiness 判断、Overall Gate 或 Next Action 转化为当前 MVP 的自动执行授权。
