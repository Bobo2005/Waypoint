"""Send event payloads to a webhook endpoint."""
import requests

DEFAULT_TIMEOUT = 5


def send_webhook(base_url: str, event: str, payload: dict) -> dict:
    """POST an event to the webhook endpoint and return the decoded response.

    Raises requests.HTTPError if the server responds with a non-2xx status.
    """
    body = {"event": event, "data": payload}
    response = requests.post(
        f"{base_url}/webhooks/incoming",
        json=body,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()