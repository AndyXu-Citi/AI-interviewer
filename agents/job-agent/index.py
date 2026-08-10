"""
Agent handler — EdgeOne Makers
========================================

agents/job-agent/index.py is auto-mapped to **POST /job-agent**.

A helpful job-search assistant: takes a natural-language need (e.g.
"上海 3 年 Python AI 工程师 15-25K"), retrieves from the job library, consults
the market report for context, and streams a concise recommendation.
"""

from typing import Any, AsyncGenerator
import asyncio
import json

from agents import Agent, Runner, function_tool

from .._logger import create_logger
from .._llm import get_model
from .._db import search_jobs, get_report


logger = create_logger("job-agent")


@function_tool
def search_jobs_tool(
    query: str = "",
    city: str = "",
    skill: str = "",
) -> str:
    """Search the job library. Returns matching jobs (title, company, salary, city, skills)."""
    jobs = search_jobs(query=query, city=city, skill=skill)
    return json.dumps({"total": len(jobs), "jobs": jobs[:20]}, ensure_ascii=False)


@function_tool
def market_report_tool() -> str:
    """Return the market report: top skills in demand, city/salary/education distribution."""
    return json.dumps(get_report(), ensure_ascii=False)


PERSONA = (
    "你是一个求职助理，帮候选人从岗位库里找到最匹配的岗位。\n"
    "工作流程：\n"
    "1. 从用户的自然语言需求里拆出关键词：城市、经验、技能、薪资、岗位名。\n"
    "2. 调用 search_jobs_tool 检索；必要时用 market_report_tool 看市场热度做筛选。\n"
    "3. 给出 Top 5 推荐，每条说明匹配点和一句话理由，并指出薪资/要求是否契合。\n"
    "4. 用中文、简洁、列表化呈现。不要编造岗位库里没有的岗位。\n"
)


agent = Agent(
    name="JobAgent",
    instructions=PERSONA,
    tools=[search_jobs_tool, market_report_tool],
    model=get_model(),
)


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(message: str, session=None, cancel_signal: asyncio.Event | None = None) -> AsyncGenerator[str, None]:
    result = Runner.run_streamed(agent, input=message, session=session)
    async for event in result.stream_events():
        if cancel_signal and cancel_signal.is_set():
            break
        if event.type == "raw_response_event" and getattr(event.data, "type", None) == "response.output_text.delta":
            delta = getattr(event.data, "delta", "")
            if delta:
                yield sse_event("text_delta", {"delta": delta})
        elif event.type == "run_item_stream_event" and event.name == "tool_called":
            tool_name = (
                getattr(event.item, "name", None)
                or getattr(getattr(event.item, "raw_item", None), "name", None)
            )
            if tool_name:
                yield sse_event("tool_called", {"tool": tool_name})


async def handler(context: Any) -> AsyncGenerator[str, None]:
    request = context.request
    body = request.body
    message = body.get("message") if isinstance(body, dict) else None
    if not message:
        yield sse_event("error", {"message": "'message' is required"})
        yield sse_event("done", {})
        return

    raw_user_id = body.get("userId") or body.get("user_id") or "" if isinstance(body, dict) else ""
    user_id = str(raw_user_id).strip() or None
    cid = context.conversation_id
    logger.log(f"[job-agent] cid={cid}, uid={user_id or '-'}, message={message[:50]!r}")

    if user_id and cid:
        try:
            existing = await context.store.get_messages(conversation_id=cid, limit=1)
            if not existing:
                await context.store.append_message(conversation_id=cid, role="user", content=message, user_id=user_id)
        except Exception as e:
            logger.error(f"[job-agent] user-index failed: {type(e).__name__}: {e}")

    session = context.store.openai_session(cid) if cid else None
    cancel_signal = request.signal
    stopped = False
    try:
        async for frame in _event_stream(message, session, cancel_signal):
            if cancel_signal.is_set():
                stopped = True
                break
            yield frame
    except asyncio.CancelledError:
        stopped = True
    except Exception as e:
        logger.error(f"[job-agent] error: {type(e).__name__}: {e}")
        yield sse_event("error", {"message": str(e), "errorType": type(e).__name__})
    finally:
        yield sse_event("done", {"stopped": stopped})
