from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from service_schema.api.router import router
from service_schema.runtime import ServiceSchemaRuntime
from telemetry import setup_telemetry

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.SERVICE_SCHEMA_LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = ServiceSchemaRuntime(settings)
    await runtime.start()
    app.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(title="service-schema", lifespan=lifespan)
_configure_logging()
setup_telemetry(app=app, service_name="service-schema")
app.include_router(router)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVICE_SCHEMA_HOST,
        port=settings.SERVICE_SCHEMA_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
