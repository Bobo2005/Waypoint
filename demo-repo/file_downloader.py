"""Download small text files from a remote server, streaming the body."""
import httpx


class DownloadError(Exception):
    """Raised when the remote server doesn't return a 200 for a download."""


DEFAULT_TIMEOUT = 5
CHUNK_SIZE = 64


def download_text(base_url: str, path: str) -> str:
    """Stream `path` from `base_url` and return it decoded as UTF-8 text.

    Raises DownloadError if the server responds with anything but 200.
    """
    url = f"{base_url}/{path.lstrip('/')}"
    with httpx.stream("GET", url, timeout=DEFAULT_TIMEOUT) as response:
        if response.status_code != 200:
            raise DownloadError(f"failed to download {path}: HTTP {response.status_code}")

        chunks = []
        for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
            if chunk:
                chunks.append(chunk.decode("utf-8"))
        return "".join(chunks)
