"""Use cases for conversation thread lifecycle operations."""

from src.state import FoundrySessionPool, SessionPool


async def delete_thread_sessions(
    thread_id: str,
    pool: SessionPool,
    foundry_pool: FoundrySessionPool,
) -> dict[str, str]:
    """Disconnect and clean up a conversation thread from all session pools."""
    await pool.disconnect(thread_id)
    await foundry_pool.disconnect(thread_id)
    return {"status": "deleted", "thread_id": thread_id}


async def abort_thread_session(thread_id: str, pool: SessionPool) -> dict[str, str]:
    """Abort the active request for a conversation thread."""
    aborted = await pool.abort(thread_id)
    return {"status": "aborted" if aborted else "not_found", "thread_id": thread_id}
