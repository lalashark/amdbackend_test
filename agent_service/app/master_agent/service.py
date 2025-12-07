"""Service helpers to execute the ADK Master Agent."""
from __future__ import annotations

from .. import schemas
from ..adk_app.master_agent import MasterAgent
from ..adk_app.runner import run_adk_agent

_MASTER_AGENT = MasterAgent()
_APP_NAME = "amdlingo-master"


async def execute_master(payload: schemas.MasterRouteRequest) -> schemas.MasterRouteResponse:
    final_state = await run_adk_agent(
        _MASTER_AGENT,
        session_id=f"{payload.session_id}-master",
        app_name=_APP_NAME,
        state={"master_request": payload.model_dump()},
        user_message=payload.text,
    )
    response_dict = final_state.get("master_response", {})
    if not response_dict:
        response_dict = {
            "mode": "document",
            "preprocessed": {},
            "raw_input": payload.text,
            "session_id": payload.session_id,
        }
    return schemas.MasterRouteResponse.model_validate(response_dict)
