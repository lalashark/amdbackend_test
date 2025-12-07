from __future__ import annotations

from fastapi import APIRouter

from ..schemas import MasterRouteRequest, MasterRouteResponse
from ..master_agent import service as master_service

router = APIRouter(prefix="/master", tags=["master"])


@router.post("/route", response_model=MasterRouteResponse)
async def route_payload(payload: MasterRouteRequest) -> MasterRouteResponse:
    return await master_service.execute_master(payload)
