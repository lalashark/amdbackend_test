from __future__ import annotations

from fastapi import APIRouter

from ..agent_service_client import AgentServiceClient
from ..session_store import session_store
from .. import schemas

router = APIRouter(prefix="", tags=["analysis"])
_agent_client = AgentServiceClient()


@router.post("/analyze/document", response_model=schemas.BackendResponse)
async def analyze_document(payload: schemas.AnalyzeRequest) -> schemas.BackendResponse:
    return await _process_request(payload, forced_mode="document")


@router.post("/analyze/code", response_model=schemas.BackendResponse)
async def analyze_code(payload: schemas.AnalyzeRequest) -> schemas.BackendResponse:
    return await _process_request(payload, forced_mode="code")


@router.post("/analyze/error", response_model=schemas.BackendResponse)
async def analyze_error(payload: schemas.AnalyzeRequest) -> schemas.BackendResponse:
    return await _process_request(payload, forced_mode="error")


@router.post("/convert/hipify", response_model=schemas.BackendResponse)
async def convert_hipify(payload: schemas.AnalyzeRequest) -> schemas.BackendResponse:
    return await _process_request(payload, forced_mode="hipify")


@router.post("/lookup/api", response_model=schemas.BackendResponse)
async def lookup_api(payload: schemas.AnalyzeRequest) -> schemas.BackendResponse:
    return await _process_request(payload, forced_mode="api")


async def _process_request(
    payload: schemas.AnalyzeRequest, forced_mode: str
) -> schemas.BackendResponse:
    session_store.create_session(payload.session_id)

    master_request = schemas.MasterRouteRequest(
        text=payload.text,
        session_id=payload.session_id,
        explicit_mode=payload.explicit_mode or forced_mode,
        parallel_modes=payload.parallel_modes or schemas.SUPPORTED_MODES,
        url=payload.url,
    )

    master_response = await _agent_client.route_request(master_request)

    worker_request = schemas.WorkerRequest(
        mode=master_response.mode,
        preprocessed=master_response.preprocessed,
        raw_input=master_response.raw_input,
        session_id=master_response.session_id,
    )
    worker_response = await _agent_client.call_worker(
        master_response.mode, worker_request
    )

    user_entry = {
        "role": "user",
        "text": payload.text,
        "mode": master_response.mode,
    }
    assistant_entry = {
        "role": "assistant",
        "mode": worker_response.mode,
        "result": worker_response.result,
    }
    session_store.append_entry(payload.session_id, user_entry)
    session_store.append_entry(payload.session_id, assistant_entry)

    return schemas.BackendResponse(
        mode=worker_response.mode,
        result=worker_response.result,
        session_id=worker_response.session_id,
        usage=worker_response.usage,
    )
