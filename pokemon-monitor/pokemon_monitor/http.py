"""A deliberately *polite* HTTP fetcher.

Retailers explicitly don't want to be hammered, and aggressive scraping is what
gets IPs and accounts banned. This fetcher:

  - sends a real, identifiable User-Agent
  - honours robots.txt (per host, cached)
  - enforces a minimum delay between requests to the same host
  - retries transient failures with exponential backoff
  - never follows a request the site disallows

It is stdlib-only (urllib) so the project keeps its zero-dependency promise.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_UA = (
    "pokemon-monitor/0.1 (personal restock notifier; "
    "+https://github.com/0xStevan/secrets-scanner)"
)


@dataclass
class Response:
    url: str
    status: int
    text: str


class FetchError(Exception):
    """Raised when a fetch ultimately fails (after retries / robots block)."""


class PoliteFetcher:
    """Rate-limited, robots-aware HTTP GET helper.

    One instance should be shared across the whole run so per-host rate limits
    and the robots cache are respected globally.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        min_interval: float = 3.0,
        timeout: float = 20.0,
        max_retries: int = 3,
        respect_robots: bool = True,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.respect_robots = respect_robots
        self._sleep = sleep
        self._clock = clock
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    # -- robots ----------------------------------------------------------
    def _robots_for(self, host: str, scheme: str):
        if host in self._robots:
            return self._robots[host]
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{scheme}://{host}/robots.txt")
        try:
            rp.read()
        except Exception:
            # If robots.txt is unreachable, fail open but stay polite via
            # rate limiting. Many CDNs 403 the robots fetch itself.
            rp = None  # type: ignore[assignment]
        self._robots[host] = rp  # type: ignore[assignment]
        return rp

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        rp = self._robots_for(parsed.netloc, parsed.scheme or "https")
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)

    # -- rate limiting ---------------------------------------------------
    def _throttle(self, host: str) -> None:
        last = self._last_hit.get(host)
        now = self._clock()
        if last is not None:
            wait = self.min_interval - (now - last)
            if wait > 0:
                self._sleep(wait)
        self._last_hit[host] = self._clock()

    # -- fetch -----------------------------------------------------------
    def get(self, url: str, headers: dict | None = None) -> Response:
        if not self.allowed(url):
            raise FetchError(f"robots.txt disallows fetching {url}")

        host = urlparse(url).netloc
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle(host)
            req = urllib.request.Request(url, headers=req_headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode(
                        resp.headers.get_content_charset() or "utf-8",
                        errors="replace",
                    )
                    return Response(url=url, status=resp.status, text=body)
            except urllib.error.HTTPError as e:
                # 4xx (except 429) are not worth retrying — they won't change.
                if e.code != 429 and 400 <= e.code < 500:
                    raise FetchError(f"HTTP {e.code} for {url}") from e
                last_err = e
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e

            if attempt < self.max_retries - 1:
                self._sleep(2 ** attempt)  # 1s, 2s, 4s ...

        raise FetchError(f"failed to fetch {url}: {last_err}")
