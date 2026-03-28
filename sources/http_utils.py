"""
Shared HTTP helpers with session reuse, timeouts, and error handling.
"""

import logging
import requests
import time
import random
import threading
from config import (
    REQUEST_TIMEOUT,
    RETRY_MAX_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
    RETRY_BACKOFF_MAX,
)

log = logging.getLogger(__name__)

# Use a per-call session (with shared default headers) for thread-safety
# while keeping the convenience of default headers.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


_thread_local = threading.local()


def _get_session():
    """Return a requests.Session unique to the current thread.

    The session is created once per thread and reused for subsequent calls
    from the same thread. Per-call headers passed to `get_json`/`post_json`
    are provided to the request invocation (not merged permanently into the
    session headers).
    """
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(_DEFAULT_HEADERS)
        _thread_local.session = sess
    return sess


def get_json(url: str, params: dict = None, headers: dict = None,
             timeout: int = REQUEST_TIMEOUT) -> dict | list | None:
    """GET request returning parsed JSON, or None on error."""
    attempts = 0
    while attempts < RETRY_MAX_ATTEMPTS:
        attempts += 1
        try:
            s = _get_session()
            resp = s.get(url, params=params, headers=headers, timeout=timeout)
            # Retry on specific status codes
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.RequestException(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError as e:
                log.warning(f"JSON parse error for {url}: {e}")
                return None
        except requests.RequestException as e:
            is_retryable = isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or "HTTP" in str(e)
            if attempts >= RETRY_MAX_ATTEMPTS or not is_retryable:
                log.warning(f"GET {url} failed (attempt {attempts}/{RETRY_MAX_ATTEMPTS}): {e}")
                return None
            # Exponential backoff with jitter
            backoff = min(RETRY_BACKOFF_MAX, RETRY_BACKOFF_FACTOR * (2 ** (attempts - 1)))
            jitter = random.uniform(0, backoff * 0.1)
            sleep_time = backoff + jitter
            log.debug(f"GET {url} retrying in {sleep_time:.2f}s (attempt {attempts})")
            time.sleep(sleep_time)


def post_json(url: str, payload: dict = None, headers: dict = None,
              timeout: int = REQUEST_TIMEOUT) -> dict | list | None:
    """POST request with JSON body, returning parsed JSON or None."""
    attempts = 0
    while attempts < RETRY_MAX_ATTEMPTS:
        attempts += 1
        try:
            s = _get_session()
            resp = s.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.RequestException(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError as e:
                log.warning(f"JSON parse error for {url}: {e}")
                return None
        except requests.RequestException as e:
            is_retryable = isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or "HTTP" in str(e)
            if attempts >= RETRY_MAX_ATTEMPTS or not is_retryable:
                log.warning(f"POST {url} failed (attempt {attempts}/{RETRY_MAX_ATTEMPTS}): {e}")
                return None
            backoff = min(RETRY_BACKOFF_MAX, RETRY_BACKOFF_FACTOR * (2 ** (attempts - 1)))
            jitter = random.uniform(0, backoff * 0.1)
            sleep_time = backoff + jitter
            log.debug(f"POST {url} retrying in {sleep_time:.2f}s (attempt {attempts})")
            time.sleep(sleep_time)


def get_text(url: str, params: dict = None, headers: dict = None,
             timeout: int = REQUEST_TIMEOUT) -> str | None:
    """GET request returning raw text, or None on error."""
    attempts = 0
    while attempts < RETRY_MAX_ATTEMPTS:
        attempts += 1
        try:
            s = _get_session()
            resp = s.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.RequestException(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            is_retryable = isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or "HTTP" in str(e)
            if attempts >= RETRY_MAX_ATTEMPTS or not is_retryable:
                log.warning(f"GET text {url} failed (attempt {attempts}/{RETRY_MAX_ATTEMPTS}): {e}")
                return None
            backoff = min(RETRY_BACKOFF_MAX, RETRY_BACKOFF_FACTOR * (2 ** (attempts - 1)))
            jitter = random.uniform(0, backoff * 0.1)
            sleep_time = backoff + jitter
            log.debug(f"GET text {url} retrying in {sleep_time:.2f}s (attempt {attempts})")
            time.sleep(sleep_time)
