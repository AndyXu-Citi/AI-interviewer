# AI 求职面试官 · 改造设计文档 v2

> 状态：设计稿 v2（待确认后进入实现）  
> 日期：2026-08-10  
> 目标：把 `AI-interviewer` 从「OpenAI Agents Starter 模板」升级成完整 AI 求职工作台：**求职 Agent + 岗位库 + 技能报表 + 简历匹配 + 严厉 AI 面试官**，并迁移 `ai_collector_project` 的 Boss 直聘爬虫能力。面试官要基于简历、项目、**具体 JD** 刨根问底。

---

## 1. 目标与定位（重新校准）

产品形态：**5 Tab 的 AI 求职工作台**

| Tab | 来源 | 核心能力 |
|---|---|---|
| **求职 Agent** | ai_collector_project v3.0 | 自然语言求职需求 → 意图解析 → 岗位检索/过滤/反思 → 推荐报告 |
| **岗位库** | ai_collector_project | 浏览已采集的 Boss 直聘岗位，按技能筛选，看 JD 详情 |
| **技能报表** | ai_collector_project | 市场技能热度、城市/薪资/经验/学历分布、对照个人画像的技能缺口 |
| **简历匹配** | ai_collector_project | 简历 vs 单条 JD / vs 全部岗位的匹配度分析与建议 |
| **AI 面试** | 本次新增 | 严厉技术面试官；支持基于简历、项目、知识点、**岗位库中任意 JD** 连续深挖 |

- **用户目标**：找 AI 应用开发方向工作，先用 Agent 找岗、看报表、做匹配，再用 AI 面试官针对目标 JD 或自己的项目被问到破防。
- **AI 面试官人设**：资深、严苛、刨根问底、抓矛盾、死咬最弱处；专业不侮辱。

### 边界
- 不真做简历投递。
- 爬虫只在本地运行（需 Chrome CDP），云端提供数据同步入口；云端核心使用已采集数据 + LLM 语义能力，不依赖本地 bge-m3/Milvus。

---

## 2. 素材来源（从 ai_collector_project 提炼）

| 素材文件 | 提炼为 | 用途 |
|---|---|---|
| `docs/INTERVIEW_GUIDE.md` (1097行) | 项目深挖追问链 | 针对 ai_collector 项目技术点的「标准回答 + 深度追问」 |
| `docs/JD_MAPPING.md` | 能力-弱点映射 | JD ↔ 项目能力映射、🟡/🔴 未掌握项 |
| `docs/qa_review.md` | 基础考察点 | 错题本、扣分点（如 vibe coding 自白） |
| `简历_Andy_AI应用开发工程师.md` | 简历深挖样例 | 简历模式默认材料 |
| `data/boss_*.json` / MySQL `final_results` | 岗位库数据源 | 岗位库、报表、匹配、JD 面试 |
| `src/sources/boss_zhipin.py` | 爬虫核心 | 本地 Boss 直聘采集能力迁移 |
| `src/web/app.py` / `static/index.html` | 4 Tab 功能与 UI | API 与交互逻辑参考 |

### 🔑 「破防点」弹药
1. **vibe coding 自白**：项目怎么搭的、底层是否真懂。
2. **数据量前后矛盾**：47 / 192 / 242 条——口径是什么。
3. **🟡 未掌握项**：多 Agent 协作、MCP 内容审查、DSP、Claude Code 等。
4. **简历 vs 实际**：「独立 0 到 1」vs vibe coding。
5. **JD 要求 vs 简历技能**：面试官可拿着岗位库某条 JD 逐条逼问「这条要求你满足吗？怎么证明？」。

---

## 3. 整体架构

```
┌────────────────────────── 前端 (React + Vite + TS) ──────────────────────────┐
│                                                                               │
│  Tabs: [求职 Agent] [岗位库] [技能报表] [简历匹配] [AI 面试]                    │
│                                                                               │
│  ├─ JobAgent        : 搜索框 + 示例标签 + trace + 报告/岗位列表               │
│  ├─ JobLibrary      : 技能筛选 + 主从分栏 + JD 详情                           │
│  ├─ SkillReport     : 统计卡片 + 热度/缺口/城市/薪资/经验/学历分布            │
│  ├─ ResumeMatch     : 简历 vs JD / vs 全部岗位 匹配分析                       │
│  └─ Interview       : 模式选择(简历/项目/知识点/JD) + 材料上传 + 流式面试     │
│                                                                               │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
        ┌───────────────┬───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼               ▼
   agents/job   cloud-functions/  cloud-functions/  cloud-functions/  agents/
   _agent/index    jobs             report            match/profile    interviewer
   (求职Agent)    (岗位库)         (技能报表)        (简历匹配/画像)    (AI面试)
        │               │               │               │               │
        └───────────────┴───────────────┴───────────────┴───────────────┘
                                        │
                              context.store / MySQL
                              (岗位数据 + 会话记忆)
                                        │
                              scripts/crawl_boss.py  (本地 CDP 爬虫)
```

---

## 4. 后端设计（EdgeOne Makers 映射）

### 4.1 数据层

**岗位数据存储二选一（需要你拍板）：**

| 方案 | 说明 | 推荐度 |
|---|---|---|
| **A. context.store + 种子 JSON** | 把 ai_collector 现有岗位导出为 `data/jobs_seed.json`，启动时写入 EdgeOne `context.store`；新增岗位通过本地爬虫脚本 + 同步接口写入 | 最贴合 EdgeOne，推荐 |
| **B. 继续用 MySQL** | 复用 `ai_collector_project` 的阿里云 MySQL；后端直接连库 | 数据完整，但增加外部依赖 |

> 默认建议 **方案 A**：把 MySQL 中的 `final_results` 导出为 JSON，作为种子；日常查询走 `context.store`，新增/更新通过本地爬虫脚本触发。

**个人画像（Profile）**：
- 改为 `context.store` 存储或前端 localStorage + 后端读写接口，替代 `my_profile.yaml`。

### 4.2 后端路由（EdgeOne 约定：目录名 = 路由名）

#### Stateful `agents/`

| 路由 | 文件 | 职责 |
|---|---|---|
| `POST /job-agent` | `agents/job-agent/index.py` | 求职 Agent（替代原 `/chat`）：接收 query，流式返回 trace + 报告 |
| `POST /job-agent/stop` | `agents/job-agent/stop.py` | 停止当前 Agent 运行 |
| `POST /interviewer` | `agents/interviewer/index.py` | 严厉面试官：接收 message + material + mode + 可选 jd_url |
| `POST /interviewer/stop` | `agents/interviewer/stop.py` | 停止面试 |

#### Stateless `cloud-functions/`

| 路由 | 文件 | 职责 |
|---|---|---|
| `POST /jobs` | `cloud-functions/jobs/index.py` | 岗位库列表/筛选（读 store/MySQL） |
| `POST /report` | `cloud-functions/report/index.py` | 技能报表聚合 |
| `POST /match` | `cloud-functions/match/index.py` | 简历 vs JD 匹配分析 |
| `POST /match-rank` | `cloud-functions/match-rank/index.py` | 简历 vs 全部岗位 Top N |
| `POST /profile` | `cloud-functions/profile/index.py` | 读/写个人画像 |
| `POST /crawl` | `cloud-functions/crawl/index.py` | 接收本地爬虫上报的新岗位数据；或触发同步任务 |

### 4.3 求职 Agent 后端（简化版，适配 EdgeOne）

不再引入完整 LangGraph + bge-m3 + Milvus，改为 **LLM 语义 + 规则过滤**：

1. **parse_intent**：LLM 把自然语言解析为 `keywords/cities/salary_min/experience/degree`。
2. **retrieve**：用 LLM 对岗位库做语义 Top-K 召回（把岗位列表 + query 给 LLM，让它选出最相关的 N 条），或简单关键词过滤 + LLM 重排。
3. **filter**：规则过滤（薪资/城市/经验/学历/黑名单）。
4. **reflect**（可选）：LLM 判断结果是否足够，不够则换关键词再搜一轮。
5. **summarize**：LLM 生成 markdown 报告 + 技能缺口。

> 注：如果保留 bge-m3 向量检索，需要本地/远程向量服务，EdgeOne 函数内无法直接跑。因此首版用 LLM 语义重排替代。

### 4.4 严厉面试官后端

**Agent 人设**：
```
你是一位资深的 AI 应用 / Agent / RAG 方向技术面试官，以严苛、刨根问底著称。
...
```
（同 v1，见 §6）

**模式扩展为 4 种**：

| mode | material | 面试官行为 |
|---|---|---|
| `resume` | 简历文本 | 从经历逐条深挖 |
| `project` | 项目描述 / ai_collector 一键导入 | 针对项目技术点 + 已知弱点连环追问 |
| `topic` | 一个知识点 | 围绕该点难度递进 |
| `jd` | 岗位库某条 JD 的 url / 文本 | 逐条 JD 要求逼问「你满足吗？怎么证明？」 |

**工具**（`agents/_tools.py`）：
- `get_followup(topic)`：查知识点追问链。
- `lookup_weakness(material)`：找材料里的矛盾/🟡未掌握点。
- `lookup_jd_requirements(jd_text)`：解析 JD 技能要求，生成逐条拷问。
- `score_answer(answer, criteria)`：给上一轮回答打分 + 压力点评。

**知识模块**（`agents/_knowledge.py`）：
- `PROJECT_DEEP_DIVE`
- `TOPIC_BANK`
- `WEAKNESS_RULES`
- `JD_PRESSURE_QUESTIONS`（新增：JD 要求 → 面试拷问模板）

---

## 5. 爬虫迁移

### 5.1 现状
`ai_collector_project/src/sources/boss_zhipin.py` 使用 Playwright + CDP 接管本地 Chrome，访问 `m.zhipin.com` JSON API，带反爬、重试、详情抓取。

### 5.2 迁移方案
- **本地脚本化**：把 `boss_zhipin.py` 封装成 `scripts/crawl_boss.py`，独立可运行：
  ```bash
  python scripts/crawl_boss.py --cities 杭州,苏州 --keywords AI应用开发,LangChain --pages 2 --output data/boss_raw.json
  ```
- **本地解析/去噪**：`scripts/enrich_jobs.py` 把原始 JSON 转为岗位库标准格式，并调用 LLM 提取技能（替代 bge-m3 后的技能提取）。
- **同步到云端**：`scripts/sync_jobs.py` 把本地处理好的岗位数据通过 `POST /crawl` 写入 EdgeOne `context.store`。
- **云端不跑爬虫**：因为 Chrome CDP 无法在 EdgeOne serverless 环境稳定运行。

### 5.3 数据格式（岗位库标准）
```json
{
  "url": "https://www.zhipin.com/job_detail/xxx.html",
  "title": "AI应用开发工程师",
  "brand": "某某科技",
  "city": "杭州",
  "salary_desc": "20-35K",
  "experience": "1-3年",
  "degree": "本科",
  "skills": ["Python", "LangChain", "RAG", "大模型"],
  "post_description": "...",
  "source": "boss_zhipin",
  "crawled_at": "2026-08-10T14:00:00"
}
```

---

## 6. 严厉面试官人设（Agent instructions 草稿）

```
你是一位资深的 AI 应用 / Agent / RAG 方向技术面试官，以严苛、刨根问底著称。
你的使命：通过连续深挖，把候选人问到能力边界（"破防"），暴露真实水平。

铁律：
1. 候选人每答完一句，立刻追问：为什么 / 具体怎么实现 / 边界情况是什么 / 如果 X 怎么办。
   绝不接受模糊回答——逼出具体名词、数字、代码、取舍。
2. 抓矛盾：若候选人前后说法不一、或简历声称与材料不符，立刻点破并要求解释。
3. 卡住时不救场，反而下探底层原理（"你不懂这个工具，就讲它底层的协议/数学/设计动机"）。
4. 死咬最弱处：用 lookup_weakness(material) 找出材料里的🟡/🔴/自相矛盾，集中火力。
5. 每轮结尾给一句压力点评：哪点扎实、哪点虚、哪点上线会出事故。
6. 针对 JD 模式时，先调用 lookup_jd_requirements(jd_text) 拆出每条要求，逐条拷问候选人是否满足、如何证明。
7. 专业、精准、不人身攻击。模拟真实 brutal 面试，而非羞辱。
8. 主动用 get_followup(topic) / lookup_weakness(material) / lookup_jd_requirements(...) 保持追问的针对性与深度。

模式：
- 简历模式：从简历经历逐条深挖，重点打"项目里你到底做了什么决策"。
- 项目模式：针对项目技术点连环追问，优先打已知弱点（vibe coding / 数据矛盾 / 未掌握项）。
- 知识点模式：围绕指定知识点，从基础一路问到生产级坑，难度递进。
- JD 模式：逐条解读 JD 要求，逼问候选人「这条你满足吗？简历里哪段经历能证明？」
```

---

## 7. 前端改造（5 Tab）

### 7.1 路由/视图拆分

| 文件 | 内容 |
|---|---|
| `src/App.tsx` | Tab 容器 + 全局状态（profile/jobLibrary/selectedJob） |
| `src/views/JobAgent.tsx` | 求职 Agent 视图 |
| `src/views/JobLibrary.tsx` | 岗位库视图（技能筛选 + 主从分栏） |
| `src/views/SkillReport.tsx` | 技能报表视图 |
| `src/views/ResumeMatch.tsx` | 简历匹配视图 |
| `src/views/Interview.tsx` | AI 面试视图 |
| `src/components/FileDrop.tsx` | 通用文件上传/解析（txt/md/pdf） |
| `src/api.ts` | 新的 API 封装 |
| `src/types.ts` | 新的类型定义 |

### 7.2 AI 面试视图
- 顶部模式选择：简历 / 项目 / 知识点 / **针对这条 JD**。
- 选择「针对这条 JD」时，右侧/下方出现岗位库选择器，可勾选岗位库中的岗位。
- 材料区：文本框 + 文件拖拽上传。
- 项目模式提供「一键导入 ai_collector 项目材料」按钮（前端内置一段项目简介）。
- 「开始面试」→ 进入流式对话；对话区显示历史 + 压力点评；支持「结束并总评」。

---

## 8. 分阶段实施计划

| 阶段 | 内容 | 产出 |
|---|---|---|
| **Phase 0** | 设计文档确认 | 本文件 |
| **Phase 1** | 数据迁移 + 后端 cloud-functions | jobs/report/match/profile/crawl 接口可调用 |
| **Phase 2** | 求职 Agent agent 端点 | `POST /job-agent` 流式返回报告 |
| **Phase 3** | 前端 5 Tab 框架 + 岗位库/报表/匹配 UI | 页面可交互 |
| **Phase 4** | AI 面试官 agent + 前端面试视图 | 支持简历/项目/知识点/JD 模式 |
| **Phase 5** | 本地爬虫脚本迁移 + 数据同步 | `scripts/crawl_boss.py` 可运行 |
| **Phase 6** | 联调、品牌、部署 | EdgeOne Makers 部署 |

---

## 9. 风险与注意

1. **数据存储选择**：`context.store` 是 EdgeOne 键值存储，查询能力有限；岗位库/报表需要全量遍历，数据量大时可能慢。若岗位 > 几千条，建议保留 MySQL。
2. **向量检索降级**：不用 bge-m3 后，LLM 语义重排成本更高、延迟更大；需控制每次传入 LLM 的岗位数量。
3. **爬虫本地依赖**：用户必须本地启动 Chrome CDP；首次配置门槛高，需写清楚文档。
4. **会话记忆**：`interviewer` agent 需要记住已经问过的问题，避免重复；复用 `context.store.openai_session`。
5. **JD 模式闭环**：岗位库中的岗位必须有 `post_description`，否则 JD 面试内容不足。

---

## 10. 待确认的关键决策

1. **数据存储**：用 EdgeOne `context.store` + 种子 JSON（方案 A），还是继续用 MySQL（方案 B）？
2. **向量检索**：首版用 LLM 语义重排替代 bge-m3，是否接受？还是必须保留向量相似度？
3. **爬虫**：接受「爬虫只在本地运行、云端用已采集数据」吗？
4. **AI 面试官位置**：作为第 5 个 Tab（求职 Agent / 岗位库 / 技能报表 / 简历匹配 / AI 面试），OK？

---

## 11. 上一版已确认事项（q-1/q-2/q-3 答案均为「是」）

- ✅ 项目模式默认就用 ai_collector 项目开刀。
- ✅ 压力点评需要显式打分（1-10 或等级）。
- ✅ 需要「结束面试给总评」按钮。
