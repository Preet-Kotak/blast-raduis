"""Entry point for the sample app."""
from api import client


def run():
    response = client.fetch_data()
    print(response)


if __name__ == "__main__":
    run()
