"""
fakehttp v1.0 — fake HTTP library used for blast radius testing.
Exposes: get, post, delete, Session, HTTPError
"""


def get(url, **kwargs):
    """Send a GET request."""
    return {"status": 200, "body": ""}


def post(url, data=None, **kwargs):
    """Send a POST request."""
    return {"status": 201, "body": ""}


def delete(url, **kwargs):
    """Send a DELETE request."""
    return {"status": 204, "body": ""}


class Session:
    """Reusable HTTP session."""

    def get(self, url, **kwargs):
        return {"status": 200, "body": ""}

    def post(self, url, data=None, **kwargs):
        return {"status": 201, "body": ""}


class HTTPError(Exception):
    """Raised when an HTTP request returns an error status."""
    pass
