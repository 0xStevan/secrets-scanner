"""Base class for retailer adapters."""

from __future__ import annotations

from ..http import FetchError, PoliteFetcher
from ..models import Product, StockResult


class Retailer:
    """Common interface every retailer adapter implements.

    Subclasses override `check`. They should be defensive: a parsing miss or a
    network hiccup must return a StockResult with `error` set, never raise — the
    engine relies on getting a result for every product so one flaky retailer
    can't take the whole loop down.
    """

    name = "base"

    def __init__(self, settings: dict | None = None) -> None:
        self.settings = settings or {}

    def check(self, product: Product, fetcher: PoliteFetcher) -> StockResult:
        raise NotImplementedError

    # Small helper so subclasses get uniform error handling.
    def _safe_get(self, fetcher: PoliteFetcher, url: str,
                  headers: dict | None = None):
        try:
            return fetcher.get(url, headers=headers), None
        except FetchError as e:
            return None, str(e)
