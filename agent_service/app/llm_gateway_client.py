"""Client for calling llm_gateway from agent service."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from .config import get_settings


class LLMGatewayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.llm_gateway_url.rstrip("/")
        self._timeout = settings.llm_gateway_timeout

    async def call_worker(self, mode: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"/worker/{mode}", payload)

    async def generate_document_summary(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._post("/llm/document", payload)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc


def get_llm_client() -> LLMGatewayClient:
    return LLMGatewayClient()
