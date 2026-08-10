const zh = {
  // Header
  "app.title": "AI 求职面试官",
  "app.subtitle": "EdgeOne Makers · 求职 Agent · 严厉面试官 · 岗位库 · 技能报表 · 简历匹配",

  "empty.title": "AI 求职面试官",
  "empty.hint": "我运行在 EdgeOne 上，是一个 OpenAI Agent：能帮你找工作、做严厉面试、出市场报表、做简历匹配。",
  "empty.features": "EdgeOne Store · 会话记忆 · Agent Tools",

  "chat.placeholder": "发消息…  ⏎ 发送 · Shift+⏎ 换行",
  "chat.hint": "由 OpenAI Agents SDK + EdgeOne Makers 驱动 · 仅供演示",

  "preset.1": "帮我找上海 3 年经验 Python AI 工程师，15-25K",
  "preset.2": "现在 AI 应用岗位最缺哪些技能？",

  // Tool lamps — interviewer agent
  "tool.weakness": "弱点探查",
  "tool.followup": "追问链",
  "tool.knowledge": "知识检索",
  "tool.jd": "JD 调取",
  "tool.weather": "天气查询",
  "tool.clothing": "穿衣建议",
  "tool.translate": "文本翻译",
  "tool.statistics": "文本统计",

  "status.error": "⚠️ 请求失败，请检查后端服务是否启动。",
  "status.stopped": "⏹ *已停止生成*",
  "status.backendError": "⚠️ 后端中断请求失败，服务端可能仍在运行。",

  "debug.title": "传输流",
  "debug.events": "事件",
  "debug.clear": "清除",
  "debug.empty": "等待 SSE 事件...",
  "debug.emptyHint": "发送消息后，所有原始后端数据将在此处显示。",

  "sidebar.label": "会话列表",
  "sidebar.title": "会话",
  "sidebar.newChat": "新建聊天",
  "sidebar.loading": "正在加载会话...",
  "sidebar.loadMore": "加载更多",
  "sidebar.loadingMore": "加载中...",
  "sidebar.emptyTitle": "暂无会话",
  "sidebar.emptyHint": "点击「新建聊天」开始第一段对话。",
  "sidebar.delete": "删除会话",
  "sidebar.deleteConfirm": "确定要永久删除这个会话吗？此操作不可恢复。",

  "aria.send": "发送",
  "aria.clearHistory": "清除历史",
  "aria.stopGeneration": "停止生成",

  "lang.switch": "English",

  "floatingLink.deploy": "一键部署",
  "floatingLink.github": "GitHub",

  // ── Tabs ──
  "tabs.jobAgent": "求职 Agent",
  "tabs.jobs": "岗位库",
  "tabs.report": "技能报表",
  "tabs.match": "简历匹配",
  "tabs.interview": "AI 面试",

  // ── Job Agent ──
  "jobAgent.title": "求职 Agent",
  "jobAgent.subtitle": "用自然语言描述需求，它会检索岗位库并给出建议。",
  "jobAgent.empty": "告诉我你想找的岗位、城市、薪资和经验，例如「上海 3 年 Python AI，15-25K」。",
  "jobAgent.hint": "由 OpenAI Agents SDK + EdgeOne Makers 驱动",

  // ── Job Library ──
  "jobs.title": "岗位库",
  "jobs.subtitle": "本地爬虫采集自 Boss 直聘（已同步到 MySQL）。",
  "jobs.searchPlaceholder": "按关键词搜索（岗位 / 公司 / 技能）…",
  "jobs.filterCity": "城市",
  "jobs.filterSkill": "技能",
  "jobs.resultCount": "共 {n} 个岗位",
  "jobs.empty": "没有符合当前筛选条件的岗位。",
  "jobs.viewDetail": "查看 JD",
  "jobs.detailClose": "关闭",
  "jobs.salary": "薪资",
  "jobs.city": "城市",
  "jobs.exp": "经验",
  "jobs.edu": "学历",
  "jobs.skills": "技能",
  "jobs.useForInterview": "用这条 JD 面试我",
  "jobs.loading": "岗位加载中…",

  // ── Skills Report ──
  "report.title": "市场技能报表",
  "report.subtitle": "基于岗位库聚合统计。",
  "report.total": "岗位总数",
  "report.topSkills": "热门技能",
  "report.cities": "城市分布",
  "report.education": "学历分布",
  "report.experience": "经验分布",
  "report.salaryAvg": "平均薪资 (K)",
  "report.noData": "暂无数据。请先运行爬虫或连接 MySQL。",
  "report.distribution": "分布",

  // ── Resume Match ──
  "match.title": "简历匹配",
  "match.subtitle": "粘贴简历，针对单条 JD 或全部岗位做 LLM 语义匹配排序。",
  "match.resumeLabel": "你的简历",
  "match.resumePlaceholder": "在此粘贴简历文本（或上传 .txt / .md / .pdf 文件）…",
  "match.uploadLabel": "上传简历",
  "match.uploadHint": "支持 .txt / .md / .pdf",
  "match.selectJdLabel": "针对某条 JD 匹配",
  "match.selectJdPlaceholder": "选择岗位（可选）",
  "match.allJobsBtn": "对全部岗位排序",
  "match.matchBtn": "开始匹配",
  "match.empty": "请先粘贴简历，然后选择 JD 或对全部岗位排序。",
  "match.score": "匹配分",
  "match.reason": "理由",
  "match.useForInterview": "用这条 JD 去面试",
  "match.interviewModeHint": "将切换到 AI 面试 Tab 的 JD 模式。",
  "match.rankTitle": "全部岗位匹配排序",
  "match.scoreTitle": "单岗位匹配",
  "match.missingResume": "请先粘贴或上传你的简历。",
  "match.loading": "匹配中…",

  // ── AI Interview ──
  "interview.title": "严厉技术面试官",
  "interview.subtitle": "会刨根问底、问到你破防的严苛面试官。上传素材可聚焦拷问方向。",
  "interview.setupTitle": "面试设置",
  "interview.setupHint": "选择模式并提供素材，面试官据此深挖你。",
  "interview.modeLabel": "模式",
  "interview.mode.resume": "简历深挖",
  "interview.mode.project": "项目拷问",
  "interview.mode.knowledge": "知识点",
  "interview.mode.jd": "指定 JD",
  "interview.materialPlaceholder": "粘贴你的简历 / 项目描述 / 想被考察的知识点…",
  "interview.knowledgePlaceholder": "想被拷问的具体知识点，例如「RAG 召回率」「LangGraph CheckPoint」。",
  "interview.uploadLabel": "上传素材",
  "interview.uploadHint": "支持 .txt / .md / .pdf",
  "interview.jdSelectLabel": "选择要面试的 JD",
  "interview.jdSelectPlaceholder": "从已采集的 JD 中选择…",
  "interview.startBtn": "开始面试",
  "interview.jdReady": "JD 已载入——开始面试并逐条作答。",
  "interview.finishBtn": "结束并生成总评",
  "interview.scoreTitle": "综合评估",
  "interview.scoreGenerating": "正在生成综合评估…",

  // ── Upload / common ──
  "upload.txtMd": "文本 / Markdown",
  "upload.pdf": "PDF",
  "upload.parsing": "正在解析 {name}…",
  "upload.parseError": "无法解析 {name}。请用 .txt / .md，或直接粘贴文本。",
  "upload.drop": "拖拽文件到此处或点击上传",
  "common.loading": "加载中…",
  "common.noData": "暂无数据",
  "common.back": "返回",
  "common.error": "出错了。",
} as const;

export default zh;
