"""Target adapter — queries Target's RedSky fulfillment endpoint.

Target's website is backed by the public-facing "RedSky" aggregation API. It
takes a product's TCIN (the numeric id in the product URL) plus a store id and
returns fulfillment/availability JSON. The web `api_key` it uses is a public
client key shipped to every browser; set it under retailers.target.api_key and
your nearest store id under retailers.target.store_id.

This endpoint changes shape from time to time. The parser below is defensive and
scans the response for any availability_status field, so a minor schema shuffle
degrades to a clear "inconclusive" note rather than a crash.
"""

from __future__ import annotations

import json

from ..http import PoliteFetcher
from ..models import Product, StockResult
from .base import Retailer

ENDPOINT = (
    "https://redsky.target.com/redsky_aggregations/v1/web/"
    "pdp_fulfillment_v1?key={key}&tcin={tcin}"
    "&store_id={store}&zip={zip}&state={state}&pricing_store_id={store}"
)

IN_STOCK_STATUSES = {"IN_STOCK", "LIMITED_STOCK", "PRE_ORDER_SELLABLE"}


def _walk(obj):
    """Yield every dict nested anywhere inside a JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def parse(payload: str, product: Product) -> StockResult:
    """Pure parser over a RedSky fulfillment response."""
    try:
        data = json.loads(payload)
    except (ValueError, TypeError) as e:
        return StockResult(product, in_stock=False, error=f"bad JSON: {e}")

    statuses: list[str] = []
    price = None
    for node in _walk(data):
        for field in ("availability_status", "availabilityStatus"):
            val = node.get(field)
            if isinstance(val, str):
                statuses.append(val.upper())
        # best-effort price pickup
        if price is None:
            cp = node.get("current_retail") or node.get("formatted_current_price")
            if isinstance(cp, (int, float)):
                price = float(cp)

    if not statuses:
        return StockResult(
            product, in_stock=False,
            note="no availability field found (endpoint schema may have changed)",
        )
    in_stock = any(s in IN_STOCK_STATUSES for s in statuses)
    return StockResult(product, in_stock=in_stock, price=price)


class Target(Retailer):
    name = "target"

    def check(self, product: Product, fetcher: PoliteFetcher) -> StockResult:
        key = self.settings.get("api_key")
        store = self.settings.get("store_id")
        if not key or not store:
            return StockResult(
                product, in_stock=False,
                error="Target needs retailers.target.api_key and store_id "
                      "(see the README for how to find them)",
            )
        if not product.sku:
            return StockResult(product, in_stock=False,
                               error="Target product needs a `sku` (the TCIN)")
        url = ENDPOINT.format(
            key=key, tcin=product.sku, store=store,
            zip=self.settings.get("zip", ""),
            state=self.settings.get("state", ""),
        )
        resp, err = self._safe_get(fetcher, url)
        if err:
            return StockResult(product, in_stock=False, error=err)
        return parse(resp.text, product)
