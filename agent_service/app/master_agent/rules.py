"""Rule-based routing heuristics for Master Agent."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from .. import schemas

CODE_KEYWORDS = ["__global__", "hipLaunchKernelGGL", "__device__", "threadIdx"]
ERROR_KEYWORDS = ["hipError", "illegal", "stack trace", "segmentation"]
HIPIFY_KEYWORDS = ["cudaMalloc", "cudaMemcpy", "<<<", "cudaError"]
API_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,32}$")
URL_PATTERN = re.compile(r"https?://[\w./-]+", re.IGNORECASE)


def detect_explicit_document(payload: schemas.MasterRouteRequest) -> bool:
    if payload.url:
        return True
    if URL_PATTERN.search(payload.text):
        return True
    return False


def rule_based_detect(payload: schemas.MasterRouteRequest) -> Optional[str]:
    text = payload.text
    lowered = text.lower()

    if detect_explicit_document(payload):
        return "document"

    if any(keyword in text for keyword in CODE_KEYWORDS):
        return "code"

    if any(keyword.lower() in lowered for keyword in ERROR_KEYWORDS):
        return "error"

    if any(keyword.lower() in lowered for keyword in HIPIFY_KEYWORDS):
        return "hipify"

    tokenized = text.strip().split()
    if len(tokenized) == 1 and API_PATTERN.match(tokenized[0]):
        return "api"

    return None
