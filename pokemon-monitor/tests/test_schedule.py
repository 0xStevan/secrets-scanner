"""Tests for drop-window polling logic (no clock dependence — we pass `now`)."""

import os
import sys
import unittest
from datetime import datetime, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pokemon_monitor.schedule import (  # noqa: E402
    DropWindow, interval_for, parse_hhmm,
)


class ParseHHMM(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(parse_hhmm("01:30"), time(1, 30))
        self.assertEqual(parse_hhmm(" 23:05 "), time(23, 5))

    def test_bad(self):
        with self.assertRaises(ValueError):
            parse_hhmm("0130")


class WindowContains(unittest.TestCase):
    def test_normal_window(self):
        w = DropWindow(time(1, 0), time(5, 0), 20)
        self.assertTrue(w.contains(time(3, 0)))
        self.assertTrue(w.contains(time(1, 0)))      # inclusive start
        self.assertFalse(w.contains(time(5, 0)))     # exclusive end
        self.assertFalse(w.contains(time(0, 59)))
        self.assertFalse(w.contains(time(12, 0)))

    def test_midnight_wrap(self):
        w = DropWindow(time(23, 0), time(2, 0), 15)
        self.assertTrue(w.contains(time(23, 30)))
        self.assertTrue(w.contains(time(0, 30)))
        self.assertTrue(w.contains(time(1, 59)))
        self.assertFalse(w.contains(time(2, 0)))
        self.assertFalse(w.contains(time(12, 0)))


class IntervalFor(unittest.TestCase):
    def setUp(self):
        self.windows = [
            DropWindow(time(1, 0), time(5, 0), 20),
            DropWindow(time(2, 0), time(3, 0), 10),  # overlaps, tighter
        ]

    def _at(self, h, m=0):
        return datetime(2026, 6, 30, h, m)

    def test_outside_uses_base(self):
        self.assertEqual(interval_for(self.windows, 300, self._at(12)), 300)

    def test_inside_uses_window(self):
        self.assertEqual(interval_for(self.windows, 300, self._at(4)), 20)

    def test_overlap_picks_tightest(self):
        # 2:30 is inside both windows -> the 10s one wins.
        self.assertEqual(interval_for(self.windows, 300, self._at(2, 30)), 10)

    def test_no_windows_is_base(self):
        self.assertEqual(interval_for([], 300, self._at(3)), 300)


if __name__ == "__main__":
    unittest.main()
