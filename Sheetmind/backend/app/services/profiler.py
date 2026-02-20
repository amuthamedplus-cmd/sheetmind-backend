"""
Request-level step profiler.

Usage:
    timer = StepTimer()
    timer.start("ai_call")
    result = do_ai_call()
    timer.stop("ai_call")
    print(timer.summary())  # -> {"ai_call": 3210, "total": 3215, ...}
"""

import time
import logging

logger = logging.getLogger(__name__)


class StepTimer:
    """Tracks elapsed time for named steps within a single request."""

    def __init__(self):
        self._start_time = time.perf_counter()
        self._steps: dict[str, dict] = {}
        self._order: list[str] = []

    def start(self, name: str) -> None:
        self._steps[name] = {"start": time.perf_counter(), "end": None, "ms": None}
        if name not in self._order:
            self._order.append(name)

    def stop(self, name: str) -> float:
        """Stop a step timer. Returns elapsed ms."""
        if name not in self._steps:
            return 0.0
        end = time.perf_counter()
        self._steps[name]["end"] = end
        ms = round((end - self._steps[name]["start"]) * 1000, 1)
        self._steps[name]["ms"] = ms
        return ms

    def mark(self, name: str, ms: float) -> None:
        """Manually record a step duration."""
        self._steps[name] = {"start": None, "end": None, "ms": round(ms, 1)}
        if name not in self._order:
            self._order.append(name)

    def summary(self) -> dict:
        """Return ordered dict of step timings + total."""
        total_ms = round((time.perf_counter() - self._start_time) * 1000, 1)
        steps = {}
        for name in self._order:
            ms = self._steps[name]["ms"]
            steps[name] = f"{ms}ms" if ms is not None else "running"

        steps["total"] = f"{total_ms}ms"

        # Add percentage breakdown
        breakdown = {}
        for name in self._order:
            ms = self._steps[name]["ms"]
            if ms is not None and total_ms > 0:
                pct = round((ms / total_ms) * 100, 1)
                breakdown[name] = f"{ms}ms ({pct}%)"
        breakdown["total"] = f"{total_ms}ms (100%)"

        return {"steps": steps, "breakdown": breakdown}

    def log(self, label: str = "Request") -> dict:
        """Log the summary and return it."""
        s = self.summary()
        logger.info(f"[PROFILE] {label}: {s['breakdown']}")
        return s
