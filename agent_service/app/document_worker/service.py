"""ADK-based Document Worker service."""
from __future__ import annotations

from .. import schemas
from ..adk_app.document_agent import DocumentWorkerAgent
from ..adk_app.runner import run_adk_agent
from ..llm_gateway_client import get_llm_client

_DOCUMENT_AGENT = DocumentWorkerAgent(llm_client=get_llm_client())
_APP_NAME = "amdlingo-document"


async def generate_document_response(payload: schemas.WorkerRequest) -> schemas.WorkerResponse:
    state = {"worker_request": payload.model_dump()}
    final_state = await run_adk_agent(
        _DOCUMENT_AGENT,
        session_id=f"{payload.session_id}-document",
        app_name=_APP_NAME,
        state=state,
        user_message=payload.raw_input,
    )
    result = final_state.get("document_result", _empty_result(payload.session_id))
    return schemas.WorkerResponse(
        mode="document",
        result=result,
        session_id=payload.session_id,
    )


def _empty_result(session_id: str) -> dict:
    return {
        "summary": "",
        "api_explanations": [],
        "key_points": [],
        "pitfalls": [],
        "concept_links": [],
        "example_code": "",
        "notes": "",
        "context_sync_key": session_id,
    }
