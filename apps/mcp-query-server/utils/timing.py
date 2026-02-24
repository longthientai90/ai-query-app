from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class TimerResult:
    start: float = 0.0
    end: float = 0.0

    @property
    def ms(self) -> float:
        # If timer is still running, compute elapsed from now.
        if self.end == 0.0:
            return (time.perf_counter() - self.start) * 1000
        return (self.end - self.start) * 1000


@asynccontextmanager
async def timer():
    t = TimerResult(start=time.perf_counter())
    try:
        yield t
    finally:
        t.end = time.perf_counter()
