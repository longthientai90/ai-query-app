from __future__ import annotations

"""CLI entrypoint to run a single agent request from terminal."""

import argparse
import asyncio
import json
import sys

from agent_core import Agent


async def _run(question: str, max_rows: int | None, session_id: str | None) -> int:
    # The CLI mirrors API behavior: start once, handle one request, then shutdown.
    agent = Agent()
    try:
        await agent.start()
        result = await agent.handle(question=question, max_rows=max_rows, session_id=session_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        await agent.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="agent-core CLI")
    parser.add_argument("question", type=str, help="User question")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--session-id", type=str, default=None)
    args = parser.parse_args()

    if sys.platform == "win32":
        # Required for compatibility with some async transports on Windows.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_run(question=args.question, max_rows=args.max_rows, session_id=args.session_id))


if __name__ == "__main__":
    raise SystemExit(main())
