"""Base class for alert channels."""

from __future__ import annotations

from ..models import AlertEvent


class Alerter:
    name = "base"

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    def send(self, event: AlertEvent) -> None:
        """Deliver the alert. Implementations may raise; the engine catches."""
        raise NotImplementedError
