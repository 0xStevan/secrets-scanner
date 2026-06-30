"""Time-of-day polling windows.

Big Pokemon drops cluster in known hours (e.g. Target ~1-5 AM). Polling fast
24/7 is wasteful and raises your block risk; polling slow misses the drop. A
DropWindow lets you poll fast only inside the window and relax the rest of the
day.

Times are interpreted in the configured timezone (or the machine's local time
if none is given). Windows may wrap past midnight (e.g. 23:00 -> 02:00).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

try:  # stdlib since 3.9, but the tz database may be absent on some systems
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


def parse_hhmm(value: str) -> time:
    """Parse 'HH:MM' (24h) into a datetime.time. Raises ValueError if malformed."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"time must be 'HH:MM', got {value!r}")
    hh, mm = int(parts[0]), int(parts[1])
    return time(hour=hh, minute=mm)


@dataclass
class DropWindow:
    start: time
    end: time
    interval: float  # seconds between checks while inside this window

    @classmethod
    def from_dict(cls, d: dict) -> "DropWindow":
        return cls(
            start=parse_hhmm(d["start"]),
            end=parse_hhmm(d["end"]),
            interval=float(d.get("interval_seconds", 20.0)),
        )

    def contains(self, t: time) -> bool:
        """Is wall-clock time `t` inside this window? Handles midnight wrap."""
        if self.start <= self.end:
            return self.start <= t < self.end
        # wraps past midnight: e.g. start 23:00, end 02:00
        return t >= self.start or t < self.end


def resolve_tz(name: str | None):
    """Return a tzinfo for `name`, or None for local time. Never raises."""
    if not name or ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def interval_for(
    windows: list[DropWindow],
    base_interval: float,
    now: datetime,
) -> float:
    """The poll interval to use right now.

    If `now` falls in one or more windows, use the *smallest* (most aggressive)
    matching interval. Otherwise fall back to `base_interval`.
    """
    t = now.time()
    matches = [w.interval for w in windows if w.contains(t)]
    return min(matches) if matches else base_interval
