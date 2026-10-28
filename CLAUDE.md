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
- **第 4 阶段已完成（2026-10-27）**，离线测试共 117 个全部通过。内容：
  - 代码规则（`forager/checks.py` 的 `check_rules`）：话题占比 ≤ 40%（每个兴趣一个桶，所有广度补充合为一个桶，5 条以上才判断）、长期兴趣 7 天覆盖（可传入历史简报）、来源类型不单一（只有可用来源 ≥ 2 种时才生效）、引用 ID 存在。规则已接进简报流程（见下面的三种模式）。
  - Critic 用例集 `eval/cases/critic/`（21 个，由 `eval/build_critic_cases.py` 生成，不要手改 JSON）。每个用例都通过全部代码规则：16 个带一个语义问题，4 个对照（含 2 个困难反例），外加未经修改的第一份真实简报 `live-01`（4 个问题），共 20 个标注问题。标注由 Claude 写成，2026-10-26 经过两轮审计：Claude 逐条对照原文自审，另有一个独立审计员（只看用例和 Critic 的判断标准）。结论和改动见用例 README 的"Label audit"一节。**作者本人的核对仍待完成**。
  - **Critic 的输出格式由用例集决定**：`{"verdict": "PASS"|"ADJUST", "issues": [{"type": "irrelevant_exploration|near_duplicate|unsupported_citation|overstated_connection|mislabeled_interest", "refs": ["p30" | "points[2]" | "connections[0]"], "explanation": "..."}]}`。评分规则见 `eval/cases/critic/README.md`：点名问题位置算抓到（重复内容要点名至少两条），点名"可争议"位置不计分，其余点名算误报。
  - **Critic 已完成（离线测通，2026-10-26）**：`forager/critic.py`。Critic 是上下文独立的 agent，只看档案、带位置编号的速报和每条内容的原文（`source_text`），看不到任何标注答案。它的输出由代码检查（类型、位置、类型与对象是否匹配），格式不对可修改一次。
  - **简报流程三种模式**（也是想法 3 的三个对照条件）：`single`（只查结构和引用，即第 1 阶段基线）、`rules`（加代码规则，违规修改一次）、`critic`（再加 Critic；ADJUST 时写作 agent 修改一次，修改后重新跑规则；修改版违反规则就保留通过规则的草稿）。命令：`python -m forager digest --mode critic|rules|single`，默认 `critic`。`rules` 和 `critic` 由 Manager 和来源专家写作，`single` 保留第 1 阶段的单 agent（基线）；可用 `--writer team|single` 覆盖。
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
  - **Manager 和三个来源专家已完成（2026-10-27，按原设计）**：`forager/team.py`。
    - Manager 只看候选内容的索引（ID、类型、标题），看不到原文；它用 `as_tool()` 向论文研究员、开源研究员、新闻研究员提出聚焦的问题。每个专家有自己的指令和一个只返回本来源候选内容的工具（开源研究员的工具在代码里算好"每天多少星"）。专家沿用 lab 的模型设置，记在同一个账本里。
    - 代码检查 Manager 的每次回答（违规修改一次）：有候选内容的专家都问过；简报里每条内容都由对应专家报告过；只有读过原文的专家点名了某个兴趣，这条内容才能标成"兴趣匹配"（Manager 没读原文，不能自己加匹配）。这条规则直接针对第一次真实简报里为了覆盖兴趣而乱贴 Sora 2 标签的问题，报告里可以讲。标题也是兴趣声明：要点放在某个兴趣的标题下时，必须引用匹配该兴趣的条目（`check_headings`），否则同样修改一次。
    - 专家的回答也由代码检查：这次运行里没调用自己的工具就作废；只保留本来源的 ID；档案里没有的兴趣改为广度补充。
    - 新闻来源 `forager/sources/news.py`：TechCrunch、The Verge、MIT Technology Review、Ars Technica、The Decoder 的 RSS/Atom，近 3 天，按媒体轮流取最多 15 条；原文最多 800 字符（快照公开提交）。快照 `data/snapshot/news-2026-10-27.json`。
    - 三种模式对比脚本 `eval/run_digest_modes.py`：同一组快照和档案，每次运行都是全新会话，代码统计来源和话题分布、最大话题占比、广度占比、未覆盖兴趣、引用、Critic 结论、请求数、花费和耗时；兴趣标题检查也对每种模式统计（`heading_problems`）；critic 模式另存 Critic 审查的草稿（`reviewed_draft`），报告列出修改改了什么；`--save critic` 同时存为当天的简报。第 5 阶段想法 3 的"多样性与相关性"指标可以直接用它（再加 LLM 判定相关性）。
  - **三种模式的真实调用已完成（2026-10-27，$0.0177）**，详见 `docs/live-runs.md` 第二节和 `eval/results/digest-modes-20261027-113548.*`。arXiv API 当天连续 5 次返回 429，所以论文用的是 10-25 的快照（GitHub、新闻是 10-27 的）。
    - 三种模式都生成了简报，每条要点的引用都有效。团队版本 9–10 次请求、约 30 秒，单 agent 1 次、约 9 秒，花费约 3.5 倍。
    - Manager 第一次回答就同时问了三个专家；每个专家都调用了自己的工具，只读了本来源的 8 条。
    - Critic 抓到一个来自论文研究员的错误标签（视频世界模型综述被标成"视频剪辑"），Manager 修改后改为广度补充；仅规则模式下这个标签留在简报里。这说明分层的必要：代码保证标签来自读过原文的 agent，只有语义检查能判断它对不对。
    - 两个团队版本都把一个与 Sora 无关的视频生成仓库标成"Sora 2"，Critic 没抓到，和用例集评估里 Sora 2 一次都没抓到一致。单 agent 反而把这两条都标成了广度补充。可能原因：每个专家只看自己那一部分，又被要求"先报兴趣匹配"。已改专家指令（只有内容本身就是该兴趣才算匹配，可以不报匹配）。
    - Critic 版本里 Manager 按来源（papers/repos/news）而不是按领域分组；已改 Manager 指令。这两处指令修改的重跑结果见下面两条。
    - 单 agent 版本不执行规则，但事后用代码测量：7 天内"AI 版权政策"未覆盖（它把 SpectralCanary 标成图像生成，团队标成版权政策）。对比脚本现在对每种模式都用代码测量规则。
    - 修复次数的原因这次没有记录；现在每次写作尝试的检查结果都保存在 `check_log` 里。
  - **重跑验证（2026-10-27 下午，$0.0150，两次都没生成简报）**，详见 `docs/live-runs.md` 第三节：
    - rules 和 critic 各一次，Manager 的最终回答都达到 lab 每次回答 4096 token 的上限（含推理）。推理用了 2045 和 2930 token，上午只有 565–680。
    - 专家笔记照常记录。上午的两个错误标签（r08 标成 Sora 2、p03 标成视频剪辑）两次都改成了广度补充。critic 那次新出现两个边缘标签：n05、p02 被标成 AI agents，rules 那次都是广度补充。这是 Claude 的判断，作者还没核对。按领域分组还没验证。
    - **已修改（尚未真实运行验证）**：Manager 只给条目 ID，可以把兴趣匹配改成广度补充，不能反过来；每条内容的摘要、话题和标签由代码从读过原文的专家笔记里复制（`Team.fill`），回答约短 60%。
    - Manager 指令加了"推理要短"，并说明分组用的领域名：兴趣标签，否则用简短的领域名。
    - Manager 的回答丢失（如被截断）且所有专家都已回答时，在无工具会话里用笔记重写一次：只多 1 次请求，不重新问专家；记为 `rewritten`，并写进 `check_log`。
    - 单 agent 的指令一字未改。
    - 报告可用：输出上限是 Manager 设计的真实约束；改成"每个 agent 只写自己读过的内容"，既省 token，又少了一次转述失真。
  - **第二次重跑（2026-10-27 晚，$0.0161，两次都生成了简报）**，详见 `docs/live-runs.md` 第四节和 `eval/results/digest-modes-20261027-184748.*`：
    - Manager 只给 ID 后，最终回答（不含推理）是 925 和 945 token，上午是 1708–2051；加上推理共 2204 和 1280 token，离 4096 上限还远，没有截断，也不需要重写。
    - 两次都按领域分组（AI agents、3D generation、Video generation 等），上午 critic 是按来源分组。分组修改已验证。
    - 每条内容的摘要和话题都来自专家笔记。Manager 每次仍给 3 条广度补充写了自己的理由（类型没变，是转述笔记）；代码允许，指令没要求。
    - 标签（Claude 的判断，作者还没核对）：r08 在 rules 是广度补充，在 critic 又被开源研究员标成 Sora 2，Critic 仍没抓到。指令修改后 4 次运行里出现 1 次；真实简报里 Critic 对这个标签是 0/2，用例集里 Sora 2 也从没抓到。p03 两次都是广度补充。p05（文生图数据集使用审计）rules 标成版权政策、critic 是广度补充，两种都说得通。p04（推理模型的测试时剪枝）在 rules 被标成 AI agents，比较牵强。
    - 新发现：标题和标签可能矛盾。critic 简报里 SpectralCanary 那条要点放在"AI copyright policy"标题下，条目却是广度补充，底部还写着版权政策 7 天未覆盖；n06（广度补充）放在"AI agents"标题下。标题由 Manager 定，标签由专家定，代码没有把两者绑在一起。另外，话题占比规则按条目算（AI agents 4/10，正好 40%），但速报要点里 AI agents 占一半。
    - Critic 抓到 n01 的引用问题（原文没有"meeting-aware"），修改后删掉了，但最终要点仍有原文没说的推断。运行脚本只保存最终简报，所以不知道这句推断是不是修改时加的。
    - 没有专家把任何条目匹配到版权政策时，覆盖修复不可能成功，白花一次请求（critic 的修改阶段就是这样）。
  - **两处离线改动（2026-10-27 晚，离线测通，尚未真实运行）**：
    - 兴趣标题检查 `check_headings`（`forager/checks.py`）：要点的领域名等于某个兴趣的标签时，必须引用匹配该兴趣的条目，否则 Manager 修改一次。它属于 `Team.check`，只管团队写作；单 agent 只统计、不强制。Manager 指令同步改为"只有引用了匹配该兴趣的条目，才用兴趣名做标题"，单 agent 指令一字未改。
    - 它不在 `check_rules` 里，所以 Critic 用例集"每个用例都通过全部代码规则"的前提不变。放到 live-01 上会在 points[4] 触发：Video editing 标题下是被标成 Sora 2 的 WorldForge V2。
    - `generate_digest` 返回 Critic 审查的草稿 `reviewed_draft`；对比脚本保存它，报告列出修改改了什么（删掉或新增的条目、改了的标签、被改写或删掉的速报原文）。
- **第 5 阶段离线准备已完成（2026-10-27 晚）**，离线测试共 127 个全部通过，没有做付费调用。计划 `docs/stage5-eval-plan.md` 已按实际脚本更新（预计花费约 $0.50，待作者批准），末尾的 Runbook 列出每一步的命令。
  - 想法 3：两组快照上三种模式共 30 份简报，代码统计多样性，LLM 判定标签是否正确、条目是否值得看、要点是否有引用支撑；判定先用作者标注的 30 条内容和 30 条要点校准。可选：作者先标注 3 份 rules 简报，再让 Critic 审查（还没准备，需要一个把作者标注转成用例文件的小脚本）。想法 2：8 个场景比较审批和静默更新。想法 1 和 think-aloud：2–3 人的用户研究。
  - `eval/judge_runs.py`：三个 LLM 判定，沿用 Week 6 的判定方式（每条标准给出 true/false 和理由，格式不对修改一次，仍不对记为错误，不算通过）。条目：`label_correct`（只看兴趣匹配，兴趣的 facets 也算）、`worth_showing`；速报：`supported`、`not_overstated`（只看跨领域关联）；偏好建议：`evidence_supports_change`（按条目实际内容而不是标签判断，并参考用户的其他已授权信号）、`message_matches_change`。判定看不到模式、写作方式和"How this digest was checked"，条目按内容固定的顺序打乱；完全相同的输入只判一次（如 Critic 判 PASS 的草稿）。报告给出每种模式的均值和 bootstrap 95% 区间、critic − rules、rules − single 和修改前后的配对差。多样性（广度占比、最大话题占比、归一化熵、覆盖兴趣数、来源类型数）也由它计算。判定标准原文在 `CRITERIA`，标注表逐字复用。
  - `eval/calibration.py`：`make` 生成盲标注表（CSV 不含模式；README 列出用户兴趣和判定标准；`key.json` 记录每行来自哪次运行和模式，标完再看），按模式均分，条目约三分之一是广度补充，要点约 30% 是跨领域关联，相同内容只出现一次；`score` 输出一致率、Cohen's kappa、混淆表和不一致的行。偏好建议的标注表在记忆场景跑完后单独生成（`make --memory`）。已有的标注表不会被覆盖。
  - `eval/run_memory_cases.py`：8 个场景（强证据、弱证据、未授权信号、矛盾证据、错误标签、30 天内被拒绝、负面证据、短期兴趣过期），用 10-25、10-27 简报里的真实条目和快照原文，场景 1 和 5 重现 10-25 那次真实审查（3D generation 的证据是真的，Sora 2 的证据来自标错的条目）。过期场景用 Critic 用例集虚构的 Lumen-V 2，"今天"设为 11-12。审批模式下脚本化用户批准所有建议（对审批最不利），静默基线直接写入。代码统计建议数、展示数、写入数、未经批准写入数、被拦截数和原因、未授权信号是否进入上下文或被引用、是否重复被拒绝的修改。每条展示或写入的建议都保存给判定用的盲视图（不含模式和结果）。注意：拒绝记录只拦截完全相同的修改，换个标签名（如"3D asset generation"）就能绕过，场景 6 的报告会列出所有修改供人工检查。
  - 对比脚本的每条记录另存档案和快照文件名，判定不再依赖 `runtime/`。`python -m forager snapshot` 不再覆盖已有文件（加 `--overwrite` 才覆盖）。
  - 第二组快照：arXiv 已保存（`arxiv-2026-10-27.json`，30 篇，与第一组没有重复）。GitHub 和新闻如果当晚再抓，会和第一组大量重复（GitHub 13/15，新闻 7/15），而且同一天的文件名会覆盖第一组，所以留到 10-28 早上抓（免费）。GitHub 只取近 7 天，相邻几天本来就会大量重复。
  - 对比脚本加了花费上限 `--max-cost`：一批的花费达到上限后不再开始新的运行（默认是估算的 1.5 倍，即计划里的停止规则）。离线测试共 128 个。
  - **第一批中断（2026-10-28 上午）**：GitHub 和新闻快照已抓取并提交（S2 的 24 条候选里只有 4 条和 S1 重复）。S1 跑到第 2 次（rules）时，开源研究员的一次请求超过 lab 的 180 秒上限，lab 把它记为待定（`pending: true`），之后拒绝所有付费调用；其余 16 次没有花钱。只生成 1 份简报（single），不计入评估。总花费约 $0.0063，其中约 $0.0010 是那次超时的请求（按 OpenRouter 的 key 用量与三个本地账本之差推算）。没有动 `.lab-state/`：lab README 要求改账本前先问老师。详见 `docs/live-runs.md` 最后一节。
  - **改用作者自己的 key（2026-10-28）**：剩下的付费工作改用作者自己的 OpenRouter key。lab 副本在 `~/Desktop/Human-AI/forager-lab-own-key/`，放在仓库外，代码与 `lab/` 相同，有自己的 `.env` 和账本（从 $0 开始，本地上限同样是 $1）。所有付费命令前加 `FORAGER_LAB_DIR=~/Desktop/Human-AI/forager-lab-own-key`，预算检查在该目录里运行 `agent.py --check`。key 由作者自己填进该副本的 `.env`，不要发到对话里，也不要读这个文件。课程 key 的账本（`lab/.lab-state`）仍有一次请求待定，留给老师核对，不要动。离线测试在新副本上也全部通过（128 个）。
  - 下一步：作者填好 key 后先免费检查；作者同意后在新副本上完整重跑 S1，再跑 S2，然后生成标注表。新副本用的是同一份 lab 代码，请求超时同样会暂停付费调用；出现时停下来问作者，不要自己改账本。之后的付费工作分小批跑，每批之间检查账本。重复运行时顺便验证第 4 阶段最后两处改动（兴趣标题检查、`reviewed_draft`）。
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
- 用户本机已有 Week 6 包：`~/Desktop/Human-AI/week6/week6/evaluation/`（含 `run_eval.py`、`harness.py`、`graders.py`）。第 5 阶段沿用 `graders.py` 的判定方式，实现在 `eval/judge_runs.py`。

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
- 每个 key 本地记账，**预算上限 1 美元**，网页搜索最多 20 次。同一连接上的调用按顺序执行，不能并行。第 5 阶段剩下的付费调用改用作者自己的 key，在单独的 lab 副本里记账（见第 3 节）。
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
- 详细执行计划（判定标准、样本量、预算、日程）见 `docs/stage5-eval-plan.md`。
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
2. **额外预算**：已决定（2026-10-28）：改用作者自己的 OpenRouter key，在单独的 lab 副本里运行（见第 3 节）。课程 key 账本里那次待定的请求仍需老师核对。
3. **Week 6 评估框架**：已在本机找到 `~/Desktop/Human-AI/week6/week6/evaluation/`。注意 Week 6 包里的 `lab_support` 比 Lab 2 新（多了 `_session_lock.py`，少了 `_runtime.py`），第 5 阶段前确认用哪一版。已决定并实现：沿用 Week 6 的判定方式（每条标准给出是否通过和理由，格式不对算错误，总分由代码算），在 Forager 的 `eval/judge_runs.py` 里实现，用 Lab 2 的连接和同一个账本，不直接跑 Week 6 的 harness。
4. ~~Lab 2 代码包~~：已解决，`lab/` 已就位（见第 3 节）。

## 13. 相关文件

- `docs/proposal.pdf`：已提交的提案
- `docs/feedback.md`：老师反馈和对应的调整方案
- `README.md`：对外的项目说明和路线图
- `CHANGELOG.md`：更新日志
