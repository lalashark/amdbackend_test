"""Utilities for executing ADK agents per HTTP request."""
from __future__ import annotations

from typing import Any, Dict

from google.adk.agents import BaseAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

DEFAULT_USER_ID = "amdlingo_user"


async def run_adk_agent(
    agent: BaseAgent,
    *,
    session_id: str,
    app_name: str,
    state: Dict[str, Any],
    user_message: str,
) -> Dict[str, Any]:
    """Execute an ADK agent once and return the final session state."""

    runner = InMemoryRunner(agent=agent, app_name=app_name)
    session_service = runner.session_service

    # Clean up any existing session with same ID (best-effort)
    try:
        await session_service.delete_session(
            app_name=app_name, user_id=DEFAULT_USER_ID, session_id=session_id
        )
    except Exception:
        pass

    await session_service.create_session(
        app_name=app_name,
        user_id=DEFAULT_USER_ID,
        session_id=session_id,
        state=state,
    )

    content = types.Content(role="user", parts=[types.Part(text=user_message or "")])
    async for _ in runner.run_async(
        user_id=DEFAULT_USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        # Drain events; state updates are persisted in the session service.
        pass

    session = await session_service.get_session(
        app_name=app_name, user_id=DEFAULT_USER_ID, session_id=session_id
    )
    final_state = session.state if session else {}

    # Cleanup to keep the in-memory store small.
    await session_service.delete_session(
        app_name=app_name, user_id=DEFAULT_USER_ID, session_id=session_id
    )
    return final_state
