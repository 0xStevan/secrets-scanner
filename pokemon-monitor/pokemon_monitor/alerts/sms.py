"""SMS / phone-push alerter via Pushover.

Pushover (https://pushover.net) delivers push notifications to your phone for a
one-off ~$5 per platform and is far simpler than wiring up Twilio for SMS. If you
specifically need a real text message, point a webhook/email at an SMS gateway;
Pushover covers the "buzz my phone instantly" need that restock alerts actually
want.

Config:
    {"token": "<app token>", "user": "<user key>"}
"""

from __future__ import annotations

import urllib.parse
import urllib.request

from .base import Alerter
from ..models import AlertEvent

API = "https://api.pushover.net/1/messages.json"


class PushoverAlerter(Alerter):
    name = "pushover"

    def send(self, event: AlertEvent) -> None:
        token = self.config.get("token")
        user = self.config.get("user")
        if not token or not user:
            raise ValueError("pushover alert needs 'token' and 'user'")
        data = urllib.parse.urlencode({
            "token": token,
            "user": user,
            "title": f"In stock: {event.title}",
            "message": event.render_text(),
            "url": event.products_url or event.result.product.url,
            "url_title": "Open product",
            "priority": self.config.get("priority", 1),
        }).encode("utf-8")
        req = urllib.request.Request(API, data=data, method="POST")
        urllib.request.urlopen(req, timeout=15).close()
