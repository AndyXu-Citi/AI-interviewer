"""
History handler — EdgeOne Makers (agents route)
================================================
File path agents/history/index.py is auto-mapped to **POST /history**.

Body:    { "conversation_id": "<uuid>" }
Returns: { "conversation_id": "<uuid>", "messages": Message[] }
"""

from __future__ import annotations

import traceback
from typing import Any

from .._logger import create_logger

logger = create_logger("history")


def _flatten_content(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text"))
            for part in content
            if isinstance(part, dict) and part.get("text")
        )
    if isinstance(content, str):
        return content
    return ""


def _to_message(record: Any) -> tuple[dict, str | None] | None:
    role = getattr(record, "role", None)
    if role not in ("user", "assistant"):
        return None

    metadata = getattr(record, "metadata", None) or {}
    if metadata.get("item_type") not in (None, "message"):
        return None

    sdk_item = getattr(record, "content", None)
    inner = sdk_item.get("content") if isinstance(sdk_item, dict) else sdk_item
    text = _flatten_content(inner)
    if not text:
        return None

    created_at = getattr(record, "created_at", 0) or 0
    message = {
        "id": getattr(record, "message_id", None) or f"{role}-{created_at}",
        "role": role,
        "content": text,
        "timestamp": created_at,
    }
    return message, metadata.get("run_id")


def _merge_assistant_fragments(items: list[tuple[dict, str | None]]) -> list[dict]:
    items.sort(key=lambda pair: pair[0]["timestamp"])
    merged: list[dict] = []
    last_run_id: str | None = None
    for msg, run_id in items:
        same_run_assistant = (
            merged
            and run_id is not None
            and run_id == last_run_id
            and merged[-1]["role"] == "assistant"
            and msg["role"] == "assistant"
        )
        if same_run_assistant:
            merged[-1]["content"] += "\n\n" + msg["content"]
        else:
            merged.append(dict(msg))
            last_run_id = run_id
    return merged


def _dedupe_adjacent(messages: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    for msg in messages:
        prev = deduped[-1] if deduped else None
        if (
            prev is not None
            and prev.get("role") == msg.get("role")
            and prev.get("content") == msg.get("content")
        ):
            continue
        deduped.append(msg)
    return deduped


async def handler(context):
    body = context.request.body or {}
    conversation_id = str(body.get("conversation_id") or "").strip()
    if not conversation_id:
        return {"conversation_id": conversation_id, "messages": []}

    store = context.store
    logger.log(f"get_messages: conversation_id={conversation_id!r}")
    try:
        history = store.get_messages(conversation_id, limit=100, order="asc") or []
        visible = [pair for record in history if (pair := _to_message(record))]
        messages = _dedupe_adjacent(_merge_assistant_fragments(visible))
        logger.log(f"get_messages: {len(history)} raw → {len(messages)} bubbles")
        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        logger.error(f"get_messages failed: {type(e).__name__}: {e}")
        logger.error(f"traceback:\n{traceback.format_exc()}")
        return {"conversation_id": conversation_id, "messages": []}
