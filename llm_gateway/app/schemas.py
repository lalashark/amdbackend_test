"""Schemas for llm_gateway."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

SUPPORTED_MODES = ["document", "code", "error", "hipify", "api"]


class MasterRouteRequest(BaseModel):
    text: str
    session_id: str
    explicit_mode: Optional[str] = None
    parallel_modes: List[str] = Field(default_factory=lambda: SUPPORTED_MODES.copy())
    url: Optional[str] = None


class MasterRouteResponse(BaseModel):
    mode: Literal["document", "code", "error", "hipify", "api"]
    preprocessed: Dict[str, Any]
    raw_input: str
    session_id: str


class WorkerRequest(BaseModel):
    mode: str
    preprocessed: Dict[str, Any]
    raw_input: str
    session_id: str


class WorkerResponse(BaseModel):
    mode: str
    result: Dict[str, Any]
    session_id: str
    usage: Optional[Dict[str, Any]] = None


class DocumentLLMRequest(BaseModel):
    session_id: str
    preprocessed: Dict[str, Any]
    raw_input: str
