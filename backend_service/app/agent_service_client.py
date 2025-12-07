"""HTTP client for interacting with agent service."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from .config import get_settings
from . import schemas


class AgentServiceClient:
    """Simple wrapper around agent service HTTP API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.agent_service_url.rstrip("/")
        self._timeout = settings.agent_service_timeout

    async def route_request(
        self, payload: schemas.MasterRouteRequest
    ) -> schemas.MasterRouteResponse:
        response_data = await self._post("/master/route", payload.model_dump(exclude_none=True))
        return schemas.MasterRouteResponse.model_validate(response_data)

    async def call_worker(
        self, mode: str, payload: schemas.WorkerRequest
    ) -> schemas.WorkerResponse:
        response_data = await self._post(
            f"/worker/{mode}", payload.model_dump(exclude_none=True)
        )
        return schemas.WorkerResponse.model_validate(response_data)

    async def _post(self, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=json_payload)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach agent service: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"agent service error: {exc.response.text}",
            ) from exc


def get_agent_service_client() -> AgentServiceClient:
    return AgentServiceClient()
