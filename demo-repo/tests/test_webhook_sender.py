from webhook_sender import send_webhook


def test_send_webhook_echoes_event(live_server):
    result = send_webhook(live_server, "user.created", {"id": 42})
    assert result["received"] is True
    assert result["event"] == "user.created"