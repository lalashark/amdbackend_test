from functools import lru_cache
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    agent_service_url: str = Field(
        default="http://agent_service:8100",
        description="Base URL of the agent service",
    )
    agent_service_timeout: float = Field(
        default=30.0,
        description="Timeout (in seconds) for requests to agent service",
    )

    class Config:
        frozen = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""

    defaults = Settings()
    return Settings(
        agent_service_url=os.getenv("AGENT_SERVICE_URL", defaults.agent_service_url),
        agent_service_timeout=float(
            os.getenv("AGENT_SERVICE_TIMEOUT", defaults.agent_service_timeout)
        ),
    )
