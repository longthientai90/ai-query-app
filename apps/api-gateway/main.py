from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Make apps/agent-core importable as "agent_core".
REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_CORE_DIR = REPO_ROOT / "apps" / "agent-core"
if str(AGENT_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CORE_DIR))

from agent_core import Agent  # noqa: E402
from api_chat import router as chat_router  # noqa: E402


class APIGatewaySettings(BaseSettings):
    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    API_GATEWAY_CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        raw = self.API_GATEWAY_CORS_ORIGINS.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


settings = APIGatewaySettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = Agent()
    try:
        await agent.start()
        app.state.agent = agent
        yield
    finally:
        await agent.stop()


app = FastAPI(title="api-gateway", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.API_GATEWAY_HOST, port=settings.API_GATEWAY_PORT, reload=False)
