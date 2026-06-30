"""Retailer adapters.

Each adapter knows how to ask one retailer "is this in stock?" and turn the
answer into a StockResult. Register new ones in REGISTRY so the engine can pick
them by the product's `retailer` field.
"""

from __future__ import annotations

from .base import Retailer
from .bestbuy import BestBuy
from .pokemoncenter import PokemonCenter
from .target import Target
from .walmart import Walmart

REGISTRY: dict[str, type[Retailer]] = {
    "bestbuy": BestBuy,
    "target": Target,
    "walmart": Walmart,
    "pokemoncenter": PokemonCenter,
}


def build(name: str, settings: dict) -> Retailer:
    """Instantiate the adapter registered under `name`."""
    key = name.strip().lower()
    if key not in REGISTRY:
        raise KeyError(
            f"unknown retailer '{name}'. Known: {', '.join(sorted(REGISTRY))}"
        )
    return REGISTRY[key](settings)


__all__ = ["Retailer", "BestBuy", "Target", "Walmart", "PokemonCenter",
           "REGISTRY", "build"]
