"""Check the health of a remote service and report a simple status string."""
import requests

DEFAULT_TIMEOUT = 5


def check_health(base_url: str) -> str:
    """Return 'healthy', 'unhealthy (<code>)', 'timeout', or 'unreachable'."""
    try:
        response = requests.get(f"{base_url}/health", timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "unreachable"
    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.HTTPError:
        return f"unhealthy ({response.status_code})"
    return "healthy"