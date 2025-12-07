"""ADK Document Worker agent implementation."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing_extensions import override

from .. import schemas
from ..llm_gateway_client import get_llm_client, LLMGatewayClient


class DocumentWorkerAgent(BaseAgent):
    """Document worker implemented using ADK BaseAgent."""

    llm_client: LLMGatewayClient
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, llm_client: LLMGatewayClient | None = None) -> None:
        client = llm_client or get_llm_client()
        super().__init__(
            name="AMDlingoDocumentWorker",
            description="Summarizes AMD technical documents and outputs structured JSON.",
            sub_agents=[],
            llm_client=client,
        )
        self.llm_client = client

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        payload_dict = ctx.session.state.get("worker_request", {})
        worker_request = schemas.WorkerRequest.model_validate(payload_dict)
        document_result = await self.llm_client.generate_document_summary(
            {
                "session_id": worker_request.session_id,
                "preprocessed": worker_request.preprocessed,
                "raw_input": worker_request.raw_input,
            }
        )
        normalized = _normalize_document_result(document_result, worker_request.session_id)
        ctx.session.state["document_result"] = normalized
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"document_result": normalized}),
        )


def _normalize_document_result(result: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Ensure the document JSON adheres to the required schema."""

    def _list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    normalized = {
        "summary": result.get("summary", ""),
        "api_explanations": _list(result.get("api_explanations")),
        "key_points": _list(result.get("key_points")),
        "pitfalls": _list(result.get("pitfalls")),
        "concept_links": _list(result.get("concept_links")),
        "example_code": result.get("example_code", ""),
        "notes": result.get("notes", ""),
        "context_sync_key": result.get("context_sync_key", session_id),
    }
    return normalized
