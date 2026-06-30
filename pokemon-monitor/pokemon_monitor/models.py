"""Core data structures shared across the monitor.

Kept deliberately small and dependency-free (stdlib dataclasses only) so the
retailer adapters and alert channels can pass these around without coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    """A single thing we are watching.

    `sku` means different things per retailer (Best Buy SKU, Target TCIN,
    Walmart item id) — each adapter knows how to interpret it. It's optional
    because some adapters work straight off the product `url`.
    """

    retailer: str
    name: str
    url: str
    sku: str | None = None
    max_price: float | None = None  # don't alert above this price; None = any

    def __post_init__(self) -> None:
        self.retailer = self.retailer.strip().lower()
        if not self.url and not self.sku:
            raise ValueError(f"Product '{self.name}' needs a url or a sku")


@dataclass
class StockResult:
    """The outcome of checking one product once."""

    product: Product
    in_stock: bool
    price: float | None = None
    title: str | None = None
    note: str = ""  # human-readable detail, e.g. why a check was inconclusive
    error: str | None = None  # set when the check failed (network/parse)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def within_budget(self) -> bool:
        """True if there's no price cap, no known price, or price <= cap."""
        if self.product.max_price is None or self.price is None:
            return True
        return self.price <= self.product.max_price

    def should_alert(self) -> bool:
        """A single check is alert-worthy only if it succeeded, the item is in
        stock, and the price (if known) is within the configured ceiling.

        Edge-triggering (only alert on the out->in transition) is handled by
        the engine, not here — this is just the per-check gate.
        """
        return self.ok and self.in_stock and self.within_budget


@dataclass
class AlertEvent:
    """What gets handed to every alert channel when stock is found."""

    result: StockResult
    products_url: str = ""  # convenience: direct buy link (defaults to product url)
    extra: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        r = self.result
        return r.title or r.product.name

    def render_text(self) -> str:
        r = self.result
        lines = [f"🟢 IN STOCK: {self.title}"]
        lines.append(f"Retailer: {r.product.retailer.title()}")
        if r.price is not None:
            lines.append(f"Price: ${r.price:.2f}")
        link = self.products_url or r.product.url
        if link:
            lines.append(f"Buy: {link}")
        if r.note:
            lines.append(r.note)
        lines.append("")
        lines.append("Reminder: complete the purchase yourself. This monitor "
                     "does not buy anything automatically.")
        return "\n".join(lines)
