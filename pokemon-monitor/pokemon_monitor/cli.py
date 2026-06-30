"""Command-line entry point for the Pokemon stock monitor.

Usage:
    python -m pokemon_monitor --config config.json          # watch forever
    python -m pokemon_monitor --config config.json --once   # single pass
"""

from __future__ import annotations

import argparse
import logging
import sys

from .engine import Engine, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pokemon-monitor",
        description="Watch retailers for Pokemon restocks and alert you. "
                    "Does NOT auto-purchase — you complete checkout yourself.",
    )
    parser.add_argument("--config", "-c", required=True,
                        help="Path to config JSON (see config.example.json)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single check pass and exit")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Debug-level logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        config = load_config(args.config)
        engine = Engine.from_config(config)
    except (OSError, ValueError, KeyError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    if not engine.alerters:
        print("Warning: no alert channels enabled — you won't be notified.",
              file=sys.stderr)

    if args.once:
        results = engine.run_once()
        found = sum(1 for r in results if r.should_alert())
        print(f"Checked {len(results)} product(s); {found} in stock.")
        return 0

    engine.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
