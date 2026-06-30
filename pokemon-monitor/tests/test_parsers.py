"""Tests for the retailer response parsers (pure, no network)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pokemon_monitor.models import Product  # noqa: E402
from pokemon_monitor.retailers import bestbuy, pokemoncenter, target, walmart  # noqa: E402


def _p(retailer, **kw):
    kw.setdefault("name", "Test")
    kw.setdefault("url", "https://example.com/p")
    return Product(retailer=retailer, **kw)


class BestBuyParse(unittest.TestCase):
    def test_in_stock(self):
        payload = (
            '{"products":[{"sku":1,"name":"Box","salePrice":159.99,'
            '"onlineAvailability":true,"inStoreAvailability":false}]}'
        )
        r = bestbuy.parse(payload, _p("bestbuy", sku="1"))
        self.assertTrue(r.in_stock)
        self.assertEqual(r.price, 159.99)
        self.assertEqual(r.title, "Box")

    def test_out_of_stock(self):
        payload = ('{"products":[{"name":"Box","salePrice":10,'
                   '"onlineAvailability":false,"inStoreAvailability":false}]}')
        r = bestbuy.parse(payload, _p("bestbuy", sku="1"))
        self.assertFalse(r.in_stock)

    def test_empty(self):
        r = bestbuy.parse('{"products":[]}', _p("bestbuy", sku="1"))
        self.assertFalse(r.in_stock)
        self.assertIn("no matching", r.note)

    def test_bad_json(self):
        r = bestbuy.parse("not json", _p("bestbuy", sku="1"))
        self.assertIsNotNone(r.error)


class TargetParse(unittest.TestCase):
    def test_in_stock_nested(self):
        payload = ('{"data":{"product":{"fulfillment":'
                   '{"shipping_options":{"availability_status":"IN_STOCK"}}}}}')
        r = target.parse(payload, _p("target", sku="1"))
        self.assertTrue(r.in_stock)

    def test_out_of_stock(self):
        payload = ('{"data":{"x":{"availability_status":"OUT_OF_STOCK"}}}')
        r = target.parse(payload, _p("target", sku="1"))
        self.assertFalse(r.in_stock)

    def test_no_field(self):
        r = target.parse('{"data":{}}', _p("target", sku="1"))
        self.assertFalse(r.in_stock)
        self.assertIn("no availability", r.note)


class WalmartParse(unittest.TestCase):
    def test_in_stock(self):
        html = '<html>...{"availabilityStatus":"IN_STOCK","price":129.0}...'
        r = walmart.parse(html, _p("walmart"))
        self.assertTrue(r.in_stock)
        self.assertEqual(r.price, 129.0)

    def test_out_of_stock(self):
        html = '<html>{"availabilityStatus":"OUT_OF_STOCK"}</html>'
        r = walmart.parse(html, _p("walmart"))
        self.assertFalse(r.in_stock)

    def test_challenge_page(self):
        r = walmart.parse("<html>Robot check</html>", _p("walmart"))
        self.assertFalse(r.in_stock)
        self.assertIn("no availabilityStatus", r.note)


class PokemonCenterParse(unittest.TestCase):
    def test_in_stock(self):
        html = (
            '<script type="application/ld+json">'
            '{"@type":"Product","name":"X","offers":'
            '{"availability":"http://schema.org/InStock","price":"39.99"}}'
            '</script>'
        )
        r = pokemoncenter.parse(html, _p("pokemoncenter"))
        self.assertTrue(r.in_stock)
        self.assertEqual(r.price, 39.99)

    def test_out_of_stock(self):
        html = (
            '<script type="application/ld+json">'
            '{"offers":{"availability":"http://schema.org/OutOfStock"}}'
            '</script>'
        )
        r = pokemoncenter.parse(html, _p("pokemoncenter"))
        self.assertFalse(r.in_stock)

    def test_no_ld(self):
        r = pokemoncenter.parse("<html>nothing</html>", _p("pokemoncenter"))
        self.assertFalse(r.in_stock)
        self.assertIn("no JSON-LD", r.note)


if __name__ == "__main__":
    unittest.main()
