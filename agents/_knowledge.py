"""
Interviewer knowledge base — private module (starts with _), not a route.

This is the "ammunition" that lets the strict interviewer drill the candidate
to the breaking point. It is sourced from the candidate's own repo
(ai_collector_project): INTERVIEW_GUIDE.md, JD_MAPPING.md, qa_review.md and the
resume. Two layers:

  1. Curated structures (WEAKNESSES / TOPIC_CHAINS) — hand-extracted, high signal,
     used to press on contradictions and run progressive follow-up chains.
  2. Raw doc search (search_knowledge) — keyword/section scan over the vendored
     markdown for deeper, on-demand lookups.

Docs are vendored into data/knowledge/ at deploy time (see scripts + edgeone.json
build step). KNOWLEDGE_DIR overrides the location.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from ._logger import create_logger

logger = create_logger("knowledge")

_KNOWLEDGE_DIR = os.path.abspath(
    os.getenv("KNOWLEDGE_DIR", os.path.join(os.path.dirname(__file__), "_kb"))
)

_DOCS = {
    "interview_guide": "INTERVIEW_GUIDE.md",
    "jd_mapping": "JD_MAPPING.md",
    "qa_review": "qa_review.md",
    "resume": "简历_Andy_AI应用开发工程师.md",
}

_cache: dict[str, str] = {}


# ========== Known weak points (contradictions / self-admitted gaps) ==========
# These are the spots the strict interviewer should press on hardest. Each entry
# is a concrete, verifiable contradiction the candidate has left in their own repo.
WEAKNESSES: list[dict] = [
    {
        "id": "vibe-coding",
        "topic": "项目真实性与技术深度",
        "evidence": "qa_review.md Q5 自认：项目是 vibe coding 搭的，跟 LangChain/LangGraph 具体什么关系说不清；study_log 也承认是 vibe coding 搭的。但简历写「独立从 0 到 1 主导」。",
        "probe": "你说项目是从 0 到 1 主导的，但又在复盘里写这是 vibe coding 搭的、不清楚和 LangGraph 的关系。那你到底主导了什么？如果再问你 LangGraph 的 CheckPointer 怎么落地的，你能答上来吗？",
    },
    {
        "id": "data-count",
        "topic": "数据采集规模",
        "evidence": "README 数据前后矛盾：RAG 层写 47 条、项目亮点写 242 条、又说采集了 192 条 Boss JD。",
        "probe": "你到底采集了多少条数据？README 里 47 / 192 / 242 三个数字互相打架。你连自己采集了多少都说不清，凭什么说 RAG 检索有效？",
    },
    {
        "id": "multi-agent",
        "topic": "多 Agent 架构",
        "evidence": "JD_MAPPING 大量 🟡：多 Agent 没有真正拆分，只有一个图；所谓「多 Agent」其实是单图多节点。",
        "probe": "你简历写「多 Agent 协作」，但 JD_MAPPING 自己标了 🟡 说其实是单图多节点。那你所谓的 Agent 边界在哪？节点和 Agent 的区别你讲得清吗？",
    },
    {
        "id": "mcp-review",
        "topic": "MCP 安全",
        "evidence": "JD_MAPPING 🟡：MCP 没有做内容审查，工具调用直接透传。",
        "probe": "你的 MCP 工具调用是直通的、没有内容审查。如果某个 MCP 工具返回了恶意指令或泄露了密钥，你的 Agent 会怎么反应？你不审查，是不是等于把执行权完全交出去了？",
    },
    {
        "id": "dspy",
        "topic": "DSPy / 提示优化",
        "evidence": "JD_MAPPING 🟡：DSPy 没真正做过，只是提了。",
        "probe": "你说用过 DSPy 做提示优化，但 JD_MAPPING 标了 🟡 说没真正做过。DSPy 的 teleprompter 是怎么工作的？你如果只调过 demo，那这算「做过」吗？",
    },
    {
        "id": "cdp-anti",
        "topic": "反爬 / CDP",
        "evidence": "项目用 Playwright + CDP 过 Boss 直聘风控，但具体绕过了哪个检测点（指纹/行为/TLS）说不清。",
        "probe": "你说用 CDP 过了 Boss 的风控，那你绕的是哪一层？是 Canvas 指纹、WebDriver 检测、还是请求签名？如果 Boss 明天加了行为风控（鼠标轨迹），你的爬虫还活得了吗？",
    },
    {
        "id": "faiss",
        "topic": "向量检索",
        "evidence": "用 FAISS 做召回，但没评估过召回率，也没做重排；维度、距离度量、与 Milvus 的差异不清楚。",
        "probe": "你用 FAISS 做向量召回，用的什么距离度量？为什么不用余弦？你评估过召回率吗？如果 top-k 里混进了无关 JD，下游 LLM 重排你做了没有？没做的话「语义匹配」就是空话。",
    },
    {
        "id": "rag-eval",
        "topic": "RAG 评估",
        "evidence": "RAG 管线没有离线评估，召回/生成质量靠「感觉」。",
        "probe": "你的 RAG 有没有离线评估集？召回率、命中率怎么量的？你说 RAG 有效，依据是什么——是跑通了，还是真的测过？",
    },
]


# ========== Progressive follow-up chains per topic ==========
# Each chain is a sequence of increasingly hostile/deep questions designed to
# walk the candidate from "I used X" down to "explain X at the metal level".
TOPIC_CHAINS: dict[str, list[str]] = {
    "langgraph": [
        "你说项目用 LangGraph 做编排，图里有哪些节点？状态是怎么在节点间传递的？",
        "LangGraph 的 State 和 Redux 的 store 有什么本质区别？为什么不用普通函数调用？",
        "CheckPointer 你用的是哪种后端？中断恢复时，部分完成的节点怎么回滚？",
        "如果某个节点抛异常，整个图是重跑还是从断点续跑？你怎么做幂等？",
        "你说多 Agent，但其实就是单图多节点。那和写一串函数有什么区别？你真正需要「多 Agent」解决的是什么问题？",
    ],
    "faiss": [
        "召回用的什么向量模型？维度多少？距离度量用的 L2 还是内积？为什么？",
        "你做没做归一化？不做余弦归一化的话，内积距离会有什么偏差？",
        "FAISS 的 IVF 你调过 nprobe 吗？召回率和延迟怎么权衡？",
        "数据量上来后 FAISS 是单机内存，你怎么做分片？和 Milvus 比你的方案输在哪？",
        "你评估过召回率吗？如果 top-5 里混进无关项，下游怎么兜住？",
    ],
    "cdp": [
        "Boss 直聘的风控你具体绕了哪一层？指纹、行为、还是请求签名？",
        "Playwright 默认的 WebDriver 指纹你怎么抹掉的？CDP 在这步干了什么？",
        "如果目标站加了行为风控（鼠标轨迹 / 停留时长），你的脚本怎么模拟？",
        "你的代理 IP 是怎么管理的？被封了怎么轮换？有没有漏桶/令牌桶限流？",
        "这种采集方式合规吗？如果对方发律师函，你的数据链路能撇清吗？",
    ],
    "rag": [
        "你的 RAG 切片策略是什么？按固定长度还是语义边界？重叠窗口多大？",
        "检索回来的 chunk 你怎么排序喂给 LLM？做过重排（rerank）吗？",
        "有没有上下文压缩？20 个 chunk 全塞进去，LLM 会注意力稀释你测过吗？",
        "你用什么指标证明 RAG 比直接问 LLM 好？有离线评估集吗？",
        "如果知识库里没有答案，你的 RAG 会编造还是拒答？怎么区分「检索为空」？",
    ],
    "mcp": [
        "你接了哪些 MCP 服务？工具是怎么被 Agent 发现的？",
        "MCP 工具返回的内容你做内容审查吗？不审查的话，工具能反过来操控 Agent 吗？",
        "如果某个 MCP 工具响应里夹带了「忽略之前指令」这种提示，你的 Agent 会中招吗？",
        "MCP 和 Function Calling 本质上区别在哪？你为什么不直接用 OpenAI 的 tools？",
        "多个 MCP 工具并发调用，你怎么保证执行顺序和副作用可控？",
    ],
    "reflection": [
        "你说有反思循环，反思是谁触发的？是 LLM 自己判断还是规则触发？",
        "Agent 怎么知道自己答错了？有验证器（validator）吗？还是纯靠「感觉不对」？",
        "反思如果无限循环怎么办？你有没有最大迭代次数和收敛判定？",
        "你复盘里写了好几个 bad case，这些 bad case 现在是测试集的一部分吗？还是写完就忘了？",
    ],
    "plugin": [
        "你的插件架构，插件和主程序是怎么解耦的？热加载怎么做？",
        "插件崩溃会影响主 Agent 吗？你做进程隔离还是线程隔离？",
        "插件的权限边界怎么划？一个插件能读另一个插件的数据吗？",
    ],
}


# ========== Loaders ==========
def _load_doc(key: str) -> str:
    if key in _cache:
        return _cache[key]
    fname = _DOCS.get(key)
    if not fname:
        return ""
    path = os.path.join(_KNOWLEDGE_DIR, fname)
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        _cache[key] = text
        logger.log(f"[knowledge] loaded {key}: {len(text)} chars from {path}")
        return text
    except FileNotFoundError:
        logger.error(f"[knowledge] doc not found: {path}")
        return ""


def get_resume() -> str:
    """Return the candidate's resume markdown (or empty string if not present)."""
    return _load_doc("resume")


def get_weaknesses() -> list[dict]:
    """Return the curated list of contradictions / self-admitted gaps."""
    return WEAKNESSES


def get_followup_chain(topic: str) -> list[str]:
    """Return the progressive follow-up chain for a topic (empty if unknown)."""
    return TOPIC_CHAINS.get(topic.strip().lower(), [])


def search_knowledge(query: str, max_chars: int = 2400) -> str:
    """Keyword/section scan over the vendored docs, returning relevant excerpts.

    Cheap, dependency-free: scores sections (split by markdown headings) by
    keyword hits and returns the top matches concatenated.
    """
    query_terms = [t for t in re.split(r"[\s,，。、]+", query.lower()) if len(t) > 1]
    if not query_terms:
        return ""

    corpus = "\n\n".join(
        f"# {key}\n{_load_doc(key)}" for key in ("interview_guide", "jd_mapping", "qa_review")
    )
    # Split into sections by markdown headings.
    sections = re.split(r"(?m)^#{1,4}\s+", corpus)
    scored: list[tuple[int, str]] = []
    for sec in sections:
        sec_low = sec.lower()
        score = sum(sec_low.count(t) for t in query_terms)
        if score > 0:
            scored.append((score, sec[:max_chars]))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return ""
    return "\n\n".join(s for _, s in scored[:4])
