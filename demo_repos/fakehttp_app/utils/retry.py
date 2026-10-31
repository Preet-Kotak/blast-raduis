"""Retry wrapper that catches fakehttp.HTTPError."""
import fakehttp


def get_with_retry(url: str, retries: int = 3) -> dict:
    """Retry a GET request up to `retries` times on HTTPError."""
    for attempt in range(retries):
        try:
            return fakehttp.get(url)
        except fakehttp.HTTPError as exc:
            if attempt == retries - 1:
                raise
            print(f"Retry {attempt + 1} after error: {exc}")
