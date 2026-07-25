"""Check the health of a remote service and report a simple status string."""
import httpx

DEFAULT_TIMEOUT = 5


def check_health(base_url: str) -> str:
    """Return 'healthy', 'unhealthy (<code>)', 'timeout', or 'unreachable'."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except httpx.ConnectError:
        return "unreachable"
    except httpx.TimeoutException:
        return "timeout"
    except httpx.HTTPStatusError:
        return f"unhealthy ({response.status_code})"
    return "healthy"
