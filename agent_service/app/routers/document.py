from __future__ import annotations

from fastapi import APIRouter

from ..schemas import WorkerRequest, WorkerResponse
from ..document_worker import service as document_service

router = APIRouter(prefix="/worker", tags=["document"])


@router.post("/document", response_model=WorkerResponse)
async def run_document_worker(payload: WorkerRequest) -> WorkerResponse:
    return await document_service.generate_document_response(payload)
