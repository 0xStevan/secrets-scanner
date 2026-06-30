# Pokemon Market Monitor

A polite **stock / restock monitor** for Pokemon products at Target, Walmart,
Best Buy, and the official Pokemon Center. When something you're watching comes
back in stock, it **pings you instantly with a direct buy link** so you can grab
it yourself.

> ### What this does *not* do — and why
>
> It does **not** auto-checkout and it never touches your credit card.
>
> An auto-buying bot would violate every one of these retailers' Terms of
> Service (they all prohibit automated ordering and actively defeat it), risk
> permanent account/order bans, and run into bot-purchasing laws that are
> expanding from tickets into retail. Storing your card to fire unattended
> purchases is also a serious security risk on its own.
>
> So this tool stops at the alert. You get notified the second stock appears and
> complete the purchase with a couple of taps — ~90% of the benefit, none of the
> ToS/legal/security downside.

It is **zero-dependency** (Python 3.9+ standard library only), matching the rest
of this repo.

---

## How it works

```
products (config)  ──►  retailer adapter  ──►  StockResult
                                                   │
                                   edge-trigger + cooldown + price ceiling
                                                   │
                                                   ▼
                              alert channels (Discord/Slack, email, push, desktop)
```

- **Edge-triggered:** you're alerted only on the *out-of-stock → in-stock*
  transition, not every cycle while it stays available.
- **Cooldown:** a flapping listing (stock bouncing in and out) can't spam you.
- **Price ceiling:** set `max_price` per product to skip scalper-priced alerts.
- **Polite by design:** identifiable User-Agent, honours `robots.txt`,
  per-host rate limiting, exponential-backoff retries. This keeps you off
  block lists and is the responsible way to read public pages.

## Quick start

```bash
cd pokemon-monitor
cp config.example.json config.json     # then edit config.json (see below)
python3 -m pokemon_monitor --config config.json --once   # one test pass
python3 -m pokemon_monitor --config config.json          # watch forever
```

> ⚠️ `config.json` holds API keys / SMTP passwords / webhook URLs. It's
> git-ignored — keep it that way. Never commit your real config.

## Configuration

See [`config.example.json`](config.example.json). Top-level knobs:

| Key | Meaning | Default |
|---|---|---|
| `interval_seconds` | seconds between full check passes | 60 |
| `min_request_interval` | min seconds between requests to one host | 3.0 |
| `respect_robots` | honour robots.txt | true |
| `alert_cooldown_seconds` | min gap between alerts for one product | 600 |

### Retailers

Add products under `"products"`, each with a `retailer`, `name`, `url`, optional
`sku`, and optional `max_price`.

- **Best Buy** — uses the **official** [Best Buy Products API](https://developer.bestbuy.com/).
  Get a free API key, put it in `retailers.bestbuy.api_key`, and set each
  product's `sku` to the Best Buy SKU (the number in the product URL). This is
  the cleanest, most ToS-friendly source.
- **Target** — queries Target's RedSky fulfillment endpoint. Needs
  `retailers.target.api_key` (the public web client key Target ships to every
  browser — find it in the network tab of a Target product page request) and a
  `store_id`. Each product's `sku` is its **TCIN** (the number in the URL).
- **Walmart** — reads the `availabilityStatus` field embedded in the product
  page. Just set each product's `url`. Walmart bot-detects aggressively, so
  expect the occasional inconclusive cycle (handled gracefully).
- **Pokemon Center** — reads the schema.org JSON-LD availability from the
  product page. Set each product's `url`.

### Alerts

Enable any combination under `"alerts"`. All you enable fire together; a failure
in one channel never stops the others.

| Channel | Config keys | Notes |
|---|---|---|
| `webhook` | `url` | Discord **or** Slack incoming webhook |
| `email` | `host`, `port`, `use_tls`, `username`, `password`, `from`, `to` | Gmail needs an [App Password](https://support.google.com/accounts/answer/185833) |
| `pushover` | `token`, `user` | Phone push via [Pushover](https://pushover.net) |
| `desktop` | — | macOS `osascript` / Linux `notify-send` / Windows toast |

> **SMS note:** for "buzz my phone instantly", Pushover is simpler and cheaper
> than a Twilio SMS pipeline. If you truly need a text, point the `email` or
> `webhook` channel at an SMS gateway.

## Running it continuously

- **cron / Task Scheduler:** run with `--once` on a schedule.
- **systemd / launchd / a small VPS / Raspberry Pi:** run without `--once` so it
  loops in-process.
- Keep `interval_seconds` reasonable (≥ 30–60s). Faster polling won't beat the
  retailers' own anti-bot queueing and just raises your block risk.

## Testing

```bash
cd pokemon-monitor
python3 -m unittest discover -s tests -v
```

The parsers and the alert-decision logic (edge-trigger, cooldown, price ceiling,
error handling) are covered without any network access.

## Extending

- **New retailer:** add an adapter in `pokemon_monitor/retailers/` subclassing
  `Retailer`, implement `check()` (and a pure `parse()` for tests), then register
  it in `retailers/__init__.py:REGISTRY`.
- **New alert channel:** add a class in `pokemon_monitor/alerts/` subclassing
  `Alerter`, then register it in `alerts/__init__.py:build_all`.

## Layout

```
pokemon-monitor/
├── config.example.json
├── pokemon_monitor/
│   ├── cli.py / __main__.py   # entry point
│   ├── engine.py              # loop, edge-trigger, cooldown
│   ├── http.py                # polite fetcher (robots, rate limit, retries)
│   ├── models.py              # Product / StockResult / AlertEvent
│   ├── retailers/             # bestbuy, target, walmart, pokemoncenter
│   └── alerts/                # webhook, email, sms(pushover), desktop
└── tests/
```
