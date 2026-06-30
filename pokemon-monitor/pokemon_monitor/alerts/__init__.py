"""Alert channels.

Each channel takes an AlertEvent and delivers it somewhere. They're built from
config; only the ones you configure are active. A failure in one channel is
logged and swallowed so it can't stop the others from firing.
"""

from __future__ import annotations

from .base import Alerter
from .desktop import DesktopAlerter
from .email import EmailAlerter
from .sms import PushoverAlerter
from .webhook import WebhookAlerter


def build_all(config: dict) -> list[Alerter]:
    """Construct every alert channel that appears (and is enabled) in config."""
    alerts_cfg = config.get("alerts", {})
    out: list[Alerter] = []

    builders = {
        "webhook": WebhookAlerter,
        "email": EmailAlerter,
        "pushover": PushoverAlerter,
        "desktop": DesktopAlerter,
    }
    for key, cls in builders.items():
        cfg = alerts_cfg.get(key)
        if cfg and cfg.get("enabled", True):
            out.append(cls(cfg))
    return out


__all__ = ["Alerter", "WebhookAlerter", "EmailAlerter", "PushoverAlerter",
           "DesktopAlerter", "build_all"]
