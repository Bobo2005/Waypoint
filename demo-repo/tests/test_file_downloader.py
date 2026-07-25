import pytest

from file_downloader import DownloadError, download_text


def test_download_text_success(live_server):
    content = download_text(live_server, "files/hello.txt")
    assert content == "hello from the fixture server"


def test_download_text_missing_raises(live_server):
    with pytest.raises(DownloadError):
        download_text(live_server, "files/missing.txt")