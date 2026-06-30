"""Tests for the engine's alert decision logic (edge-trigger + cooldown +
price ceiling) and the fetcher's politeness, all without real network."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pokemon_monitor.engine import Engine, ProductState  # noqa: E402
from pokemon_monitor.http import PoliteFetcher  # noqa: E402
from pokemon_monitor.models import Product, StockResult  # noqa: E402


def make_engine(**kw):
    """An engine with no real adapters/alerters — we only test evaluate()."""
    eng = Engine(
        products=[], adapters={}, alerters=[],
        fetcher=PoliteFetcher(),
        cooldown=kw.get("cooldown", 600.0),
    )
    return eng


class EvaluateLogic(unittest.TestCase):
    def setUp(self):
        self.product = Product("bestbuy", "Box",
                               "https://x/p", sku="1", max_price=100.0)

    def _result(self, in_stock, price=None, error=None):
        return StockResult(self.product, in_stock=in_stock,
                           price=price, error=error)

    def test_edge_fires_once(self):
        eng = make_engine()
        t = [1000.0]
        eng._clock = lambda: t[0]
        # First in-stock read fires.
        self.assertTrue(eng.evaluate(self._result(True, 50)))
        # Still in stock next cycle -> no repeat alert.
        self.assertFalse(eng.evaluate(self._result(True, 50)))

    def test_re_fires_after_restock_cycle(self):
        eng = make_engine(cooldown=0)
        t = [0.0]
        eng._clock = lambda: t[0]
        self.assertTrue(eng.evaluate(self._result(True, 50)))   # in
        self.assertFalse(eng.evaluate(self._result(False)))     # out
        self.assertTrue(eng.evaluate(self._result(True, 50)))   # back in -> fire

    def test_cooldown_blocks_rapid_reflap(self):
        eng = make_engine(cooldown=600)
        t = [0.0]
        eng._clock = lambda: t[0]
        self.assertTrue(eng.evaluate(self._result(True, 50)))
        self.assertFalse(eng.evaluate(self._result(False)))
        t[0] = 60  # only a minute later
        self.assertFalse(eng.evaluate(self._result(True, 50)))  # cooled? no
        t[0] = 700  # past cooldown
        self.assertFalse(eng.evaluate(self._result(True, 50)))  # still in stock
        # need an out->in edge after cooldown
        self.assertFalse(eng.evaluate(self._result(False)))
        self.assertTrue(eng.evaluate(self._result(True, 50)))

    def test_price_ceiling_blocks(self):
        eng = make_engine()
        eng._clock = lambda: 0.0
        # in stock but above max_price (100) -> no alert
        self.assertFalse(eng.evaluate(self._result(True, 250)))

    def test_error_does_not_reset_edge(self):
        eng = make_engine()
        t = [0.0]
        eng._clock = lambda: t[0]
        self.assertTrue(eng.evaluate(self._result(True, 50)))   # fire
        # transient error must NOT clear last_in_stock...
        self.assertFalse(eng.evaluate(self._result(False, error="timeout")))
        # ...so a successful in-stock read right after is NOT a new edge.
        self.assertFalse(eng.evaluate(self._result(True, 50)))


class FetcherPoliteness(unittest.TestCase):
    def test_throttle_waits_between_same_host(self):
        slept = []
        clock = [0.0]
        f = PoliteFetcher(min_interval=3.0,
                          sleep=lambda s: slept.append(s),
                          clock=lambda: clock[0])
        f._throttle("example.com")          # first hit: no wait
        self.assertEqual(slept, [])
        f._throttle("example.com")          # immediate second hit: must wait ~3s
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 3.0)

    def test_robots_disabled_allows_all(self):
        f = PoliteFetcher(respect_robots=False)
        self.assertTrue(f.allowed("https://anything.example/x"))


if __name__ == "__main__":
    unittest.main()
