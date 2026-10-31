"""
fakehttp v2.0 — fake HTTP library used for blast radius testing.
Exposes: get, post, Session
Removed from v1: delete, HTTPError
"""


def get(url, **kwargs):
    """Send a GET request."""
    return {"status": 200, "body": ""}


def post(url, data=None, **kwargs):
    """Send a POST request."""
    return {"status": 201, "body": ""}


class Session:
    """Reusable HTTP session."""

    def get(self, url, **kwargs):
        return {"status": 200, "body": ""}

    def post(self, url, data=None, **kwargs):
        return {"status": 201, "body": ""}
