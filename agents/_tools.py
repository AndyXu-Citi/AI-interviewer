"""
Agent Tools — private module (starts with _), not mapped as a route.

Replaces the starter's mock tools (weather/clothing/translate/stats) with
interviewer tools. These give the strict interviewer real digging material:
known contradictions to press on, progressive follow-up chains, raw doc search,
and (for JD mode) the ability to pull a specific job description to grill on.
"""

from typing import Annotated

from agents import function_tool

from ._knowledge import (
    get_followup_chain,
    get_weaknesses,
    search_knowledge,
    TOPIC_CHAINS,
)


# ========== Tool: Lookup known weaknesses ==========
@function_tool
def lookup_weakness() -> str:
    """Return the candidate's known weak points and contradictions (from their own repo) to press on hardest.

    Use this early and often: it surfaces the spots where the candidate has
    contradicted themselves (e.g. "built from 0 to 1" vs "vibe coding", or
    conflicting data counts) so you can drill until they break.
    """
    items = get_weaknesses()
    return "\n\n".join(
        f"[{w['id']}] {w['topic']}\n证据: {w['evidence']}\n追问: {w['probe']}"
        for w in items
    )


# ========== Tool: Get progressive follow-up chain ==========
@function_tool
def get_followup_chain(topic: Annotated[str, "Technical topic to drill, e.g. langgraph, faiss, cdp, rag, mcp, reflection, plugin"]) -> str:
    """Return a progressive chain of increasingly hostile follow-up questions for a topic.

    Pick the topic the candidate just claimed expertise in, then walk them from
    'I used X' down to 'explain X at the metal level'. Available topics:
    """ + ", ".join(sorted(TOPIC_CHAINS.keys())) + "."
    chain = get_followup_chain(topic)
    if not chain:
        return (
            "Unknown topic. Available topics: "
            + ", ".join(sorted(TOPIC_CHAINS.keys()))
            + ". Ask the candidate to pick one they claimed, or use search_knowledge instead."
        )
    return "\n".join(f"{i+1}. {q}" for i, q in enumerate(chain))


# ========== Tool: Search raw knowledge docs ==========
@function_tool
def search_knowledge(query: Annotated[str, "What to look up in the interview guide / JD mapping / QA review"]) -> str:
    """Search the candidate's own interview guide, JD mapping and QA review for relevant excerpts.

    Use when you need the exact standard answer or the candidate's past mistakes
    on a specific point, so you can compare it against what they say now.
    """
    return search_knowledge(query) or "No matching section found in the knowledge base."


# ========== Tool: Get a JD to interview against ==========
@function_tool
def get_jd(jd_id: Annotated[str, "Job id from the job library (encryptJobId or numeric id)"]) -> str:
    """Fetch a specific job description from the job library, so you can interview the candidate against that exact JD.

    Use in JD mode: pull the requirements, then grill the candidate line by line
    on every skill the JD lists. Returns title, company, salary, city, skills and
    the full post description.
    """
    from ._db import get_job

    job = get_job(jd_id)
    if not job:
        return f"No job found for id={jd_id!r}. List jobs first to get valid ids."
    return (
        f"职位: {job.get('title')}\n"
        f"公司: {job.get('company')}\n"
        f"薪资: {job.get('salary')}\n"
        f"城市: {job.get('city')} {job.get('district', '')}\n"
        f"经验: {job.get('experience')}  学历: {job.get('education')}\n"
        f"技能要求: {', '.join(job.get('skills', []))}\n"
        f"JD 全文:\n{job.get('description', '')}"
    )
