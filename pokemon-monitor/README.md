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
| `timezone` | IANA tz for drop windows, e.g. `America/New_York` | machine local |
| `drop_windows` | time-of-day fast-polling windows (see below) | none |

### Drop windows (fast/slow polling)

Big drops cluster in known hours (Target tends to drop ~1–5 AM, often ~3 AM then
trickle). Polling fast 24/7 is wasteful and raises your block risk; polling slow
misses the drop. A drop window polls fast only inside the window and relaxes the
rest of the day:

```json
"timezone": "America/New_York",
"drop_windows": [
  { "start": "01:00", "end": "05:00", "interval_seconds": 20 }
]
```

With this, the monitor checks every 20s between 1–5 AM and every
`interval_seconds` otherwise. Windows may wrap past midnight
(`"start": "23:00", "end": "02:00"`); if windows overlap, the tightest interval
wins. Times use `timezone` (or the machine's local time if unset). Drop windows
only apply to the long-running loop, not `--once`.

> Reality check: even 20s polling won't beat checkout bots on a sub-minute
> initial sellout. Drop windows are about catching the **trickle restocks** that
> follow — those are far more winnable by a human.

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

Notifications only happen while the monitor is running, so for unattended use
pick one of these. Ready-made files are in [`deploy/`](deploy/).

Remembering stock state across runs: set `"state_file"` in config (it's on by
default as `monitor-state.json` in `config.example.json`). The monitor saves
each product's in/out-of-stock status there so the edge-trigger and cooldown
keep working between runs — essential for the cron option below, harmless for
the always-on options. The file is git-ignored.

### Option A — systemd (always-on Linux box / VPS / Raspberry Pi)

Runs in a loop and restarts on crash or reboot.

```bash
# edit User / WorkingDirectory / ExecStart paths in the file first
sudo cp deploy/pokemon-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pokemon-monitor
journalctl -u pokemon-monitor -f      # live log of checks/alerts
```

### Option B — macOS (launchd)

Starts at login, restarts on crash. Desktop alerts work natively here.

```bash
# edit the two paths in the file first
cp deploy/com.pokemon-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.pokemon-monitor.plist
```

### Option C — cron (periodic one-shot checks, Linux/macOS)

No long-running daemon; cron fires a single `--once` pass on a schedule. Relies
on `state_file` to avoid repeat alerts. See [`deploy/crontab.example`](deploy/crontab.example):

```cron
*/5 * * * * cd /path/to/pokemon-monitor && /usr/bin/python3 -m pokemon_monitor --config config.json --once >> ~/pokemon-monitor.log 2>&1
```

> Keep `interval_seconds` (loop mode) or the cron frequency reasonable (≥ ~2–5
> min). Faster polling won't beat the retailers' own anti-bot queueing and just
> raises your block risk.

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
