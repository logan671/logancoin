from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class PricePoint:
    ts: datetime
    price: float


class SymbolPriceBuffer:
    def __init__(self, max_window_seconds: int = 300) -> None:
        self.max_window = timedelta(seconds=max_window_seconds)
        self.points: deque[PricePoint] = deque()

    def add_tick(self, price: float, ts: datetime | None = None) -> None:
        if price <= 0:
            raise ValueError("price must be positive")
        now = ts or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        self.points.append(PricePoint(ts=now, price=price))
        self._trim(now)

    def _trim(self, now: datetime) -> None:
        threshold = now - self.max_window
        while self.points and self.points[0].ts < threshold:
            self.points.popleft()

    def latest(self) -> PricePoint | None:
        return self.points[-1] if self.points else None

    def get_5min_change(self, now: datetime | None = None) -> float | None:
        if len(self.points) < 2:
            return None

        pivot_time = (now or self.points[-1].ts) - timedelta(minutes=5)
        first: PricePoint | None = None
        for point in self.points:
            first = point
            if point.ts >= pivot_time:
                break

        latest = self.points[-1]
        if first is None or first.price <= 0:
            return None

        return (latest.price - first.price) / first.price

    def is_fresh(self, freshness_seconds: float = 3.0, now: datetime | None = None) -> bool:
        if not self.points:
            return False
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        delta = current - self.points[-1].ts
        return delta.total_seconds() <= freshness_seconds

    def get_direction(self, now: datetime | None = None) -> str | None:
        change = self.get_5min_change(now=now)
        if change is None:
            return None
        if change > 0:
            return "up"
        if change < 0:
            return "down"
        return "flat"
