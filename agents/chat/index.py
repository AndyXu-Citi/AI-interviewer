"""
Agent handler — EdgeOne Makers
========================================

The file path agents/chat/index.py is auto-mapped to **POST /chat**.

This handler is the STRICT TECHNICAL INTERVIEWER. It streams SSE, keeps session
memory, and injects candidate material (resume / project / knowledge point / JD)
so the interviewer can drill the candidate to the breaking point.

`context` contract (EdgeOne Makers):
    context.request.body    — dict, request body
    context.request.signal  — asyncio.Event, set when /chat/stop is called
    context.conversation_id — conversation ID
    context.run_id          — run ID for this invocation
    context.store           — EdgeOne built-in store; openai_session() for memory
"""

from typing import Any, AsyncGenerator
import asyncio
import json

from agents import Agent, Runner

from .._logger import create_logger
from .._llm import get_model
from .._tools import lookup_weakness, get_followup_chain, search_knowledge, get_jd


logger = create_logger("interviewer")

MODES = ("resume", "project", "knowledge", "jd")


def _mode_block(data: dict) -> str:
    mode = (data.get("mode") or "project").lower()
    jd_id = data.get("jdId") or data.get("jd_id") or ""
    if mode == "resume":
        return (
            "【模式：简历深挖】这是候选人的简历。逐条质疑每一个声称的项目与技能，"
            "把简历里的说法和已知的弱点（lookup_weakness）做交叉验证，抓自相矛盾处。"
        )
    if mode == "project":
        return (
            "【模式：项目拷问】这是候选人描述的项目，把它当成被测系统逐项拆解："
            "架构选型、失败模式、trade-off、如果重做会改什么。用 get_followup_chain 深挖技术点。"
        )
    if mode == "knowledge":
        return (
            "【模式：知识点专项】候选人指定要被考的知识点已附在材料里。"
            "若主题命中 get_followup_chain 的列表就直接调用，否则用 search_knowledge 找标准答案再追问。"
        )
    if mode == "jd":
        return (
            f"【模式：JD 面试】针对具体岗位面试。先调用 get_jd(jd_id={jd_id!r}) 拉出岗位要求，"
            "然后逐条技能拷问候选人是否真满足，不满足的要逼问底层原理或项目证据。"
        )
    return "【模式：通用】围绕候选人说的每一句话深挖，绝不轻易放过。"


PERSONA = (
    "你是一位资深、极度严苛的技术面试官。你的任务不是友善聊天，而是用压力测试找出候选人的真实能力天花板——"
    "目标是问到对方破防，但保持专业、不人身攻击。\n\n"
    "行为准则：\n"
    "1. 候选人每答一句，立刻向下追问：为什么 / 具体怎么实现 / 边界情况呢 / 如果 X 怎么办。绝不接受含糊其辞。\n"
    "2. 候选人一旦声称掌握某技术，调用 get_followup_chain(topic) 把它从「我用过」逼到「讲底层原理」。\n"
    "3. 开局就调用 lookup_weakness() 找出候选人自己仓库里的自相矛盾点（例如「从0到1主导」vs「vibe coding 搭的」、"
    "数据量 47/192/242 互相打架），直接点破并要求自圆其说。\n"
    "4. 候选人卡壳或打太极时，下沉到第一性原理并加压；若确实答不上来，记为能力缺口，但继续逼问相关底层。\n"
    "5. 每轮只说 1-3 句话 + 一个尖锐问题，不要长篇大论。一句带压迫感的点评就足够。\n"
    "6. 绝不主动给答案。你的目的是暴露对方不知道的东西。必要时可给一句毫不留情的阶段性判语。\n"
    "7. 在 JD 模式下，对 JD 列出的每一项技能都追问证据；不满足的项要追问『那你拿什么证明你能做』。\n"
)


def _build_instructions(ctx: Any, agent: Agent) -> str:
    data = getattr(ctx, "context", None) or {}
    material = data.get("material") or ""
    header = _mode_block(data)
    block = (
        f"{PERSONA}\n\n{header}\n"
    )
    if material:
        block += f"\n--- 候选人提供的材料 ---\n{material}\n"
    return block


# ========== Agent ==========
agent = Agent(
    name="StrictInterviewer",
    instructions=_build_instructions,
    tools=[lookup_weakness, get_followup_chain, search_knowledge, get_jd],
    model=get_model(),
)


# ========== SSE Helper ==========
def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ========== Event Stream Generator ==========
async def _event_stream(
    message: str,
    session=None,
    context_obj: Any = None,
    cancel_signal: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    result = Runner.run_streamed(agent, input=message, context=context_obj, session=session)

    async for event in result.stream_events():
        if cancel_signal and cancel_signal.is_set():
            break

        if event.type == "raw_response_event" and getattr(event.data, "type", None) == "response.output_text.delta":
            delta = getattr(event.data, "delta", "")
            if delta:
                yield sse_event("text_delta", {"delta": delta})

        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                tool_name = (
                    getattr(event.item, "name", None)
                    or getattr(getattr(event.item, "raw_item", None), "name", None)
                )
                if tool_name:
                    logger.log(f"[stream] tool_called: {tool_name}")
                    yield sse_event("tool_called", {"tool": tool_name})


# ========== Core Handler ==========
async def handler(context: Any) -> AsyncGenerator[str, None]:
    request = context.request
    body = request.body
    message = body.get("message") if isinstance(body, dict) else None

    if not message:
        yield sse_event("error", {"message": "'message' is required"})
        yield sse_event("done", {})
        return

    raw_user_id = ""
    if isinstance(body, dict):
        raw_user_id = body.get("userId") or body.get("user_id") or ""
    user_id = str(raw_user_id).strip() or None

    cid = context.conversation_id
    logger.log(f"[request] cid={cid}, uid={user_id or '-'}, mode={body.get('mode')}, message={message[:50]!r}")

    # First-turn-only user-indexed write so /conversations can list this thread.
    if user_id and cid:
        try:
            existing = await context.store.get_messages(conversation_id=cid, limit=1)
            already_indexed = bool(existing)
        except Exception as e:
            logger.error(f"[user-index] probe failed: {type(e).__name__}: {e}")
            already_indexed = False

        if not already_indexed:
            try:
                await context.store.append_message(
                    conversation_id=cid, role="user", content=message, user_id=user_id
                )
                logger.log(f"[user-index] WROTE first-turn index for user_id={user_id!r}")
            except Exception as e:
                logger.error(f"[user-index] FAILED to write user index: {type(e).__name__}: {e}")

    # Build the material/context object injected into the interviewer's instructions.
    context_obj = {
        "mode": (body.get("mode") or "project"),
        "material": body.get("material") or "",
        "jdId": body.get("jdId") or body.get("jd_id") or "",
    }

    session = context.store.openai_session(cid) if cid else None
    cancel_signal = request.signal
    stopped = False

    try:
        async for frame in _event_stream(message, session, context_obj, cancel_signal):
            if cancel_signal.is_set():
                stopped = True
                break
            yield frame
    except asyncio.CancelledError:
        stopped = True
        logger.log("[stream] cancelled")
    except Exception as e:
        logger.error(f"[stream] error: {type(e).__name__}: {e}")
        detail: Any = str(e)
        status: Any = None
        response = getattr(e, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
            try:
                body_text = response.text if hasattr(response, "text") else None
                if callable(body_text):
                    body_text = body_text()
                if body_text:
                    try:
                        detail = json.loads(body_text)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        detail = body_text
            except Exception:
                pass
        yield sse_event("error", {
            "message": str(e),
            "errorType": type(e).__name__,
            "status": status,
            "detail": detail,
        })
    finally:
        yield sse_event("done", {"stopped": stopped})
