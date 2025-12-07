from functools import lru_cache
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    llm_gateway_url: str = Field(
        default="http://llm_gateway:8001",
        description="LLM gateway base URL",
    )
    llm_gateway_timeout: float = Field(default=10.0)

    class Config:
        frozen = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings()
    return Settings(
        llm_gateway_url=os.getenv("LLM_GATEWAY_URL", defaults.llm_gateway_url),
        llm_gateway_timeout=float(
            os.getenv("LLM_GATEWAY_TIMEOUT", defaults.llm_gateway_timeout)
        ),
    )
