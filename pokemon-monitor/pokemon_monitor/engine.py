"""The monitor engine: load config, check products on a loop, fire alerts.

Alerting is *edge-triggered*: you only get pinged on the out-of-stock -> in-stock
transition, not on every cycle while it stays in stock. A per-product cooldown
stops a flapping listing (stock bouncing in and out) from spamming you.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import retailers
from .alerts import Alerter, build_all
from .http import PoliteFetcher
from .models import AlertEvent, Product, StockResult

log = logging.getLogger("pokemon_monitor")


@dataclass
class ProductState:
    last_in_stock: bool = False
    # -inf means "never alerted", so the cooldown can never block the first
    # alert (using 0.0 would wrongly gate the first alert near epoch / in tests).
    last_alert_ts: float = float("-inf")


@dataclass
class Engine:
    products: list[Product]
    adapters: dict[str, retailers.Retailer]
    alerters: list[Alerter]
    fetcher: PoliteFetcher
    interval: float = 60.0
    cooldown: float = 600.0  # min seconds between alerts for the same product
    state: dict[str, ProductState] = field(default_factory=dict)
    _clock = time.time

    # -- construction ----------------------------------------------------
    @classmethod
    def from_config(cls, config: dict, fetcher: PoliteFetcher | None = None) -> "Engine":
        products = [Product(**p) for p in config.get("products", [])]
        if not products:
            raise ValueError("config has no products to watch")

        retailer_settings = config.get("retailers", {})
        adapters: dict[str, retailers.Retailer] = {}
        for p in products:
            if p.retailer not in adapters:
                adapters[p.retailer] = retailers.build(
                    p.retailer, retailer_settings.get(p.retailer, {})
                )

        fetcher = fetcher or PoliteFetcher(
            min_interval=config.get("min_request_interval", 3.0),
            respect_robots=config.get("respect_robots", True),
        )
        return cls(
            products=products,
            adapters=adapters,
            alerters=build_all(config),
            fetcher=fetcher,
            interval=config.get("interval_seconds", 60.0),
            cooldown=config.get("alert_cooldown_seconds", 600.0),
        )

    # -- per-product logic ----------------------------------------------
    def _key(self, p: Product) -> str:
        return f"{p.retailer}:{p.sku or p.url}"

    def check_product(self, product: Product) -> StockResult:
        adapter = self.adapters[product.retailer]
        try:
            return adapter.check(product, self.fetcher)
        except Exception as e:  # adapters shouldn't raise, but never trust that
            log.exception("adapter %s crashed", product.retailer)
            return StockResult(product, in_stock=False, error=f"adapter error: {e}")

    def evaluate(self, result: StockResult) -> bool:
        """Decide whether this result should fire an alert, and update state.

        Returns True if an alert should be dispatched. Encapsulates the
        edge-trigger + cooldown rules so it can be unit-tested without network.
        """
        key = self._key(result.product)
        st = self.state.setdefault(key, ProductState())
        now = self._clock()

        worthy = result.should_alert()
        # Edge: was out of stock (or unknown) last time, in stock now.
        is_edge = worthy and not st.last_in_stock
        cooled = (now - st.last_alert_ts) >= self.cooldown

        # Update the remembered stock state. Only treat a clean, successful
        # out-of-stock read as "now out" so a transient error doesn't reset the
        # edge and cause a duplicate alert on the next success.
        if result.ok:
            st.last_in_stock = worthy

        if is_edge and cooled:
            st.last_alert_ts = now
            return True
        return False

    def dispatch(self, result: StockResult) -> None:
        event = AlertEvent(result=result,
                           products_url=result.product.url)
        for alerter in self.alerters:
            try:
                alerter.send(event)
                log.info("alerted via %s: %s", alerter.name, event.title)
            except Exception as e:
                log.error("alert channel %s failed: %s", alerter.name, e)

    # -- main loop -------------------------------------------------------
    def run_once(self) -> list[StockResult]:
        """One pass over all products. Returns every result (for logging/tests)."""
        results = []
        for product in self.products:
            result = self.check_product(product)
            results.append(result)
            if not result.ok:
                log.warning("check failed [%s] %s: %s",
                            product.retailer, product.name, result.error)
                continue
            status = "IN STOCK" if result.in_stock else "out of stock"
            log.info("[%s] %s — %s", product.retailer, product.name, status)
            if self.evaluate(result):
                self.dispatch(result)
        return results

    def run_forever(self) -> None:
        log.info("watching %d product(s) every %.0fs (Ctrl-C to stop)",
                 len(self.products), self.interval)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                log.info("stopped by user")
                return
            time.sleep(self.interval)


def load_config(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)
