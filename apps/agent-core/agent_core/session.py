from __future__ import annotations

"""In-memory session state for conversation and tool execution traces."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Message:
    """Single chat message with UTC timestamp."""

    role: str
    content: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ToolEvent:
    """Compact audit record of one tool invocation."""

    name: str
    arguments: dict[str, Any]
    result_summary: dict[str, Any]
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AgentSession:
    """Conversation container keyed by session_id."""

    session_id: str
    messages: list[Message] = field(default_factory=list)
    tool_events: list[ToolEvent] = field(default_factory=list)

    def push_user(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))

    def push_assistant(self, content: str) -> None:
        self.messages.append(Message(role="assistant", content=content))

    def push_tool(self, name: str, arguments: dict[str, Any], result_summary: dict[str, Any]) -> None:
        self.tool_events.append(ToolEvent(name=name, arguments=arguments, result_summary=result_summary))

    def trim(self, keep_last_messages: int) -> None:
        """Bound memory usage by keeping only recent messages/events."""
        if keep_last_messages > 0 and len(self.messages) > keep_last_messages:
            self.messages = self.messages[-keep_last_messages:]
        if keep_last_messages > 0 and len(self.tool_events) > keep_last_messages:
            self.tool_events = self.tool_events[-keep_last_messages:]

    def as_chat_context(self, keep_last_messages: int) -> list[dict[str, str]]:
        """Expose session history in LLM-ready chat format."""
        messages = self.messages[-keep_last_messages:] if keep_last_messages > 0 else self.messages
        return [{"role": m.role, "content": m.content} for m in messages]
