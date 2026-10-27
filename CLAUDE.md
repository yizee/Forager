# Forager：项目说明（交接给 Claude 工程模式）

> 本文件汇总了截至 2026-10-25 的所有设计结论，是继续开发的唯一依据。开始任何工作前请先完整读一遍。

## 1. 一句话说明

**问题**：想在多个快速变化的领域（AI 新闻、论文、开源工具）保持前沿的人，要么被信息淹没，要么信息流悄悄变窄，只剩最近感兴趣的方向。
**方案**：Forager 是一个个性化 agent，每天推送一份可追溯来源的简报，并让用户看得见、管得住它学到的偏好。
**三个设计贡献**：基于选项的兴趣澄清；经授权的长期和短期偏好记忆；保护信息广度的 Critic agent。

作者：SHI YIZE（01532875），SMU CS 619 Human-AI Interaction 课程项目。长期目标是把它整合进作者的个人网站 Yard，但这不在课程范围内。

## 2. 课程要求与时间

| 交付物 | 要求 | 截止 | 占比 |
| --- | --- | --- | --- |
| 提案 | 已提交，已收到反馈 | 已完成 | 5% |
| 演示视频 | 2 分钟，展示做好的应用 | **2026-11-03（Week 11 周二）** | 5% |
| 项目报告 | 最多 6 页，图表可放附录 | Week 11 结束 | 20% |
| 三个想法的合理性和创新性 | 也看实现质量或设计讨论深度 | | 60% |
| 评估质量 | | | 10% |

课程硬性要求：做一个面向用户的 LLM 应用，实现课程中的三个想法，至少一部分想法必须让用户看得见、能参与，并说明设计理由、做评估。老师明确说过，实现深度不是唯一标准：实现简单但设计讨论充分（UI 草图、流程图），也可以拿高分。

**时间非常紧**：距离视频截止只剩约 9 天。优先保证能演示的端到端流程，其次才是评估的完整度。没做完的部分用设计草图在报告和视频中说明。

## 3. 当前状态

- 提案已提交（`docs/proposal.pdf`），老师反馈见 `docs/feedback.md`。
- GitHub 仓库 `yizee/Forager` 已建立。本地克隆在 `~/Desktop/Forager`，虚拟环境 `.venv`（Python 3.11）。
- **第 1–3 阶段已完成**，离线测试共 40 个全部通过（`.venv/bin/python -m pytest`，只收集 `tests/`），2026-10-25 的真实调用也全部通过，花费 $0.0053。详情和给报告用的观察见 `docs/live-runs.md`。下一步：第 4 阶段。
- **第 4 阶段进行中。** 已完成：
  - 代码规则（`forager/checks.py` 的 `check_rules`）：话题占比 ≤ 40%（每个兴趣一个桶，所有广度补充合为一个桶，5 条以上才判断）、长期兴趣 7 天覆盖（可传入历史简报）、来源类型不单一（只有可用来源 ≥ 2 种时才生效）、引用 ID 存在。规则还没有接进简报流程。
  - Critic 用例集 `eval/cases/critic/`（21 个，由 `eval/build_critic_cases.py` 生成，不要手改 JSON）。每个用例都通过全部代码规则：16 个带一个语义问题，4 个对照（含 2 个困难反例），外加未经修改的第一份真实简报 `live-01`（4 个问题），共 20 个标注问题。标注由 Claude 写成，2026-10-26 经过两轮审计：Claude 逐条对照原文自审，另有一个独立审计员（只看用例和 Critic 的判断标准）。结论和改动见用例 README 的"Label audit"一节。**作者本人的核对仍待完成**。
  - **Critic 的输出格式由用例集决定**：`{"verdict": "PASS"|"ADJUST", "issues": [{"type": "irrelevant_exploration|near_duplicate|unsupported_citation|overstated_connection|mislabeled_interest", "refs": ["p30" | "points[2]" | "connections[0]"], "explanation": "..."}]}`。评分规则见 `eval/cases/critic/README.md`：点名问题位置算抓到（重复内容要点名至少两条），点名"可争议"位置不计分，其余点名算误报。
  - **Critic 已完成（离线测通，2026-10-26）**：`forager/critic.py`。Critic 是上下文独立的 agent，只看档案、带位置编号的速报和每条内容的原文（`source_text`），看不到任何标注答案。它的输出由代码检查（类型、位置、类型与对象是否匹配），格式不对可修改一次。
  - **简报流程三种模式**（也是想法 3 的三个对照条件）：`single`（只查结构和引用，即第 1 阶段基线）、`rules`（加代码规则，违规修改一次）、`critic`（再加 Critic；ADJUST 时写作 agent 修改一次，修改后重新跑规则；修改版违反规则就保留通过规则的草稿）。命令：`python -m forager digest --mode critic|rules|single`，默认 `critic`。目前写作 agent 还是第 1 阶段的单 agent，Manager 和来源专家接入后流程不变。
  - **覆盖规则是软规则**：修改一次后仍未覆盖的长期兴趣变成警告，显示在简报里，而不是判失败。只有 arXiv 时，有些兴趣（如版权政策）根本没有对应内容；硬性要求会逼写作 agent 乱贴标签，正是 Critic 要抓的问题。这一点写进报告。
  - 简报 Markdown 末尾有"How this digest was checked"，显示规则结果、未覆盖的兴趣和 Critic 的问题（想法 3 对用户可见的部分之一）。
  - **用例集评估脚本**：`eval/run_critic_cases.py`（每个用例用全新的 Critic 会话，可 `--repeats`，付费前先显示估算并确认）。评分与用例 README 一致，同时输出"仅规则"（按构造全部为 0）和"规则 + Critic"。分析脚本：`eval/analyze_critic_results.py`。
  - **用例集真实评估已完成（2026-10-27，21 × 3 = 63 次审查，$0.036）**，详见 `docs/critic-eval.md`：
    - 仅规则抓到 0/60，规则 + Critic 抓到 45/60（75%），类型全部正确，误报为 0（对照组 0/12）。
    - 构造用例 45/48（94%），真实简报 live-01 是 0/12。构造用例高估了真实场景的效果，这是报告里必须讲的局限。
    - 最弱的是兴趣标签错误（47%）：虚构的 Lumen-V 2 抓到 2/3，真实的 Sora 2 一次也没抓到。
    - 不要在看过结果后改标注（会抬高 Critic 的分数）；要改进 Critic，需用新的用例或新的真实简报来评估。
  - **GitHub 来源已完成（2026-10-27）**：`forager/sources/github.py`，按话题搜索近 7 天创建、星标最多的仓库，并附 README 摘录；快照 `data/snapshot/github-2026-10-27.json`。候选内容按来源交替排列（最多 24 条），来源类型不单一规则因此可以满足。Hugging Face 按计划不做。
  - **Streamlit 界面已完成（2026-10-27）**：`.venv/bin/streamlit run forager/app.py`，四个页面：简报、设置（想法 1）、记忆（想法 2）、话题（想法 3）。
    - 审批仍由 SDK 强制执行：记忆审查在后台线程里运行，SDK 在 `needs_approval` 处暂停，线程等页面上的"批准/拒绝"。每条建议有编号，重复点击不会误答下一条；10 分钟无回答视为拒绝。报告里可以强调这一点。
    - 运行数据路径集中在 `forager/storage.py`，可用 `FORAGER_RUNTIME_DIR` 指到别处（界面测试用临时目录）。
    - 界面测试用 Streamlit 的 AppTest 无头运行，配合脚本化模型，不花钱。
  - 下一步：三种模式各跑一次真实调用（约 $0.01），按第 8 节的"进度落后"方案完成第 4 阶段 → 第 5 阶段评估和录视频素材。可选：三个来源专家和 Manager、新闻来源、在新的真实简报上评估 Critic（先标注后运行）。
- `lab/` 是从 `~/Desktop/Human-AI/week5/week3-lab-ta` 复制来的（带 `.env`）。本地账本 `lab/.lab-state` 从 2026-10-25 开始记，起点 $0；之前 week4 和 week6 的账本里另有约 $0.025 的花费。
- `runtime/profile.json` 目前是用典型用户人设生成的演示档案（含审批通过的"3D generation"）。用户可以随时用 `python -m forager onboard` 重做。
- 真实调用发现的关键问题（第 4 阶段要用）：简报通过了所有代码检查，但有错误的"兴趣匹配"标签（两条被标成 Sora 2 的内容其实与 Sora 2 无关）和夸大的跨领域关联；而且错误标签会随用户打分传进偏好记忆，导致 agent 提出基于错误归因的建议。这正是 Critic 要解决、规则解决不了的问题。
- 第 2 阶段（`python -m forager onboard`，基线 `--baseline`）：
  - 档案由代码根据用户的选择生成（`build_profile`），模型给出的选项之外的内容一律忽略，保证"不凭空添加偏好"。
  - 用户接受的相邻领域权重 0.5；用户选中的短期关注 14 天后过期；新档案的所有追踪授权默认关闭。
  - 终端里用编号代替可点选的选项；Streamlit 界面在第 4 阶段复用 `onboarding.py`。
  - 综合查询的澄清（时间范围、时间线还是对比）暂未实现，放到第 4 阶段做界面时再做。
- 第 3 阶段（`consent` / `rate` / `like` / `review` / `profile` 命令）设计要点：
  - 授权三层保证：未授权的信号不记录；使用时按当前授权过滤（只看最近 30 天）；撤回授权时删除该类已收集的数据。新档案和默认档案的授权全部关闭。
  - 写入工具 `propose_profile_update` 用 `needs_approval=True`，由 SDK 暂停等待用户决定。审批前代码先检查：至少 2 条不同的已授权信号作为证据、目标合法、30 天内被拒绝过的修改不再提出、每次最多 3 条建议。不合格的建议直接拦截，不打扰用户，原因通过 `rejection_message` 告诉模型。工具本身写入前再检查一次。
  - 用户看到的"改动内容"和"证据"由代码根据参数和信号记录生成，和 agent 的措辞分开显示，防止措辞误导。
  - 所有建议和结果记录在 `runtime/proposals.jsonl`，用于想法 2 的评估。静默更新基线：`review --silent-baseline`。
  - 短期兴趣过期后不再用于简报（自动降权），在 `review` 时请用户选择：延长 14 天、转为长期或删除。
- 所有"JSON 回复 + 代码检查 + 修改一次"的 agent 都用 `forager/jsonagent.py`。
- Lab 代码由 `forager/labkit.py` 定位：默认 `lab/`（也接受 `lab/week3-lab-ta/`），可用环境变量 `FORAGER_LAB_DIR` 覆盖。
- 候选内容超过 `session.run` 的 6000 字符上限，所以通过 `input_builder` 作为上下文消息传入，用户消息只放简短指令。
- 用户本机已有 Week 6 包：`~/Desktop/Human-AI/week6/week6/evaluation/`（含 `run_eval.py`、`harness.py`、`graders.py`），第 5 阶段使用。

## 4. 产品功能

### 内容来源（三类）

| 类型 | 来源 | 获取方式 |
| --- | --- | --- |
| 新闻 | 科技新闻 | RSS 或新闻 API |
| 论文 | arXiv（cs.AI、cs.CL、cs.CV 等）；AI 厂商研究博客（OpenAI、Anthropic、Google DeepMind、Meta） | arXiv API；博客 RSS |
| 开源 | GitHub 近期热门仓库；Hugging Face 热门模型 | GitHub 搜索 API（近期创建、按星标排序）；Hugging Face API |

时间不够时，**最先砍掉 Hugging Face**。不加入其他来源类型。求职信息已明确从项目中删除。

### 每日简报（两层，互相连通）

1. **信息速报**：5–8 条按领域分组的要点，一栏"跨领域关联"，一栏"与上次相比的新进展"。**每条要点必须引用至少一个内容 ID**，点击可跳转到对应的完整内容。
2. **完整内容**：每条内容有摘要、原文链接，以及推荐理由标签：`兴趣匹配：<哪条偏好>` 或 `广度补充：<原因>`。

### 其他功能（辅助功能，做到能用即可，不算三个想法）
- 用户设定每日推送时间。
- 综合查询，例如"本周图像生成 × 视频剪辑"。
- 对内容打分（1–5）和点赞。
- 每周话题分布视图和"探索度"滑块（属于想法 3 的界面部分）。

### 典型用户（演示和报告都用这个人物）
一位关注 AI agent、视频剪辑和图像生成的 AI 学生。阶段性兴趣的例子：某个新模型（如 Sora）发布后的一段集中关注。

## 5. 三个设计想法

### 想法 1：基于澄清的兴趣收集（Week 1，意图表达）
- 用户用一句话粗略描述自己，agent 把它拆成几个方向，对每个方向用**可点选的选项**追问细节（不是让用户继续打字），并主动推荐相关领域（如"AI 版权政策"），最后生成一份可编辑的兴趣档案让用户确认。
- 综合查询也用同样方式澄清：时间范围？按时间线还是并排对比？
- 设计理由：人识别自己想要什么，比凭空回忆容易。
- 对照基线：自由文本兴趣描述。

### 想法 2：经授权、附带证据的偏好记忆（Week 4，记忆）
- **追踪授权**：开始前列出可收集的信号（打分、点赞、点击、阅读时长），用户逐项选择是否允许。未授权的信号绝不能被使用。
- **可见档案**：每条偏好标明来源（`stated` 用户说的 / `inferred` 推断的）和类型（`long_term` 长期 / `short_term` 短期，带过期时间）。
- **不静默更新**：agent 只能附带证据提出修改建议，例如"你给三条 Sora 相关内容都打了 5 分，要把视频生成加为重点关注吗？"，用户批准后才写入。
- **实现要求**：写入偏好的工具用 `@function_tool(needs_approval=True)`，由 SDK 强制执行审批（即 Lab 2 的 TODO 1），不能只靠指令里写"先问用户"。报告里要强调这一点。
- 短期兴趣到期后自动降权，或提醒用户确认。
- 对照基线：静默自动更新。

### 想法 3：来源专家 + 规则 + Critic（Week 6，多 agent；同时涉及 Week 2 验证输出）
- **Manager** 用 `as_tool()` 把聚焦的问题委派给三个来源专家，每个专家有自己的工具和指令：
  - 新闻研究员：关注事件和行业动态
  - 论文研究员：提炼论文的核心贡献
  - 开源研究员：说明项目能做什么、热度增长多快
- Manager 合并成简报草稿后，**每份简报都由 Python 代码固定执行检查**（不交给模型决定是否检查）：
  - **规则（代码）**：单个话题占比 ≤ 40%；每个长期兴趣 7 天内至少出现一次；来源类型不单一；每条速报要点引用的 ID 真实存在。
  - **Critic（agent）**：只做规则做不到的语义判断：探索内容是否真的和用户相关；标签不同但实际重复的内容（如 5 条都在讲同一次模型发布）；被引用的内容是否真的支撑要点，跨领域关联有没有夸大。
  - Critic 输出 `PASS` 或 `ADJUST` 加理由；`ADJUST` 时 Manager 修改一次。
- 用户能看到：推荐理由标签、每周话题分布、探索度滑块。
- 设计比喻（报告和视频用）：**轮作（crop rotation）**。农田长期单一种植会变贫瘠，Critic 就是在给信息流"轮作"。
- 设计理由：以相关性为目标的推荐器会越推越窄；一个目标不同、上下文独立的 agent 能抵消这种倾向。
- 对照基线：单 agent；仅规则（无 Critic）。
- **老师的核心疑问**：Critic 是否比简单规则更有价值。这是想法 3 的核心研究问题，评估必须正面回答。如果结果显示 Critic 没有明显优势，也要如实报告。

与课程示例（偏好记忆 + 征求同意）的区别：Forager 关注偏好如何影响用户看到的内容，包括会过期的短期兴趣、广度保护和可追溯的速报。

## 6. 技术基础与约束

### 基础代码：Lab 2 代码包（week3-lab-ta）
- 用户手里有 `lab2.zip`（包含 `week3-lab-ta/`）。这是老师说的"更新后的 Lab 1 代码"，自带 `EXTENDING.md`。**先读 `EXTENDING.md`**。旧的 Lab 1 包（`lab-student-package`）不再使用。
- 调用模型统一用 `lab_support.open_lab()` 和 `lab.session(agent_factory=..., on_event=...)`，`session.run()` 返回 `status / answer / artifacts / error / events`。
- 多 agent 参考 `project_examples.py` 的 `workflow_example`；评估参考 `evaluation_example`（每个任务都用全新的文件和对话）。
- `project_examples.py` 可以离线运行（脚本化的模型回复，不需要 key、不联网）。**新功能先用离线方式测通，再做付费调用。**
- 依赖版本固定：`openai-agents==0.22.2`、`openai==3.14.1`、`httpx2==2.13.0`，Python ≥ 3.10。

### 模型与预算（硬约束）
- 通过 OpenRouter 调用 `z-ai/glm-5.3-flash`，代码锁定此模型，换模型会报错。key 由老师发放。
- `.env` 里只有 `OPENROUTER_API_KEY` 和 `OPENROUTER_MODEL`。**`.env` 绝不能提交到 Git，也不要让用户把 key 发到对话里。**
- 每个 key 本地记账，**预算上限 1 美元**，网页搜索最多 20 次。同一连接上的调用按顺序执行，不能并行。
- **禁止删除或重置 `.lab-state/`**，Lab 说明明确禁止。
- 1 美元在评估阶段可能不够。待确认：老师是否给项目额外额度；否则用户可用自己的 OpenRouter key 调用同一模型。批量评估前先估算调用量并告知用户。

### 运行环境
- 云端会话访问不了 arXiv、GitHub 搜索 API、Hugging Face 和 OpenRouter。**代码必须在用户自己的电脑上运行和测试**（Claude 桌面应用连接本地文件夹，或用户自己运行）。
- 界面：Streamlit 或 Gradio，二选一，倾向 Streamlit。用 `on_event` 回调显示工具调用过程。

### 建议的目录结构

```
Forager/
  CLAUDE.md            本文件
  README.md            对外的项目说明和路线图
  CHANGELOG.md         更新日志
  docs/                提案、反馈、设计笔记、UI 草图
  lab/                 Lab 2 代码包（仓库为 Public 期间加入 .gitignore，不得推送）
  forager/             项目代码：sources/、agents/、profile.py、checks.py、app.py
  data/snapshot/       评估用的固定内容快照（新闻 + 论文 + 开源项目）
  eval/                测试用例和评估脚本
  runtime/             运行时数据（profile.json、digest 记录），加入 .gitignore
```

### 数据结构草案（可调整，改动要写进 CHANGELOG）

```json
// runtime/profile.json
{
  "interests": [
    {"id": "i1", "label": "image generation", "facets": ["new models", "copyright"],
     "type": "long_term", "source": "stated", "weight": 1.0, "expires": null},
    {"id": "i2", "label": "Sora", "type": "short_term", "source": "inferred",
     "weight": 0.8, "expires": "2026-11-10",
     "evidence": ["rated item n12 5/5", "rated item p03 5/5"]}
  ],
  "consent": {"ratings": true, "likes": true, "clicks": false, "reading_time": false},
  "exploration": 0.2,
  "delivery_time": "08:00",
  "setup": {"method": "clarification|free_text", "description": "...", "date": "2026-10-25"}
}
// 每条 interest 另有 "origin": "clarification|suggested|free_text|manual|proposal"（第 2、3 阶段加入）
// 第 3 阶段：经建议写入的 interest 还有 "evidence"（从信号记录复制）和 "approved_on" 或 "updated_silently_on"

// runtime/signals.jsonl 中的一条信号（只在授权时记录）
{"id": "s1a2b3c", "time": "2026-10-25T09:00:00", "signal": "ratings|likes|clicks|reading_time",
 "value": 5, "digest": "2026-10-25",
 "item": {"id": "p03", "type": "paper", "title": "...", "topics": [], "reason_kind": "interest", "interest_id": "i2"}}

// runtime/proposals.jsonl 中的一条记录
{"time": "...", "mode": "approval|silent|expiry", "decision": "approved|rejected|blocked|silent|approved_not_applied|kept|made_long_term|removed",
 "applied": true, "change": "<代码生成的改动描述>", "message": "<agent 的话>", "evidence_ids": ["s1a2b3c"],
 "evidence": ["rated p03 ... 5/5 ..."], "errors": [], "proposal": {...}}

// 一条内容
{"id": "p03", "type": "paper|news|repo", "title": "...", "url": "...",
 "summary": "...", "topics": ["image generation"], "published": "2026-10-20",
 "reason": {"kind": "interest|breadth", "interest_id": "i1", "text": "..."}}

// 一条速报要点
{"text": "...", "field": "image generation", "cites": ["p03", "n12"]}
```

## 7. 评估计划（按老师反馈精简为 4 个核心指标）

| 想法 | 核心指标 | 方法 |
| --- | --- | --- |
| 1 | 兴趣档案准确度（用户 1–7 分自评），对比自由文本基线 | 用户研究 |
| 2 | 偏好更新是否附证据并等待批准的通过率（数据来自 `runtime/proposals.jsonl`；对照 `review --silent-baseline`） | LLM 判定的测试用例 |
| 3 | 话题多样性与相关性的权衡，对比单 agent / 仅规则 / 规则 + Critic | 代码统计 + LLM 判定相关性 |
| 3 | 速报要点的引用支撑率 | LLM 判定的测试用例 |

- 所有自动化测试使用 `data/snapshot/` 里的**固定快照**，保证结果可复现，不用实时数据。
- **必须设计规则一定会失败的用例**，来检验 Critic 的价值：不相关的探索内容、标签不同但实际重复的内容、引用存在但并不支撑要点。真实快照里不一定恰好有这些情况，所以要人工构造，并在第 4 阶段开头就做好，开发 Critic 时直接用来测试。
- 报告要说明想法 3 相对提案的变化：提案中广度检查（话题占比、7 天覆盖）也由 Critic 做，现在改为代码规则，Critic 只做语义判断。这是对老师反馈的直接回应。
- LLM 判定要用一小批人工标注的样本校准，报告里写明这一步。
- Think-aloud 用户研究（2–3 人）作为补充的质性证据，任务包括：从零设置兴趣档案、审阅一条偏好更新建议、找出某条内容为什么出现并修正一条不想要的推荐。记录时把观察和解读分开。
- Week 6 的评估框架（`run_eval.py`）还没有拿到；拿到前用 `project_examples.py` 的 `evaluation_example` 模式自己写评估脚本。

## 8. 分阶段路线图

每个阶段都要先做出能端到端运行的版本，再开始下一阶段。完成后在 README 的路线图里打勾。

| 阶段 | 内容 | 完成标准 | 建议完成日 |
| --- | --- | --- | --- |
| 1 | 最小可用版本：只接 arXiv，单 agent 生成两层简报 | 离线测试通过；一次真实调用生成的简报中，每条速报要点都有有效引用 | 10-27 |
| 2 | 想法 1：澄清式兴趣设置 + `profile.json` | 一句话描述 → 选项追问 → 用户确认后保存档案 | 10-28 |
| 3 | 想法 2：打分、追踪授权、附证据的更新建议（`needs_approval=True`） | 拒绝时档案不变，批准时写入；未授权信号不被使用 | 10-29 |
| 4 | 想法 3：**先人工构造"规则必然失败"的用例集**（`eval/cases/`：不相关的探索内容、标签不同但实际重复的内容、引用存在但不支撑要点），再加入 GitHub 和新闻来源、三个来源专家、规则检查 + Critic；Streamlit 界面 | 用例集就绪并用于开发 Critic；三个版本（单 agent / 仅规则 / 规则 + Critic）都能跑通 | 10-31 |
| 5 | 评估和录视频素材 | 4 个核心指标有结果；录好演示 | 11-02 |

如果进度落后：第 4 阶段先只加 GitHub 来源；界面可以简化；没实现的部分用草图在报告和视频中说明。

## 9. 视频结构（2 分钟，用典型用户串起来）

| 时间 | 内容 |
| --- | --- |
| 0:00–0:15 | 问题：信息碎片化，信息流越推越窄 |
| 0:15–0:45 | 想法 1：一句话描述 → 选项追问 → 兴趣档案 |
| 0:45–1:10 | 两层简报：点击速报要点跳到原文；推荐理由标签 |
| 1:10–1:30 | 想法 2：打分后 agent 附证据提出更新，用户批准 |
| 1:30–1:50 | 想法 3：广度补充标签、话题分布、探索度滑块 |
| 1:50–2:00 | 一个关键评估结果 |

## 10. 报告写作要求（来自老师反馈）

- **开头直接写问题和解决方案**，就像本文件第 1 节的三句话；动机压缩成一小段。
- 每个想法都要写清：是什么、为什么有帮助、怎么实现、和基线相比如何。
- 写一节设计变体讨论，可选话题：偏好更新是即时还是每日汇总；推荐理由的粒度；短期兴趣多久过期；事件时间线追踪（只做设计，不实现，配草图）。
- 广度与相关性的权衡结果放进"收获与心得"。

## 11. 工作规范

- **每次更新都要提交并推送到 GitHub**（`yizee/Forager`，分支 `main`），并在 `CHANGELOG.md` **最上面**加一条记录，按日期分为 `Added` / `Changed` / `Fixed` / `Removed`。
- 提交信息用英文，简洁说明做了什么。
- 绝不提交：`.env`、`.lab-state/`、`runtime/`、API key；仓库为 Public 期间，也不提交 `lab/` 里老师的代码。
- 代码、注释和仓库文档用英文；和用户沟通用中文。
- 新功能先离线测试，再做付费调用；批量付费调用（尤其是评估）前先告诉用户预计花费。
- 修改了数据结构或设计决定时，同步更新本文件和 README。

## 12. 待确认事项

1. **仓库可见性**：`yizee/Forager` 目前是 Public。推送 Lab 代码前必须改成 Private（Settings → Danger Zone → Change visibility）。
2. **额外预算**：是否向老师申请项目额度，或改用用户自己的 OpenRouter key。
3. **Week 6 评估框架**：已在本机找到 `~/Desktop/Human-AI/week6/week6/evaluation/`。注意 Week 6 包里的 `lab_support` 比 Lab 2 新（多了 `_session_lock.py`，少了 `_runtime.py`），第 5 阶段前确认用哪一版。
4. ~~Lab 2 代码包~~：已解决，`lab/` 已就位（见第 3 节）。

## 13. 相关文件

- `docs/proposal.pdf`：已提交的提案
- `docs/feedback.md`：老师反馈和对应的调整方案
- `README.md`：对外的项目说明和路线图
- `CHANGELOG.md`：更新日志
