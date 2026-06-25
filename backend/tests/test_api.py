"""
AtmosMind backend API tests — tiered autocomplete, AI boundaries, rate limiting.
Run from backend/:  pytest -v
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api
from ai_chat import DECLINE_MESSAGES
from security import ChatSafetyVerdict


def _collect_chat_sse(response) -> str:
    """Concatenate token payloads from a /api/chat SSE response."""
    tokens: list[str] = []
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        data = json.loads(payload)
        if data.get("type") == "token":
            tokens.append(data.get("content", ""))
        elif data.get("type") == "error" or data.get("error"):
            return data.get("error") or data.get("reply") or data.get("message", "")
    return "".join(tokens)


def _mock_agent_with_reply(reply: str):
    agent = MagicMock()

    async def astream(**_kwargs):
        yield reply

    agent.astream = astream
    return agent


def _redis_hit(name: str, lat: float, lon: float, population: int = 1_000_000) -> dict:
    return {"name": name, "lat": lat, "lon": lon, "population": population}


def _sqlite_row(name: str, lat: float, lon: float, **extra) -> dict:
    return {
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "country": extra.get("country", "Country"),
        "country_code": extra.get("country_code", "XX"),
        "admin1": extra.get("admin1", ""),
        "population": extra.get("population", 500_000),
    }


def _open_meteo_response(*cities: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": list(cities)}
    return mock_resp


# ─── Tiered search (unit-level, mocked tiers) ────────────────────────────────


class TestTieredSearch:
    def test_short_query_returns_empty(self):
        assert api._tiered_search("ab", "en") == []

    @patch("api.requests.get")
    @patch("api.search_by_prefix")
    @patch("api.get_connection")
    @patch("api.search_redis")
    @patch("api._get_redis")
    def test_en_redis_tier_satisfies_without_sqlite(
        self, mock_get_redis, mock_search_redis, mock_get_conn, mock_sqlite, mock_requests
    ):
        mock_get_redis.return_value = MagicMock()
        mock_search_redis.return_value = [
            _redis_hit("London, United Kingdom", 51.5085, -0.1257, 9_000_000),
            _redis_hit("London, Canada", 42.9834, -81.233, 400_000),
            _redis_hit("Londonderry, United Kingdom", 54.997, -7.309, 100_000),
            _redis_hit("Long Beach, United States", 33.766, -118.189, 500_000),
            _redis_hit("Longford, Ireland", 53.725, -7.798, 10_000),
        ]

        results = api._tiered_search("lon", "en")

        assert len(results) == api.MIN_SUGGESTIONS
        assert results[0]["name"] == "London, United Kingdom"
        mock_search_redis.assert_called_once()
        mock_get_conn.assert_not_called()
        mock_sqlite.assert_not_called()
        mock_requests.assert_not_called()

    @patch("api.requests.get")
    @patch("api.search_by_prefix")
    @patch("api.get_connection")
    @patch("api.search_redis")
    @patch("api._get_redis")
    def test_redis_miss_falls_back_to_sqlite(
        self, mock_get_redis, mock_search_redis, mock_get_conn, mock_sqlite, mock_requests
    ):
        mock_get_redis.return_value = MagicMock()
        mock_search_redis.return_value = [
            _redis_hit("London, United Kingdom", 51.5085, -0.1257),
        ]
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_sqlite.return_value = [
            _sqlite_row("Londrina", -23.31, -51.16, country="Brazil", country_code="BR"),
            _sqlite_row("Longyearbyen", 78.22, 15.63, country="Norway", country_code="NO"),
            _sqlite_row("Londontowne", 38.93, -76.55, country="United States", country_code="US"),
            _sqlite_row("London Grove", 39.84, -75.98, country="United States", country_code="US"),
        ]

        results = api._tiered_search("lon", "en")

        assert len(results) >= api.MIN_SUGGESTIONS
        mock_search_redis.assert_called_once()
        mock_sqlite.assert_called_once()
        mock_requests.assert_not_called()
        mock_conn.close.assert_called_once()

    @patch("api.requests.get")
    @patch("api.search_by_prefix")
    @patch("api.get_connection")
    @patch("api.search_redis")
    @patch("api._get_redis")
    def test_redis_and_sqlite_fail_falls_back_to_open_meteo(
        self, mock_get_redis, mock_search_redis, mock_get_conn, mock_sqlite, mock_requests
    ):
        mock_get_redis.side_effect = RuntimeError("Redis connection refused")
        mock_get_conn.side_effect = RuntimeError("SQLite unavailable")
        mock_requests.return_value = _open_meteo_response(
            {
                "name": "Zzyzx",
                "latitude": 35.14,
                "longitude": -115.65,
                "feature_code": "PPL",
                "population": 100,
                "admin1": "California",
                "country_code": "US",
            },
            {
                "name": "Zzyzx Springs",
                "latitude": 35.15,
                "longitude": -115.66,
                "feature_code": "PPL",
                "population": 50,
                "admin1": "California",
                "country_code": "US",
            },
            {
                "name": "Zzyzxville",
                "latitude": 35.16,
                "longitude": -115.67,
                "feature_code": "PPL",
                "population": 25,
                "admin1": "California",
                "country_code": "US",
            },
            {
                "name": "Zzyzxton",
                "latitude": 35.17,
                "longitude": -115.68,
                "feature_code": "PPL",
                "population": 10,
                "admin1": "California",
                "country_code": "US",
            },
            {
                "name": "Zzyzxburg",
                "latitude": 35.18,
                "longitude": -115.69,
                "feature_code": "PPL",
                "population": 5,
                "admin1": "California",
                "country_code": "US",
            },
        )

        results = api._tiered_search("zzy", "en")

        assert len(results) >= api.MIN_SUGGESTIONS
        mock_requests.assert_called_once()
        assert "Zzyzx" in results[0]["name"]

    @patch("api.requests.get")
    @patch("api.search_by_prefix")
    @patch("api.get_connection")
    @patch("api.search_redis")
    @patch("api._get_redis")
    def test_redis_offline_degrades_to_sqlite_without_raising(
        self, mock_get_redis, mock_search_redis, mock_get_conn, mock_sqlite, mock_requests
    ):
        mock_get_redis.return_value = None
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_sqlite.return_value = [
            _sqlite_row("Paris", 48.85, 2.35, country="France", country_code="FR"),
            _sqlite_row("Parma", 44.80, 10.33, country="Italy", country_code="IT"),
            _sqlite_row("Paraty", -23.22, -44.71, country="Brazil", country_code="BR"),
            _sqlite_row("Parakou", 9.34, 2.63, country="Benin", country_code="BJ"),
            _sqlite_row("Paraná", -31.73, -60.53, country="Argentina", country_code="AR"),
        ]

        results = api._tiered_search("par", "en")

        assert len(results) >= api.MIN_SUGGESTIONS
        mock_search_redis.assert_not_called()
        mock_sqlite.assert_called_once()
        mock_requests.assert_not_called()


# ─── Autocomplete HTTP resilience ────────────────────────────────────────────


class TestAutocompleteEndpoint:
    def test_query_shorter_than_min_length_returns_empty(self, client: TestClient):
        response = client.post("/api/autocomplete", json={"query": "ab", "language": "en"})
        assert response.status_code == 200
        assert response.json() == {"suggestions": []}

    @patch("api._tiered_search", side_effect=RuntimeError("catastrophic failure"))
    def test_internal_failure_returns_empty_not_500(self, mock_search, client: TestClient):
        response = client.post("/api/autocomplete", json={"query": "london", "language": "en"})
        assert response.status_code == 200
        assert response.json() == {"suggestions": []}

    @patch("api._tiered_search")
    def test_successful_autocomplete_payload(self, mock_search, client: TestClient):
        mock_search.return_value = [
            {"name": "London, United Kingdom", "lat": 51.5, "lon": -0.12, "population": 9_000_000}
        ]
        response = client.post("/api/autocomplete", json={"query": "lon", "language": "en"})
        assert response.status_code == 200
        body = response.json()
        assert body["suggestions"][0]["name"] == "London, United Kingdom"

    @patch("api._tiered_search")
    def test_autocomplete_preserves_unicode_names(self, mock_search, client: TestClient):
        """AC-06: Unicode city names must pass through unchanged (no ASCII folding)."""
        mock_search.return_value = [
            {
                "name": "İstanbul, Türkiye",
                "lat": 41.0138,
                "lon": 28.9603,
                "population": 15_000_000,
            }
        ]
        response = client.post(
            "/api/autocomplete",
            json={"query": "İst", "language": "tr"},
        )
        assert response.status_code == 200
        assert response.json()["suggestions"][0]["name"] == "İstanbul, Türkiye"


# ─── AI chat boundaries ──────────────────────────────────────────────────────


class TestChatBoundaries:
    def test_empty_messages_returns_422(self, client: TestClient):
        response = client.post("/api/chat", json={"messages": [], "language": "en", "unit": "metric"})
        assert response.status_code == 422

    def test_oversized_message_returns_422(self, client: TestClient):
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "x" * 2001}],
                "language": "en",
                "unit": "metric",
            },
        )
        assert response.status_code == 422

    @patch("api.get_atmosmind_agent")
    def test_off_topic_prompt_returns_decline_message(self, mock_get_agent, client: TestClient, monkeypatch):
        async def _block_off_topic(_user_text: str, _language: str = "en"):
            return ChatSafetyVerdict(allowed=False, message=DECLINE_MESSAGES["en"])

        monkeypatch.setattr(api, "evaluate_chat_input_safety", _block_off_topic)
        mock_get_agent.return_value = _mock_agent_with_reply(DECLINE_MESSAGES["en"])
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Write me a Python sorting algorithm."}],
                "language": "en",
                "unit": "metric",
            },
        )
        assert response.status_code == 200
        reply = _collect_chat_sse(response)
        assert "AtmosMind" in reply
        assert "weather" in reply.lower()

    @patch("api.get_atmosmind_agent")
    def test_off_topic_classifier_decline_integration(self, mock_get_agent, client: TestClient, monkeypatch):
        async def _block_off_topic(_user_text: str, _language: str = "en"):
            return ChatSafetyVerdict(allowed=False, message=DECLINE_MESSAGES["en"])

        monkeypatch.setattr(api, "evaluate_chat_input_safety", _block_off_topic)
        mock_get_agent.return_value = _mock_agent_with_reply(DECLINE_MESSAGES["en"])
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Who won the 2022 FIFA World Cup?"}],
                "language": "en",
                "unit": "metric",
            },
        )
        assert response.status_code == 200
        assert _collect_chat_sse(response) == DECLINE_MESSAGES["en"]

    @patch("api.get_atmosmind_agent")
    def test_weather_prompt_reaches_model(self, mock_get_agent, client: TestClient):
        mock_get_agent.return_value = _mock_agent_with_reply(
            "Expect mild temperatures in Paris tomorrow."
        )
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "What is the weather in Paris tomorrow?"}],
                "language": "en",
                "unit": "metric",
            },
        )
        assert response.status_code == 200
        assert "Paris" in _collect_chat_sse(response)

    def test_agent_init_failure_returns_json_reply(self, client: TestClient, monkeypatch):
        def _broken_agent():
            raise RuntimeError("GOOGLE_API_KEY is not set.")

        monkeypatch.setattr(api, "_atmosmind_agent", None)
        monkeypatch.setattr(api, "get_atmosmind_agent", _broken_agent)

        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Paris'te hava nasıl?"}],
                "language": "tr",
                "unit": "metric",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        reply = _collect_chat_sse(response)
        assert "bağlanılamadı" in reply or "yanıt veremiyor" in reply


# ─── Rate limiting ───────────────────────────────────────────────────────────


class TestRateLimiting:
    @pytest.fixture(autouse=True)
    def mock_chat_agent(self, monkeypatch):
        agent = _mock_agent_with_reply("Sunny in Berlin.")
        monkeypatch.setattr(api, "_atmosmind_agent", agent)
        monkeypatch.setattr(api, "get_atmosmind_agent", lambda: agent)

    def test_chat_rate_limit_returns_429(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("security.RATE_LIMIT_MAX_REQUESTS", 3)
        payload = {
            "messages": [{"role": "user", "content": "What is the weather in Berlin?"}],
            "language": "en",
            "unit": "metric",
        }

        with patch("api.get_city_advice", return_value="Bring water."):
            for _ in range(3):
                response = client.post("/api/chat", json=payload)
                assert response.status_code == 200

            blocked = client.post("/api/chat", json=payload)
            assert blocked.status_code == 429
            assert "Too many requests" in blocked.json()["detail"]

    def test_rate_limit_is_per_endpoint(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("security.RATE_LIMIT_MAX_REQUESTS", 2)
        chat_payload = {
            "messages": [{"role": "user", "content": "Weather in Rome?"}],
            "language": "en",
            "unit": "metric",
        }
        advice_payload = {
            "city": "Rome",
            "weather_summary": "Sunny, 25C",
            "language": "en",
            "unit": "metric",
        }

        with patch("api.get_city_advice", return_value="Bring water."):
            assert client.post("/api/chat", json=chat_payload).status_code == 200
            assert client.post("/api/chat", json=chat_payload).status_code == 200
            assert client.post("/api/chat", json=chat_payload).status_code == 429

            # Different endpoint bucket should still be allowed.
            assert client.post("/api/get-city-advice", json=advice_payload).status_code == 200
