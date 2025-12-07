"""Master Agent service orchestrating routing and preprocessing."""
from __future__ import annotations

from typing import List

from .. import schemas
from . import preprocess, rules, scoring


def build_master_response(payload: schemas.MasterRouteRequest) -> schemas.MasterRouteResponse:
    allowed_modes = _normalize_allowed_modes(payload.parallel_modes)

    mode = None
    if payload.explicit_mode and payload.explicit_mode in allowed_modes:
        mode = payload.explicit_mode
    else:
        rule_mode = rules.rule_based_detect(payload)
        if rule_mode in allowed_modes:
            mode = rule_mode

    scores = scoring.compute_scores(payload)
    scored_mode = max(allowed_modes, key=lambda m: scores.get(m, 0))
    mode = mode or scored_mode

    preprocessed = preprocess.preprocess_payload(mode, payload)

    return schemas.MasterRouteResponse(
        mode=mode,
        preprocessed=preprocessed,
        raw_input=payload.text,
        session_id=payload.session_id,
    )


def _normalize_allowed_modes(candidates: List[str] | None) -> List[str]:
    if not candidates:
        return schemas.SUPPORTED_MODES.copy()
    sanitized = [mode for mode in candidates if mode in schemas.SUPPORTED_MODES]
    return sanitized or schemas.SUPPORTED_MODES.copy()
