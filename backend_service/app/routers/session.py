from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..session_store import session_store
from .. import schemas

router = APIRouter(prefix="", tags=["session"])


@router.post("/session/create", response_model=schemas.SessionHistoryResponse)
def create_session(payload: schemas.SessionCreateRequest) -> schemas.SessionHistoryResponse:
    session_store.create_session(payload.session_id)
    return schemas.SessionHistoryResponse(
        session_id=payload.session_id, history=session_store.get_history(payload.session_id)
    )


@router.post("/session/append", response_model=schemas.SessionHistoryResponse)
def append_session(payload: schemas.SessionAppendRequest) -> schemas.SessionHistoryResponse:
    if payload.entry.role == "assistant" and payload.entry.result is None:
        raise HTTPException(status_code=400, detail="assistant entry requires result")
    if payload.entry.role == "user" and payload.entry.text is None:
        raise HTTPException(status_code=400, detail="user entry requires text")

    session_store.append_entry(payload.session_id, payload.entry.model_dump(exclude_none=True))
    return schemas.SessionHistoryResponse(
        session_id=payload.session_id, history=session_store.get_history(payload.session_id)
    )


@router.get("/session/history", response_model=schemas.SessionHistoryResponse)
def get_history(session_id: str = Query(..., description="Session identifier")) -> schemas.SessionHistoryResponse:
    history = session_store.get_history(session_id)
    return schemas.SessionHistoryResponse(session_id=session_id, history=history)
