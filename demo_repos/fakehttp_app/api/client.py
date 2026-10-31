"""HTTP client wrapper around fakehttp."""
import fakehttp


def fetch_data(url: str = "http://example.com") -> dict:
    return fakehttp.get(url)


def delete_resource(url: str) -> dict:
    # Uses fakehttp.delete — removed in v2
    return fakehttp.delete(url)


def create_session() -> fakehttp.Session:
    return fakehttp.Session()
