"""Authenticated, rate-limited HTTP client for the Zenodo REST API."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from .targets import Target

USER_AGENT = "ICE-LAPSE-Uploader/1.0 (+https://github.com/biodiversity-aq/ICE-LAPSE-dataset)"
RATE_INTERVAL_SECONDS = 0.75  # keeps this process at <=80 requests/min and <=4,800/hour
MAX_ATTEMPTS = 6


class RateLimitedClient:
    """Pace calls below Zenodo's documented limits and retry on HTTP 429."""

    def __init__(self, session: Any):
        self.session = session
        self.last_request = 0.0

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        for attempt in range(MAX_ATTEMPTS):
            wait = RATE_INTERVAL_SECONDS - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            response = self.session.request(method, url, **kwargs)
            self.last_request = time.monotonic()
            if response.status_code == 429 and attempt < MAX_ATTEMPTS - 1:
                if hasattr(kwargs.get("data"), "seek"):
                    kwargs["data"].seek(0)  # rewind file upload before retrying
                delay = _retry_delay(response.headers.get("Retry-After", "60"))
                print(f"Zenodo rate limit; waiting {delay:g}s", file=sys.stderr)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        raise RuntimeError("Zenodo rate-limit retries exhausted")


def _retry_delay(retry_after: str) -> float:
    try:
        return max(float(retry_after), RATE_INTERVAL_SECONDS)
    except ValueError:
        return 60.0


def create_client(target: Target) -> RateLimitedClient:
    """Client authenticated with the target's token from the environment."""
    token = os.environ.get(target.token_env)
    if not token:
        raise RuntimeError(f"Set {target.token_env} in environment; never put token in source code")
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("Install dependencies with: python -m pip install -r requirements.txt") from error
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})
    return RateLimitedClient(session)
