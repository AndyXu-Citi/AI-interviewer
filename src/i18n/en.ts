const en = {
  // Header
  "app.title": "AI Job Interview Coach",
  "app.subtitle": "EdgeOne Makers · Job Agent · Strict Interviewer · Job Library · Skills Report · Resume Match",

  "empty.title": "AI Job Interview Coach",
  "empty.hint": "I run on EdgeOne as an OpenAI Agent: job search, strict interviews, market report and resume matching.",
  "empty.features": "EdgeOne Store · Session Memory · Agent Tools",

  "chat.placeholder": "Type a message…  ⏎ send · Shift+⏎ newline",
  "chat.hint": "Powered by OpenAI Agents SDK + EdgeOne Makers · demo only",

  "preset.1": "Help me find AI engineering jobs in Shanghai, 3y exp, 15-25K",
  "preset.2": "What skills are most in demand for AI application roles right now?",

  // Tool lamps — interviewer agent
  "tool.weakness": "Weakness Probe",
  "tool.followup": "Follow-up Chain",
  "tool.knowledge": "Knowledge Search",
  "tool.jd": "JD Lookup",
  // (legacy starter tools, kept for parity)
  "tool.weather": "Weather",
  "tool.clothing": "Clothing",
  "tool.translate": "Translate",
  "tool.statistics": "Statistics",

  "status.error": "⚠️ Request failed. Check the backend is running.",
  "status.stopped": "⏹ *generation stopped*",
  "status.backendError": "⚠️ Backend abort failed; the server may still be running.",

  "debug.title": "Stream",
  "debug.events": "Events",
  "debug.clear": "Clear",
  "debug.empty": "Waiting for SSE events...",
  "debug.emptyHint": "All raw backend frames appear here after you send a message.",

  "sidebar.label": "Conversations",
  "sidebar.title": "Chats",
  "sidebar.newChat": "New chat",
  "sidebar.loading": "Loading conversations...",
  "sidebar.loadMore": "Load more",
  "sidebar.loadingMore": "Loading...",
  "sidebar.emptyTitle": "No conversations",
  "sidebar.emptyHint": "Click “New chat” to start.",
  "sidebar.delete": "Delete conversation",
  "sidebar.deleteConfirm": "Permanently delete this conversation? This cannot be undone.",

  "aria.send": "Send",
  "aria.clearHistory": "Clear history",
  "aria.stopGeneration": "Stop generation",

  "lang.switch": "中文",

  "floatingLink.deploy": "Deploy",
  "floatingLink.github": "GitHub",

  // ── Tabs ──
  "tabs.jobAgent": "Job Agent",
  "tabs.jobs": "Job Library",
  "tabs.report": "Skills Report",
  "tabs.match": "Resume Match",
  "tabs.interview": "AI Interview",

  // ── Job Agent ──
  "jobAgent.title": "Job-Search Agent",
  "jobAgent.subtitle": "Describe what you want in plain language; it searches the library and advises.",
  "jobAgent.empty": "Tell me the role, city, salary and experience you want — e.g. “Shanghai, 3y Python AI, 15-25K”.",
  "jobAgent.hint": "Powered by OpenAI Agents SDK + EdgeOne Makers",

  // ── Job Library ──
  "jobs.title": "Job Library",
  "jobs.subtitle": "Boss Zhipin jobs collected by the local crawler (synced to MySQL).",
  "jobs.searchPlaceholder": "Search by keyword (title / company / skill)…",
  "jobs.filterCity": "City",
  "jobs.filterSkill": "Skill",
  "jobs.resultCount": "{n} jobs",
  "jobs.empty": "No jobs match the current filters.",
  "jobs.viewDetail": "View JD",
  "jobs.detailClose": "Close",
  "jobs.salary": "Salary",
  "jobs.city": "City",
  "jobs.exp": "Experience",
  "jobs.edu": "Education",
  "jobs.skills": "Skills",
  "jobs.useForInterview": "Interview me on this JD",
  "jobs.loading": "Loading jobs…",

  // ── Skills Report ──
  "report.title": "Market Skills Report",
  "report.subtitle": "Aggregated from the job library.",
  "report.total": "Total jobs",
  "report.topSkills": "Top skills in demand",
  "report.cities": "Cities",
  "report.education": "Education",
  "report.experience": "Experience",
  "report.salaryAvg": "Avg salary (K)",
  "report.noData": "No data yet. Run the crawler or connect MySQL.",
  "report.distribution": "Distribution",

  // ── Resume Match ──
  "match.title": "Resume Match",
  "match.subtitle": "Paste your resume, then match against one JD or all jobs (LLM semantic ranking).",
  "match.resumeLabel": "Your resume",
  "match.resumePlaceholder": "Paste your resume text here (or upload a .txt / .md / .pdf file)…",
  "match.uploadLabel": "Upload resume",
  "match.uploadHint": "Supports .txt / .md / .pdf",
  "match.selectJdLabel": "Match against a specific JD",
  "match.selectJdPlaceholder": "Pick a job (optional)",
  "match.allJobsBtn": "Rank against ALL jobs",
  "match.matchBtn": "Match",
  "match.empty": "Paste a resume first, then choose a JD or rank against all jobs.",
  "match.score": "Match score",
  "match.reason": "Why",
  "match.useForInterview": "Use this JD for an interview",
  "match.interviewModeHint": "Switches to the AI Interview tab in JD mode.",
  "match.rankTitle": "Ranking across all jobs",
  "match.scoreTitle": "Single-Job Match",
  "match.missingResume": "Please paste or upload your resume first.",
  "match.loading": "Matching…",

  // ── AI Interview ──
  "interview.title": "Strict Technical Interviewer",
  "interview.subtitle": "A harsh interviewer who digs until you break. Upload material to focus the grilling.",
  "interview.setupTitle": "Interview setup",
  "interview.setupHint": "Pick a mode and provide material. The interviewer uses it to drill you.",
  "interview.modeLabel": "Mode",
  "interview.mode.resume": "Resume deep-dive",
  "interview.mode.project": "Project grilling",
  "interview.mode.knowledge": "Knowledge point",
  "interview.mode.jd": "Specific JD",
  "interview.materialPlaceholder": "Paste your resume / project description / the knowledge point you want to be tested on…",
  "interview.knowledgePlaceholder": "The specific topic to grill you on, e.g. “RAG recall rate”, “LangGraph checkpoint”.",
  "interview.uploadLabel": "Upload material",
  "interview.uploadHint": "Supports .txt / .md / .pdf",
  "interview.jdSelectLabel": "Pick a JD to interview on",
  "interview.jdSelectPlaceholder": "Choose a collected JD…",
  "interview.startBtn": "Start interview",
  "interview.jdReady": "JD loaded — start the interview and answer each question.",
  "interview.finishBtn": "End & get overall assessment",
  "interview.scoreTitle": "Overall assessment",
  "interview.scoreGenerating": "Generating overall assessment…",

  // ── Upload / common ──
  "upload.txtMd": "Text / Markdown",
  "upload.pdf": "PDF",
  "upload.parsing": "Parsing {name}…",
  "upload.parseError": "Could not parse {name}. Use .txt / .md, or paste the text.",
  "upload.drop": "Drop file here or click to upload",
  "common.loading": "Loading…",
  "common.noData": "No data",
  "common.back": "Back",
  "common.error": "Something went wrong.",
} as const;

export default en;
