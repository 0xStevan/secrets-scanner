"""Walmart adapter — reads the availability flag embedded in the product page.

Walmart renders product pages with a big `__NEXT_DATA__` JSON blob that contains
an `availabilityStatus` field ("IN_STOCK" / "OUT_OF_STOCK"). We fetch the page
(politely, honouring robots.txt) and read that field instead of trying to drive
the live UI.

Walmart aggressively bot-detects; expect this to occasionally return an
inconclusive result when served a challenge page. That's handled gracefully —
it just means "couldn't tell this round", not a crash.
"""

from __future__ import annotations

import json
import re

from ..http import PoliteFetcher
from ..models import Product, StockResult
from .base import Retailer

_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
# Fallback: find the raw availabilityStatus token even if JSON shape shifts.
_AVAIL_TOKEN = re.compile(r'"availabilityStatus"\s*:\s*"([A-Z_]+)"')
_PRICE_TOKEN = re.compile(r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)')


def parse(html: str, product: Product) -> StockResult:
    """Pure parser over a Walmart product page's HTML."""
    statuses = _AVAIL_TOKEN.findall(html)

    # If the embedded JSON parses, prefer a price from it; otherwise regex.
    price = None
    m = _NEXT_DATA.search(html)
    if m:
        try:
            json.loads(m.group(1))  # validate it's real JSON; tolerate failure
        except ValueError:
            pass
    pm = _PRICE_TOKEN.search(html)
    if pm:
        try:
            price = float(pm.group(1))
        except ValueError:
            price = None

    if not statuses:
        return StockResult(
            product, in_stock=False,
            note="no availabilityStatus found (bot challenge or page changed)",
        )
    in_stock = any(s == "IN_STOCK" for s in statuses)
    return StockResult(product, in_stock=in_stock, price=price)


class Walmart(Retailer):
    name = "walmart"

    def check(self, product: Product, fetcher: PoliteFetcher) -> StockResult:
        if not product.url:
            return StockResult(product, in_stock=False,
                               error="Walmart product needs a `url`")
        resp, err = self._safe_get(fetcher, product.url)
        if err:
            return StockResult(product, in_stock=False, error=err)
        return parse(resp.text, product)
