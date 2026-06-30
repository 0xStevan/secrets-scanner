"""Discord / Slack incoming-webhook alerter.

Both Discord and Slack accept a JSON POST with a top-level `content` (Discord) or
`text` (Slack) field. We send both keys so a single channel works for either —
the platform ignores the one it doesn't recognise.

Config:
    {"url": "https://discord.com/api/webhooks/..."}
"""

from __future__ import annotations

import json
import urllib.request

from .base import Alerter
from ..models import AlertEvent


class WebhookAlerter(Alerter):
    name = "webhook"

    def send(self, event: AlertEvent) -> None:
        url = self.config.get("url")
        if not url:
            raise ValueError("webhook alert needs a 'url'")
        text = event.render_text()
        payload = json.dumps({"content": text, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=15).close()
