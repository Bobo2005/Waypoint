"""Fetch current weather for a city from a small JSON weather API."""
import requests

DEFAULT_TIMEOUT = 5


def get_weather(city: str, base_url: str) -> dict:
    """Return the current weather payload for `city`.

    Raises requests.HTTPError if the server responds with a non-2xx status.
    """
    response = requests.get(
        f"{base_url}/weather",
        params={"city": city},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()