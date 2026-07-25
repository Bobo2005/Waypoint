from status_reporter import check_health


def test_check_health_healthy(live_server):
    assert check_health(live_server) == "healthy"


def test_check_health_unhealthy(live_server):
    assert check_health(f"{live_server}/broken") == "unhealthy (503)"


def test_check_health_unreachable():
    # Nothing is listening on this high port, so the connection should fail
    # fast without needing a live_server at all.
    assert check_health("http://127.0.0.1:65530") == "unreachable"