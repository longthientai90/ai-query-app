from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_core_client import AgentCoreClient
from api_chat import router as chat_router
from telemetry import setup_telemetry

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class APIGatewaySettings(BaseSettings):
    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    API_GATEWAY_CORS_ORIGINS: str = "*"
    AGENT_CORE_BASE_URL: str = "http://127.0.0.1:8100"
    AGENT_CORE_HANDLE_PATH: str = "/agent/handle"
    AGENT_CORE_TIMEOUT_SEC: float = 120.0

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
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
    client = AgentCoreClient(
        base_url=settings.AGENT_CORE_BASE_URL,
        handle_path=settings.AGENT_CORE_HANDLE_PATH,
        timeout_sec=settings.AGENT_CORE_TIMEOUT_SEC,
    )
    app.state.agent_core_client = client
    try:
        yield
    finally:
        await client.close()


app = FastAPI(title="api-gateway", lifespan=lifespan)
setup_telemetry(app=app, service_name="api-gateway")
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
