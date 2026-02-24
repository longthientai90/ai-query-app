from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from chat_service import ChatService, ChatServiceError
from mcp_service import MCPService, MCPServiceError
from schemas import ChatRequest

router = APIRouter()


def get_mcp_service(request: Request) -> MCPService:
    service: MCPService | None = getattr(request.app.state, "mcp_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="MCP service is not ready")
    return service


def get_chat_service(request: Request) -> ChatService:
    service: ChatService | None = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="Chat service is not ready")
    return service


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> dict:
    mcp_service = get_mcp_service(request)
    chat_service = get_chat_service(request)
    try:
        return await chat_service.ask(
            mcp_service=mcp_service,
            question=payload.question,
            max_rows=payload.max_rows,
        )
    except MCPServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ChatServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON from Azure OpenAI: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {exc}") from exc

