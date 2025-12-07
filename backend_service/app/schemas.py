"""Pydantic schemas shared across backend routes."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

SUPPORTED_MODES = ["document", "code", "error", "hipify", "api"]


class AnalyzeRequest(BaseModel):
    text: str
    session_id: str
    explicit_mode: Optional[Literal["document", "code", "error", "hipify", "api"]] = None
    parallel_modes: Optional[List[str]] = Field(default_factory=lambda: SUPPORTED_MODES.copy())
    url: Optional[str] = None


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
    result: Dict[str, Any]
    mode: str
    session_id: str
    usage: Optional[Dict[str, Any]] = None


class BackendResponse(BaseModel):
    mode: str
    result: Dict[str, Any]
    session_id: str
    usage: Optional[Dict[str, Any]] = None


class SessionCreateRequest(BaseModel):
    session_id: str


class SessionAppendEntry(BaseModel):
    role: Literal["user", "assistant"]
    text: Optional[str] = None
    mode: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class SessionAppendRequest(BaseModel):
    session_id: str
    entry: SessionAppendEntry


class SessionHistoryResponse(BaseModel):
    session_id: str
    history: List[Dict[str, Any]]
