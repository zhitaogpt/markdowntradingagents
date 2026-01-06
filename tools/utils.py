import random
import time
import sys
# Use curl_cffi as required by Yahoo's anti-bot
from curl_cffi import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def get_session():
    """Create a curl_cffi session to mimic a browser."""
    # impersonate="chrome120" is a powerful feature of curl_cffi
    session = requests.Session(impersonate="chrome120")
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session

def exponential_backoff(func, retries=3, initial_delay=5):
    last_exception = None
    delay = initial_delay
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            err_msg = str(e).lower()
            if any(x in err_msg for x in ["429", "too many requests", "rate limited", "empty", "none"]):
                actual_delay = delay * random.uniform(0.8, 1.2)
                print(f"[Retry {attempt+1}/{retries}] Rate Limit. Sleeping {actual_delay:.2f}s...", file=sys.stderr)
                time.sleep(actual_delay)
                delay *= 2
            else:
                print(f"[Retry {attempt+1}/{retries}] Error: {e}", file=sys.stderr)
                time.sleep(delay)
    raise last_exception
