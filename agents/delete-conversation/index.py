"""
Delete-conversation handler — EdgeOne Makers (agents route)
==========================================================
File path agents/delete-conversation/index.py is auto-mapped to **POST /delete-conversation**.

Body:    { conversation_id, user_id? }
Returns: { status: "ok", conversation_id }
"""

import traceback

from .._logger import create_logger

logger = create_logger("delete-conversation")


async def handler(context):
    body = context.request.body or {}
    conversation_id = str(body.get("conversation_id") or body.get("conversationId") or "").strip()
    if not conversation_id:
        return {"status": "error", "message": "conversation_id is required"}

    store = context.store
    logger.log(f"delete_conversation: conversation_id={conversation_id!r}")
    try:
        store.delete_conversation(conversation_id=conversation_id)
        logger.log(f"delete_conversation: deleted {conversation_id!r}")
        return {"status": "ok", "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"delete_conversation failed: {type(e).__name__}: {e}")
        logger.error(f"traceback:\n{traceback.format_exc()}")
        return {"status": "error", "conversation_id": conversation_id, "message": str(e)}
