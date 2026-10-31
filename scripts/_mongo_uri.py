"""
Shared helper for test scripts — reads MONGO_URI from secrets.toml.
Never hardcodes credentials.
"""
import os
import sys


def load() -> str:
    """
    Return MONGO_URI, reading from (in order):
    1. MONGO_URI environment variable (already set)
    2. .streamlit/secrets.toml  (local dev)
    Exits with a clear message if neither is found.
    """
    uri = os.environ.get("MONGO_URI", "")
    if uri:
        return uri

    # Walk up from script dir to find secrets.toml
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    toml_path = os.path.join(here, ".streamlit", "secrets.toml")
    if os.path.exists(toml_path):
        with open(toml_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MONGO_URI"):
                    uri = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["MONGO_URI"] = uri
                    return uri

    print("ERROR: MONGO_URI not set and .streamlit/secrets.toml not found.")
    print("Add MONGO_URI to .streamlit/secrets.toml or set the env variable.")
    sys.exit(1)
