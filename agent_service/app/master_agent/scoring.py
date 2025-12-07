"""Scoring functions for Master Agent routing."""
from __future__ import annotations

from typing import Dict

from ..schemas import MasterRouteRequest, SUPPORTED_MODES
from . import rules


def compute_scores(payload: MasterRouteRequest) -> Dict[str, int]:
    text = payload.text
    lowered = text.lower()
    tokens = text.strip().split()

    features = {
        "has_url": rules.detect_explicit_document(payload),
        "has_code_braces": "{" in text and "}" in text,
        "has_semicolon": ";" in text,
        "lines_count": len(text.strip().splitlines()),
        "contains_hip_api": "hip" in lowered,
        "contains_cuda_api": "cuda" in lowered,
        "contains_error": "error" in lowered or "illegal" in lowered,
        "has_stack_trace": "stack" in lowered or "line" in lowered,
        "token_count": len(tokens),
    }

    scores: Dict[str, int] = {mode: 0 for mode in SUPPORTED_MODES}

    scores["document"] += 20 if features["has_url"] else 0
    scores["document"] += 10 if features["contains_hip_api"] else 0
    scores["document"] += 5 if features["lines_count"] > 5 else 0

    scores["code"] += 15 if features["has_code_braces"] else 0
    scores["code"] += 10 if features["has_semicolon"] else 0
    scores["code"] += 20 if features["lines_count"] > 3 else 0

    scores["error"] += 40 if features["contains_error"] else 0
    scores["error"] += 10 if features["has_stack_trace"] else 0

    scores["hipify"] += 50 if features["contains_cuda_api"] else 0
    scores["hipify"] -= 10 if features["contains_hip_api"] else 0

    is_api_like = features["token_count"] == 1 and 0 < len(text.strip()) <= 32
    scores["api"] += 40 if is_api_like else 0

    return scores
