"""Bounded real-clock probe, 20 attempts per source revision."""
import asyncio
import inspect
import json
import time

from ordinary_chat_service import Outcome, execute_request
from test_ordinary_chat_service import limits, reply, request

ATTEMPTS = 20


async def probe():
    start = time.monotonic()
    precise_start = time.perf_counter()
    loop = asyncio.get_running_loop()
    trace = {"loop_resolution": loop._clock_resolution, "calls": 0}

    class Fake:
        async def send(self, payload, *, timeout_seconds):
            trace["calls"] += 1
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                trace["cancel_monotonic_ms"] = 1000 * (time.monotonic() - start)
                trace["cancel_perf_counter_ms"] = 1000 * (time.perf_counter() - precise_start)
                return reply(usage={"total_tokens": 7})

    result = await execute_request(request(limits=limits(timeout_seconds=0.01)), transport=Fake())
    return {**trace, "outcome": result.outcome.value, "execution": result.execution.value,
            "text_returned": result.text is not None, "usage_total": result.usage.total_tokens}


if __name__ == "__main__":
    print(time.get_clock_info("monotonic"))
    print(inspect.getsource(asyncio.wait_for))
    print(inspect.getsource(asyncio.Timeout._on_timeout))
    loop_source = inspect.getsource(asyncio.BaseEventLoop._run_once)
    start = loop_source.index("end_time = self.time()")
    print(loop_source[start:loop_source.index("# This is the only place", start)])
    rows = [asyncio.run(probe()) for _ in range(ATTEMPTS)]
    print(json.dumps(rows, indent=2))
    passed = sum(row["outcome"] == Outcome.UNKNOWN_AFTER_START.value and not row["text_returned"]
                 and row["usage_total"] == 7 and row["calls"] == 1 for row in rows)
    print(f"{passed} PASS / {ATTEMPTS - passed} FAIL (planned {ATTEMPTS} attempts)")
    raise SystemExit(passed != ATTEMPTS)
