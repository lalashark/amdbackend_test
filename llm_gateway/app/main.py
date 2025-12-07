from __future__ import annotations

from fastapi import FastAPI, HTTPException, status

from .config import get_settings
from . import mock_logic, schemas
from .document_llm import generate_document_summary

app = FastAPI(title="LLM Gateway")
_settings = get_settings()


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "mode": _settings.mode}


@app.post("/worker/{mode}", response_model=schemas.WorkerResponse)
async def worker_request(mode: str, payload: schemas.WorkerRequest) -> schemas.WorkerResponse:
    if _settings.mode == "mock":
        result = mock_logic.build_worker_result(mode, payload)
        return schemas.WorkerResponse(
            mode=mode,
            result=result,
            session_id=payload.session_id,
            usage={"mock_tokens": 0},
        )

    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="LLM real mode not implemented yet")


@app.post("/llm/document")
async def document_llm(payload: schemas.DocumentLLMRequest) -> dict:
    if _settings.mode == "mock":
        return mock_logic.build_document_llm_output(payload)
    result = await generate_document_summary(payload.model_dump())
    return result
