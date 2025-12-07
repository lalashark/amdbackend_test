"""Mock implementations for llm_gateway modes."""
from __future__ import annotations

from typing import Dict

from . import schemas


def detect_mode(payload: schemas.MasterRouteRequest) -> str:
    if payload.explicit_mode:
        return payload.explicit_mode

    lowered = payload.text.lower()
    if "hiperror" in lowered or "illegal" in lowered:
        return "error"
    if "cuda" in lowered and "hip" not in lowered:
        return "hipify"
    if "__global__" in payload.text or "hiplaunchkernelggl" in lowered:
        return "code"
    if len(payload.text.strip().split()) == 1 and payload.text.strip():
        return "api"
    return "document"


def build_preprocessed(mode: str, payload: schemas.MasterRouteRequest) -> Dict[str, object]:
    if mode == "document":
        return {
            "url": payload.url or "https://rocm.docs.amd.com/mock",
            "title": "Mock Document",
            "api_list": ["hipMemcpy", "hipMalloc"],
            "section_headers": ["Description", "Parameters"],
            "raw_text": payload.text,
            "document_category": "HIP Runtime API",
        }
    if mode == "code":
        return {
            "language": "hip",
            "api_list": ["hipMalloc", "hipMemcpy"],
            "normalized_code": payload.text,
            "issues_found": ["potential boundary issue"],
            "kernel_blocks": ["mock_kernel"],
            "pointer_metadata": {"A": "device", "B": "device"},
        }
    if mode == "error":
        return {
            "error_type": "hipErrorIllegalAddress",
            "error_message": payload.text,
            "likely_api": "hipMemcpyAsync",
            "stack_trace": ["mock.cpp:42"],
            "code_context": "int i = ...;",
            "pointer_metadata": {"A": "device"},
        }
    if mode == "hipify":
        return {
            "original_code": payload.text,
            "hipified_code_static": payload.text.replace("cuda", "hip"),
            "mapping_report": [
                {"from": "cudaMalloc", "to": "hipMalloc"},
                {"from": "cudaMemcpy", "to": "hipMemcpy"},
            ],
            "unconverted_segments": ["<<<grid, block>>>"]
        }
    if mode == "api":
        api_name = payload.text.strip() or "hipMemcpy"
        return {
            "api_name": api_name,
            "metadata": {
                "description": "Mock description",
                "parameters": ["void* dst", "const void* src"],
                "return": "hipError_t",
                "category": "HIP Runtime API",
            },
        }
    return {}


def build_worker_result(mode: str, request: schemas.WorkerRequest) -> Dict[str, object]:
    session_key = request.session_id
    if mode == "document":
        return {
            "summary": "文件重點摘要 (mock)",
            "api_explanations": [
                {
                    "name": "hipMemcpy",
                    "description": "Copies memory between host/device.",
                    "parameters": "dst, src, size, direction",
                    "return": "hipError_t",
                    "common_pitfalls": ["direction mismatch"],
                    "example_code": "hipMemcpy(dst, src, size, hipMemcpyHostToDevice);",
                }
            ],
            "key_points": ["重點 1", "重點 2"],
            "pitfalls": ["注意記憶體方向"],
            "concept_links": ["HIP runtime"],
            "example_code": "// mock example",
            "notes": "mock notes",
            "context_sync_key": session_key,
        }
    if mode == "code":
        return {
            "summary": "此 kernel 執行向量加法 (mock)",
            "issues": [
                {
                    "type": "boundary_error",
                    "description": "缺少 i < N 判斷",
                    "location": "line 10",
                    "severity": "high",
                }
            ],
            "fix_explanation": "加入 boundary check",
            "fixed_code": "if (i < N) { C[i] = A[i] + B[i]; }",
            "optimization_suggestions": ["考慮 shared memory"],
            "api_reference": ["hipLaunchKernelGGL"],
            "context_sync_key": session_key,
        }
    if mode == "error":
        return {
            "error_summary": "hipErrorIllegalAddress (mock)",
            "root_cause": "缺少 boundary check",
            "evidence": ["未檢查 i < N"],
            "fix_steps": ["加入 if (i < N)", "確認指標初始化"],
            "fixed_code": "if (i < N) {...}",
            "risk_analysis": ["不修復會造成非法存取"],
            "related_api_docs": ["hipMemcpy"],
            "context_sync_key": session_key,
        }
    if mode == "hipify":
        return {
            "hip_code_final": request.preprocessed.get("hipified_code_static", ""),
            "hip_code_static": request.preprocessed.get("hipified_code_static", ""),
            "diff_summary": [
                {"type": "api_mapping", "from": "cudaMalloc", "to": "hipMalloc"}
            ],
            "unconverted_notes": [
                {
                    "segment": "<<<grid, block>>>",
                    "status": "manual_port_required",
                    "suggestion": "改用 hipLaunchKernelGGL",
                }
            ],
            "porting_risks": ["請確認 ROCm 是否具備等效 library"],
            "explanation": "mock hipify 說明",
            "context_sync_key": session_key,
        }
    if mode == "api":
        api_name = request.preprocessed.get("api_name", "hipMemcpy")
        return {
            "api_name": api_name,
            "description": "Copies memory (mock)",
            "parameters": request.preprocessed.get("metadata", {}).get("parameters", []),
            "return": "hipError_t",
            "usage": "使用 hipMemcpy 時請選對方向",
            "example_code": "hipMemcpy(dst, src, size, hipMemcpyDeviceToHost);",
            "pitfalls": ["方向錯誤"],
            "related_apis": ["hipMemcpyAsync"],
            "notes": "mock notes",
            "context_sync_key": session_key,
        }
    return {"message": "unsupported mode"}


def build_document_llm_output(payload: schemas.DocumentLLMRequest) -> Dict[str, object]:
    """Reuse worker mock logic to emulate an LLM response for Document mode."""
    worker_request = schemas.WorkerRequest(
        mode="document",
        preprocessed=payload.preprocessed,
        raw_input=payload.raw_input,
        session_id=payload.session_id,
    )
    return build_worker_result("document", worker_request)
