"""Email alerter over SMTP (stdlib smtplib).

Works with Gmail (use an App Password, not your account password), Fastmail,
SES SMTP, etc.

Config:
    {
      "host": "smtp.gmail.com", "port": 587, "use_tls": true,
      "username": "you@gmail.com", "password": "app-password",
      "from": "you@gmail.com", "to": ["you@gmail.com"]
    }
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .base import Alerter
from ..models import AlertEvent


class EmailAlerter(Alerter):
    name = "email"

    def send(self, event: AlertEvent) -> None:
        cfg = self.config
        recipients = cfg.get("to") or []
        if isinstance(recipients, str):
            recipients = [recipients]
        if not cfg.get("host") or not recipients:
            raise ValueError("email alert needs 'host' and 'to'")

        msg = EmailMessage()
        msg["Subject"] = f"🟢 In stock: {event.title}"
        msg["From"] = cfg.get("from") or cfg.get("username", "")
        msg["To"] = ", ".join(recipients)
        msg.set_content(event.render_text())

        host = cfg["host"]
        port = int(cfg.get("port", 587))
        with smtplib.SMTP(host, port, timeout=20) as server:
            if cfg.get("use_tls", True):
                server.starttls()
            if cfg.get("username"):
                server.login(cfg["username"], cfg.get("password", ""))
            server.send_message(msg)
