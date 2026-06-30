"""Pokemon Center adapter — reads schema.org availability from the product page.

The official Pokemon Center store embeds JSON-LD (`<script type=
"application/ld+json">`) with an `offers.availability` field using schema.org
vocabulary ("http://schema.org/InStock" / "OutOfStock"). That's a stable,
intentionally-public signal, which makes this the friendliest source to read.
"""

from __future__ import annotations

import json
import re

from ..http import PoliteFetcher
from ..models import Product, StockResult
from .base import Retailer

_LD_JSON = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _find_offers(obj):
    """Yield every dict that looks like a schema.org Offer."""
    if isinstance(obj, dict):
        if "availability" in obj:
            yield obj
        for v in obj.values():
            yield from _find_offers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _find_offers(v)


def parse(html: str, product: Product) -> StockResult:
    """Pure parser over a Pokemon Center product page's HTML."""
    offers = []
    for block in _LD_JSON.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        offers.extend(_find_offers(data))

    if not offers:
        return StockResult(
            product, in_stock=False,
            note="no JSON-LD availability found (page may have changed)",
        )

    in_stock = False
    price = None
    title = None
    for offer in offers:
        avail = str(offer.get("availability", "")).lower()
        if "instock" in avail or "preorder" in avail:
            in_stock = True
        if price is None and offer.get("price") is not None:
            try:
                price = float(offer["price"])
            except (ValueError, TypeError):
                pass
        title = title or offer.get("name")
    return StockResult(product, in_stock=in_stock, price=price, title=title)


class PokemonCenter(Retailer):
    name = "pokemoncenter"

    def check(self, product: Product, fetcher: PoliteFetcher) -> StockResult:
        if not product.url:
            return StockResult(product, in_stock=False,
                               error="Pokemon Center product needs a `url`")
        resp, err = self._safe_get(fetcher, product.url)
        if err:
            return StockResult(product, in_stock=False, error=err)
        return parse(resp.text, product)
