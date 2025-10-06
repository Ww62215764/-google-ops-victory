from __future__ import annotations

import logging
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient
from requests.exceptions import RequestException

import main
from main import app


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Resets the app_context singleton after each test."""
    yield
    main.app_context = main.AppContext()


@pytest.fixture
def client():
    """Provides a TestClient for making API calls in tests."""
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    """Tests that the /health endpoint works correctly."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_collect_success(client):
    """Tests the successful data collection path."""
    with patch("main.get_api_key", return_value="fake_api_key"), patch(
        "main.call_api_with_retry",
        return_value={"codeid": 10000, "retdata": {"curent": {"long_issue": "20251006001"}}},
    ), patch("main.detect_and_handle_upstream_stale"), patch("main.parse_and_insert_data"):
        response = client.post("/collect")
        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_collect_circuit_breaker(client):
    """Tests that the circuit breaker returns 429 when upstream is stale."""
    with patch("main.get_api_key", return_value="fake_api_key"), patch(
        "main.call_api_with_retry",
        return_value={"codeid": 10000, "retdata": {"curent": {"long_issue": "20251006001"}}},
    ), patch("main.detect_and_handle_upstream_stale", side_effect=main.UpstreamStaleException):
        response = client.post("/collect")
        assert response.status_code == 429


def test_collect_api_error(client):
    """Tests that a 502 is returned when the upstream API gives an error."""
    with patch("main.get_api_key", return_value="fake_api_key"), patch(
        "main.call_api_with_retry", return_value={"codeid": 9999}
    ):
        response = client.post("/collect")
        assert response.status_code == 502


@pytest.mark.asyncio
async def test_middleware_sends_metrics(client):
    """Tests that the monitoring middleware sends metrics on a request."""
    with patch("main.MonitoringMiddleware.send_metrics") as mock_send_metrics:
        client.get("/health")
    mock_send_metrics.assert_called_once()


def test_parse_data_value_error():
    """Tests that a ValueError is raised if key data is missing from the API response."""
    with pytest.raises(ValueError, match="关键字段缺失: long_issue"):
        main.parse_and_insert_data({}, MagicMock())


@pytest.mark.asyncio
async def test_docs_endpoint_is_skipped_by_middleware(client):
    """Tests that the /docs endpoint is correctly ignored by the middleware."""
    with patch("main.MonitoringMiddleware.send_metrics") as mock_send_metrics:
        client.get("/docs")
    mock_send_metrics.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_unhandled_exception_is_logged(client, caplog):
    """Tests that unhandled exceptions in endpoints are logged by the middleware."""
    @app.get("/__unhandled_error_route")
    async def unhandled_error_route():
        raise ValueError("Unhandled error")

    with caplog.at_level(logging.ERROR), pytest.raises(ValueError):
        client.get("/__unhandled_error_route")
    assert "Unhandled exception" in caplog.text
    app.routes.pop()


@pytest.mark.asyncio
async def test_middleware_http_exception_is_handled(client):
    """Tests that HTTPExceptions are handled correctly and metrics are sent."""
    @app.get("/__http_exception_route")
    async def http_exception_route():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    with patch("main.MonitoringMiddleware.send_metrics") as mock_send_metrics:
        response = client.get("/__http_exception_route")
        assert response.status_code == 418
    mock_send_metrics.assert_called_once()
    app.routes.pop()


@pytest.mark.asyncio
async def test_send_metrics_handles_exception(caplog):
    """Tests that the system logs an error but does not crash if sending metrics fails."""
    middleware = main.MonitoringMiddleware(app=app)
    with patch('main.AppContext.monitoring_client', new_callable=PropertyMock, side_effect=Exception("unavailable")):
        with caplog.at_level(logging.ERROR):
            middleware.send_metrics("/test", "GET", 200, 123.45)
            assert "Failed to send metrics" in caplog.text


def test_get_secret_client_is_singleton():
    """Tests that the secret_client behaves like a singleton."""
    with patch("main.secretmanager.SecretManagerServiceClient") as mock_constructor:
        _ = main.app_context.secret_client
        _ = main.app_context.secret_client
        mock_constructor.assert_called_once()


def test_get_cloud_logger_is_singleton():
    """Tests that the cloud_logger behaves like a singleton."""
    with patch("main.cloud_logging.Client") as mock_constructor:
        _ = main.app_context.cloud_logger
        _ = main.app_context.cloud_logger
        mock_constructor.assert_called_once()


def test_get_api_key_success():
    """Tests successful retrieval of the API key."""
    with patch("main.AppContext.secret_client", new_callable=PropertyMock) as mock_secret_client:
        mock_secret_client.return_value.access_secret_version.return_value.payload.data = b"fake_api_key"
        key = main.get_api_key()
        assert key == "fake_api_key"


def test_get_api_key_failure():
    """Tests that a non-network error during API key retrieval fails without retries."""
    with patch("main.AppContext.secret_client", new_callable=PropertyMock) as mock_secret_client:
        mock_secret_client.side_effect = Exception("Non-network error")
        with pytest.raises(Exception, match="Non-network error"):
            main.get_api_key()
        mock_secret_client.assert_called_once()


def test_get_api_key_failure_retries(caplog):
    """Tests the retry mechanism for network errors during API key retrieval."""
    with patch('main.AppContext.secret_client', new_callable=PropertyMock) as mock_secret_client:
        mock_secret_client.side_effect = RequestException("Network error")
        with caplog.at_level(logging.WARNING), pytest.raises(RequestException):
            main.get_api_key()
        assert "Retrying in" in caplog.text
        assert mock_secret_client.call_count == 3


def test_collect_internal_server_error(client, caplog):
    """Tests that an unexpected internal error is caught and logged, returning a 500."""
    with patch("main.get_api_key", side_effect=ValueError("A wild error appears")):
        response = client.post("/collect")
        assert response.status_code == 500
        assert "Collector pipeline failed" in caplog.text
