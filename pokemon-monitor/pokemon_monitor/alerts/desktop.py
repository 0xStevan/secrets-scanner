"""Desktop notification alerter.

Cross-platform best-effort using whatever the OS provides, with no third-party
dependency:
  - macOS:   osascript display notification
  - Linux:   notify-send (libnotify)
  - Windows: PowerShell toast via BurntToast-free balloon fallback

If none is available it raises, and the engine logs it (your other channels
still fire).
"""

from __future__ import annotations

import platform
import shutil
import subprocess

from .base import Alerter
from ..models import AlertEvent


class DesktopAlerter(Alerter):
    name = "desktop"

    def send(self, event: AlertEvent) -> None:
        title = f"In stock: {event.title}"
        # Keep the body short — desktop toasts truncate hard.
        r = event.result
        body = r.product.retailer.title()
        if r.price is not None:
            body += f" — ${r.price:.2f}"

        system = platform.system()
        if system == "Darwin":
            script = f'display notification "{body}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=True, timeout=10)
        elif system == "Linux":
            if not shutil.which("notify-send"):
                raise RuntimeError("notify-send not found (install libnotify)")
            subprocess.run(["notify-send", title, body], check=True, timeout=10)
        elif system == "Windows":
            ps = (
                "powershell", "-NoProfile", "-Command",
                f"[void][System.Reflection.Assembly]::LoadWithPartialName("
                f"'System.Windows.Forms');"
                f"$n=New-Object System.Windows.Forms.NotifyIcon;"
                f"$n.Icon=[System.Drawing.SystemIcons]::Information;"
                f"$n.Visible=$true;"
                f"$n.ShowBalloonTip(10000,'{title}','{body}',"
                f"[System.Windows.Forms.ToolTipIcon]::Info)",
            )
            subprocess.run(ps, check=True, timeout=15)
        else:
            raise RuntimeError(f"no desktop notifier for platform {system}")
