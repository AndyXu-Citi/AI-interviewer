"""
Conversations handler — EdgeOne Makers (agents route)
=====================================================
File path agents/conversations/index.py is auto-mapped to **POST /conversations**.

Body:    { user_id, limit?, order?, after?, before? }
Returns: { conversations: [...], nextCursor, previousCursor }
"""

from __future__ import annotations

import traceback
from typing import Any

from .._logger import create_logger

logger = create_logger("conversations")

DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 100
TITLE_MAX_LEN = 8


def _clamp_limit(raw: Any) -> int:
    try:
        return max(MIN_LIMIT, min(MAX_LIMIT, int(raw)))
    except (TypeError, ValueError):
        return DEFAULT_LIMIT


def _attr(item: Any, *keys: str) -> Any:
    if isinstance(item, dict):
        for k in keys:
            if item.get(k) is not None:
                return item[k]
        return None
    for k in keys:
        v = getattr(item, k, None)
        if v is not None:
            return v
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _truncate_title(text: str) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= TITLE_MAX_LEN else text[:TITLE_MAX_LEN] + "..."


def _normalize_conversation(item: Any) -> dict | None:
    conv_id = _attr(item, "conversation_id", "conversationId", "id")
    if not conv_id:
        return None
    metadata = _attr(item, "metadata") or {}
    title = None
    preview = None
    if isinstance(metadata, dict):
        title = metadata.get("title") or metadata.get("name") or metadata.get("subject")
        preview = metadata.get("preview") or metadata.get("last_message") or metadata.get("snippet")
    if not title:
        first_message = _attr(item, "first_user_message", "firstUserMessage", "first_message")
        if first_message:
            title = _truncate_title(str(first_message))
    user_id = _attr(item, "user_id", "userId")
    return {
        "id": str(conv_id),
        "title": title or "New chat",
        "preview": str(preview) if preview else None,
        "lastMessageAt": _to_int(_attr(item, "last_message_at", "lastMessageAt", "updated_at")),
        "createdAt": _to_int(_attr(item, "created_at", "createdAt")),
        "userId": str(user_id) if user_id else None,
        "messageCount": _to_int(_attr(item, "message_count", "messageCount")),
    }


def _extract_items(result: Any) -> list:
    if hasattr(result, "items") and isinstance(result.items, list):
        return result.items
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ("items", "conversations", "data", "results"):
            if isinstance(result.get(key), list):
                return result[key]
    return []


def _pick_cursor(result: Any, *keys: str) -> str | None:
    for k in keys:
        value = result.get(k) if isinstance(result, dict) else getattr(result, k, None)
        if isinstance(value, str) and value:
            return value
    return None


def _fill_missing_titles(store: Any, conversations: list[dict]) -> None:
    if not hasattr(store, "get_messages"):
        return
    for conv in conversations:
        if conv["title"] != "New chat":
            continue
        try:
            messages = store.get_messages(conversation_id=conv["id"], limit=5, order="asc") or []
        except Exception as e:
            logger.error(f"failed to fetch first message for {conv['id']}: {e}")
            continue
        for msg in messages:
            if _attr(msg, "role") != "user":
                continue
            text = str(_attr(msg, "content") or "")
            if text.strip():
                conv["title"] = _truncate_title(text)
                break


async def handler(context):
    body = context.request.body or {}
    user_id = str(body.get("user_id") or body.get("userId") or "").strip()
    if not user_id:
        return {"status": "error", "message": "user_id is required", "conversations": []}

    limit = _clamp_limit(body.get("limit", DEFAULT_LIMIT))
    order = "asc" if body.get("order") == "asc" else "desc"
    after = str(body.get("after") or "").strip() or None
    before = str(body.get("before") or "").strip() or None

    store = context.store
    params: dict = {"user_id": user_id, "limit": limit, "order": order}
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    logger.log(f"list_conversations: user_id={user_id!r} limit={limit} order={order}")
    try:
        result = store.list_conversations(**params)
        raw_items = _extract_items(result)
        conversations = [c for item in raw_items if (c := _normalize_conversation(item))]

        seen_ids: set[str] = set()
        deduped: list[dict] = []
        for conv in conversations:
            if conv["id"] in seen_ids:
                continue
            seen_ids.add(conv["id"])
            deduped.append(conv)
        duplicates_dropped = len(conversations) - len(deduped)
        conversations = deduped

        _fill_missing_titles(store, conversations)

        response = {
            "conversations": conversations,
            "nextCursor": _pick_cursor(result, "next_cursor", "nextCursor"),
            "previousCursor": _pick_cursor(result, "previous_cursor", "previousCursor", "prev_cursor", "prevCursor"),
        }
        logger.log(f"list_conversations: returned {len(conversations)} unique ({duplicates_dropped} dropped)")
        return response
    except Exception as e:
        logger.error(f"list_conversations failed: {type(e).__name__}: {e}")
        logger.error(f"traceback:\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e), "conversations": []}
