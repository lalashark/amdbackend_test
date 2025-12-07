"""Non-AI preprocessing stubs for Master Agent."""
from __future__ import annotations

from typing import Dict

from ..schemas import MasterRouteRequest
from . import document_fetcher


def preprocess_payload(mode: str, payload: MasterRouteRequest) -> Dict[str, object]:
    text = payload.text
    session_id = payload.session_id

    if mode == "document":
        url = payload.url or _extract_first_url(text) or ""
        fetched = document_fetcher.fetch_document(url) if url else {}
        api_list = fetched.get("api_list") or _extract_api_candidates(text)
        return {
            "url": url,
            "title": fetched.get("title") or "Untitled Document",
            "api_list": api_list,
            "section_headers": fetched.get("section_headers") or ["Description", "Usage"],
            "raw_text": fetched.get("raw_text") or text,
            "document_category": fetched.get("document_category") or "HIP Runtime API",
            "section_contents": fetched.get("section_contents", {}),
        }
    if mode == "code":
        return {
            "language": _guess_language(text),
            "api_list": _extract_api_candidates(text),
            "normalized_code": text.strip(),
            "issues_found": [],
            "kernel_blocks": _detect_kernel_names(text),
            "pointer_metadata": {},
        }
    if mode == "error":
        return {
            "error_type": _detect_error_type(text),
            "error_message": text,
            "likely_api": _detect_likely_api(text),
            "stack_trace": _extract_stack_trace(text),
            "code_context": "",
            "pointer_metadata": {},
        }
    if mode == "hipify":
        return {
            "original_code": text,
            "hipified_code_static": text.replace("cuda", "hip"),
            "mapping_report": _build_mapping_report(text),
            "unconverted_segments": _detect_unconverted_segments(text),
        }
    if mode == "api":
        api_name = text.strip()
        return {
            "api_name": api_name,
            "metadata": {
                "description": "",
                "parameters": [],
                "return": "",
                "category": "",
            },
        }
    return {"raw": text, "session_id": session_id}


def _extract_first_url(text: str) -> str:
    for token in text.split():
        if token.startswith("http://") or token.startswith("https://"):
            return token
    return ""


def _extract_api_candidates(text: str) -> list[str]:
    tokens = [token.strip(";(),") for token in text.split()]
    return [token for token in tokens if token.startswith("hip") or token.startswith("cuda")]


def _guess_language(text: str) -> str:
    if "__global__" in text or "hipLaunchKernelGGL" in text:
        return "hip"
    if "__device__" in text:
        return "cuda"
    return "c++"


def _detect_kernel_names(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("__global__"):
            parts = line.split()
            if len(parts) >= 3:
                result.append(parts[2].split("(")[0])
    return result


def _detect_error_type(text: str) -> str:
    for word in text.split():
        if word.startswith("hipError"):
            return word
    if "illegal" in text.lower():
        return "hipErrorIllegalAddress"
    return "unknown"


def _detect_likely_api(text: str) -> str:
    for token in text.split():
        if token.startswith("hip"):
            return token
    return "hipMemcpy"


def _extract_stack_trace(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if ":" in line and line.strip().startswith("at"):
            lines.append(line.strip())
    return lines[:5]


def _build_mapping_report(text: str) -> list[dict[str, str]]:
    report = []
    if "cudaMalloc" in text:
        report.append({"from": "cudaMalloc", "to": "hipMalloc"})
    if "cudaMemcpy" in text:
        report.append({"from": "cudaMemcpy", "to": "hipMemcpy"})
    return report


def _detect_unconverted_segments(text: str) -> list[str]:
    segments = []
    if "<<<" in text and ">>>" in text:
        segments.append("<<<grid, block>>>")
    return segments
