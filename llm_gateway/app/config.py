from functools import lru_cache
import os
from pydantic import BaseModel, Field


class GatewaySettings(BaseModel):
    mode: str = Field(default="mock", description="Gateway running mode: mock or real")
    agent_service_url: str = Field(
        default="http://agent_service:8100",
        description="Base URL for agent service",
    )
    vllm_base_url: str = Field(
        default="http://210.61.209.139:45014/v1/",
        description="OpenAI-compatible endpoint for vLLM",
    )
    vllm_model_id: str = Field(
        default="openai/gpt-oss-120b", description="Model identifier for vLLM"
    )
    vllm_api_key: str = Field(
        default="dummy-key", description="API key for vLLM (use dummy if not required)"
    )

    class Config:
        frozen = True


@lru_cache(maxsize=1)
def get_settings() -> GatewaySettings:
    return GatewaySettings(
        mode=os.getenv("LLM_GATEWAY_MODE", "mock"),
        agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://agent_service:8100"),
        vllm_base_url=os.getenv("VLLM_BASE_URL", "http://210.61.209.139:45014/v1/"),
        vllm_model_id=os.getenv("VLLM_MODEL_ID", "openai/gpt-oss-120b"),
        vllm_api_key=os.getenv("VLLM_API_KEY", "dummy-key"),
    )
