"""Best Buy adapter — uses the official Best Buy Products API.

Best Buy publishes a real API (https://developer.bestbuy.com/), which is by far
the cleanest and most ToS-friendly way to check availability. Get a free API
key and put it in config under retailers.bestbuy.api_key.

Falls back with a clear error if no key is configured rather than scraping the
site, which Best Buy's terms disallow for automated tools.
"""

from __future__ import annotations

import json

from ..http import PoliteFetcher
from ..models import Product, StockResult
from .base import Retailer

API_TMPL = (
    "https://api.bestbuy.com/v1/products(sku={sku})"
    "?apiKey={key}&format=json"
    "&show=sku,name,salePrice,onlineAvailability,inStoreAvailability"
)


def parse(payload: str, product: Product) -> StockResult:
    """Turn a Best Buy API JSON response into a StockResult. Pure / testable."""
    try:
        data = json.loads(payload)
    except (ValueError, TypeError) as e:
        return StockResult(product, in_stock=False, error=f"bad JSON: {e}")

    products = data.get("products") or []
    if not products:
        return StockResult(product, in_stock=False,
                           note="no matching product in API response")
    p = products[0]
    in_stock = bool(p.get("onlineAvailability") or p.get("inStoreAvailability"))
    price = p.get("salePrice")
    return StockResult(
        product,
        in_stock=in_stock,
        price=float(price) if price is not None else None,
        title=p.get("name"),
    )


class BestBuy(Retailer):
    name = "bestbuy"

    def check(self, product: Product, fetcher: PoliteFetcher) -> StockResult:
        key = self.settings.get("api_key")
        if not key:
            return StockResult(
                product, in_stock=False,
                error="Best Buy needs an API key (retailers.bestbuy.api_key). "
                      "Free at https://developer.bestbuy.com/",
            )
        if not product.sku:
            return StockResult(product, in_stock=False,
                               error="Best Buy product needs a numeric `sku`")
        url = API_TMPL.format(sku=product.sku, key=key)
        resp, err = self._safe_get(fetcher, url)
        if err:
            return StockResult(product, in_stock=False, error=err)
        return parse(resp.text, product)
