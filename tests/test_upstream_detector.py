from __future__ import annotations

import datetime
import logging
from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import GoogleAPIError

from collector.upstream_detector import (
    M_THRESHOLD,
    N_CHECK,
    ALERTS_TABLE,
    UPSTREAM_TABLE,
    UpstreamStaleException,
    detect_and_handle_upstream_stale,
    get_last_n_returned_periods,
    log_upstream_call,
    mark_upstream_stale,
)


@pytest.fixture
def mock_bq_client():
    """Provides a MagicMock for the BigQuery client."""
    return MagicMock()


def test_detector_logs_call(mock_bq_client, monkeypatch):
    """
    Tests that `detect_and_handle_upstream_stale` correctly logs the API call.
    """
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_bq_client.query.return_value = mock_query_job

    detect_and_handle_upstream_stale(
        "test_collector", 12345, '{"data": "test"}', datetime.datetime.utcnow()
    )

    mock_bq_client.insert_rows_json.assert_called_once()
    args, _ = mock_bq_client.insert_rows_json.call_args
    assert args[0] == UPSTREAM_TABLE


def test_mark_upstream_stale(mock_bq_client, monkeypatch):
    """Tests that `mark_upstream_stale` correctly generates and inserts an alert."""
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    now = datetime.datetime.utcnow()
    mark_upstream_stale("test_collector", 12345, now, now, 10)
    mock_bq_client.insert_rows_json.assert_called_once()
    args, _ = mock_bq_client.insert_rows_json.call_args
    assert args[0] == ALERTS_TABLE


def test_detector_no_history(mock_bq_client, monkeypatch):
    """Tests that the detector does not trigger when there is no history."""
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_bq_client.query.return_value = mock_query_job

    detect_and_handle_upstream_stale("test_collector", 12345)
    assert mock_bq_client.insert_rows_json.call_args[0][0] == UPSTREAM_TABLE


def test_detector_not_stale(mock_bq_client, monkeypatch):
    """Tests that the detector does not trigger when the history is not repetitive."""
    mock_results = [MagicMock(returned_period=p) for p in range(12345, 12345 - N_CHECK, -1)]
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)

    detect_and_handle_upstream_stale("test_collector", 12346)


def test_detector_stale_triggers_exception(mock_bq_client, monkeypatch):
    """Tests that `UpstreamStaleException` is raised when stale conditions are met."""
    mock_results = [
        MagicMock(returned_period=12345, call_ts=datetime.datetime.utcnow()) for _ in range(M_THRESHOLD)
    ]
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)

    with pytest.raises(UpstreamStaleException):
        detect_and_handle_upstream_stale("test_collector", 12345)
    assert mock_bq_client.insert_rows_json.call_count == 2


def test_detector_stale_with_alert_func(mock_bq_client, monkeypatch):
    """Tests that a provided alert function is called when the detector triggers."""
    mock_results = [
        MagicMock(returned_period=12345, call_ts=datetime.datetime.utcnow()) for _ in range(M_THRESHOLD)
    ]
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    mock_alert_func = MagicMock()

    with pytest.raises(UpstreamStaleException):
        detect_and_handle_upstream_stale("test_collector", 12345, send_alert_func=mock_alert_func)
    mock_alert_func.assert_called_once()


def test_detector_stale_with_failing_alert_func(mock_bq_client, caplog, monkeypatch):
    """Tests that an exception in the alert function is logged but does not crash the system."""
    mock_results = [
        MagicMock(returned_period=12345, call_ts=datetime.datetime.utcnow()) for _ in range(M_THRESHOLD)
    ]
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    mock_alert_func = MagicMock(side_effect=Exception("API is down"))

    with pytest.raises(UpstreamStaleException):
        detect_and_handle_upstream_stale("test_collector", 12345, send_alert_func=mock_alert_func)
    assert "send_alert_func failed" in caplog.text


def test_get_last_n_failure(mock_bq_client, caplog, monkeypatch):
    """Tests graceful handling of a BQ query failure in `get_last_n_returned_periods`."""
    mock_bq_client.query.side_effect = GoogleAPIError("Test BQ failure")
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    result = get_last_n_returned_periods("test_collector")
    assert result == []
    assert "Failed to query last n returned periods" in caplog.text


def test_mark_upstream_stale_failure(mock_bq_client, caplog, monkeypatch):
    """Tests graceful handling of a BQ insert failure in `mark_upstream_stale`."""
    mock_bq_client.insert_rows_json.side_effect = GoogleAPIError("Test BQ failure")
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    now = datetime.datetime.utcnow()
    mark_upstream_stale("test_collector", 12345, now, now, 10)
    assert "Failed to insert stale alert (BQ)" in caplog.text


def test_log_upstream_call_failure(mock_bq_client, caplog, monkeypatch):
    """Tests graceful handling of a BQ insert failure in `log_upstream_call`."""
    mock_bq_client.insert_rows_json.side_effect = GoogleAPIError("Test BQ failure")
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    log_upstream_call("test_collector", 12345)
    assert "Failed to log upstream call" in caplog.text


def test_log_upstream_call_success_logs_debug(mock_bq_client, caplog, monkeypatch):
    """Tests that a debug log is created on a successful upstream call log."""
    mock_bq_client.insert_rows_json.return_value = []
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    with caplog.at_level(logging.DEBUG):
        log_upstream_call("test_collector", 12345)
    assert "Logged upstream call: test_collector 12345" in caplog.text


def test_mark_upstream_stale_success_logs_info(mock_bq_client, caplog, monkeypatch):
    """Tests that an info log is created on successfully marking upstream as stale."""
    mock_bq_client.insert_rows_json.return_value = []
    monkeypatch.setattr("collector.upstream_detector.bigquery.Client", lambda project=None: mock_bq_client)
    now = datetime.datetime.utcnow()
    with caplog.at_level(logging.INFO):
        mark_upstream_stale("test_collector", 12345, now, now, 10)
    assert "Inserted upstream_stale_alert: period=12345 count=10" in caplog.text
