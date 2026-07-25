from weather_client import get_weather


def test_get_weather_returns_payload(live_server):
    result = get_weather("Lagos", base_url=live_server)
    assert result["city"] == "Lagos"
    assert "temp_c" in result