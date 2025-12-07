"""ADK Master Agent implementation."""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing_extensions import override

from .. import schemas
from ..master_agent import logic


class MasterAgent(BaseAgent):
    """Deterministic routing agent implemented with ADK."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self) -> None:
        super().__init__(
            name="AMDlingoMasterAgent",
            description="Routes AMDlingo requests to the correct worker mode",
            sub_agents=[],
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        request_dict = ctx.session.state.get("master_request", {})
        master_request = schemas.MasterRouteRequest.model_validate(request_dict)
        response = logic.build_master_response(master_request)
        response_dict = response.model_dump()
        ctx.session.state["master_response"] = response_dict
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"master_response": response_dict}),
        )
