import pytest
from unittest.mock import patch, MagicMock, call
import datetime
import os
import sys

# 将应用目录添加到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 假设 UpstreamStaleException 在 collector.upstream_detector 模块中定义
from collector.upstream_detector import (
    detect_and_handle_upstream_stale,
    UpstreamStaleException,
    mark_upstream_stale,
    N_CHECK,
    M_THRESHOLD
)

@pytest.fixture
def mock_bq_client():
    """
    修正: 攻击目标从不存在的 `get_bq_client` 修正为模块级的 `bq` 实例。
    """
    with patch('collector.upstream_detector.bq') as mock_client:
        yield mock_client

def test_detector_logs_call(mock_bq_client):
    """
    修正: 不直接测试私有函数 `_log_upstream_call`。
    改为测试 `detect_and_handle_upstream_stale` 是否正确地触发了日志记录。
    """
    # 纪律修正: 修复遗漏的陷阱一
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_bq_client.query.return_value = mock_query_job
    
    detect_and_handle_upstream_stale("test_collector", 12345, '{"data": "test"}', datetime.datetime.utcnow())
    
    mock_bq_client.insert_rows_json.assert_called_once()
    args, kwargs = mock_bq_client.insert_rows_json.call_args
    from collector.upstream_detector import UPSTREAM_TABLE
    assert args[0] == UPSTREAM_TABLE
    assert len(args[1]) == 1
    # 胜利前的最后修正: 键名是 'collector' 而非 'collector_name'
    assert args[1][0]['collector'] == "test_collector"
    assert args[1][0]['returned_period'] == 12345

def test_mark_upstream_stale(mock_bq_client):
    """测试 mark_upstream_stale 函数是否能正确生成和插入告警"""
    now = datetime.datetime.utcnow()
    alert = mark_upstream_stale(
        "test_collector", 12345, now, now, 10, "CRITICAL", "Stale"
    )
    assert alert['severity'] == "CRITICAL"
    assert alert['note'] == "Stale"
    mock_bq_client.insert_rows_json.assert_called_once()
    args, kwargs = mock_bq_client.insert_rows_json.call_args
    # 修正陷阱二: 期望一个完全限定的表名
    from collector.upstream_detector import ALERTS_TABLE
    assert args[0] == ALERTS_TABLE

def test_detector_no_history(mock_bq_client):
    """测试在没有历史记录时，检测器不会触发"""
    # 修正陷阱一: 返回一个拥有 .result() 方法的模拟对象
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_bq_client.query.return_value = mock_query_job

    result = detect_and_handle_upstream_stale("test_collector", 12345)
    assert result is None
    # 验证日志记录被调用
    # 纪律修正: 使用完全限定的表名
    from collector.upstream_detector import UPSTREAM_TABLE
    mock_bq_client.insert_rows_json.assert_called_once()
    assert mock_bq_client.insert_rows_json.call_args[0][0] == UPSTREAM_TABLE


def test_detector_not_stale(mock_bq_client):
    """测试在历史记录不重复时，检测器不会触发"""
    # 模拟返回的历史期号
    mock_results = [MagicMock(returned_period=p) for p in range(12345, 12345 - N_CHECK, -1)]
    # 修正陷阱一: 返回一个拥有 .result() 方法的模拟对象
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    
    result = detect_and_handle_upstream_stale("test_collector", 12346)
    assert result is None

def test_detector_stale_triggers_exception(mock_bq_client):
    """测试在历史记录连续重复达到阈值时，检测器会触发异常"""
    # 确保 M_THRESHOLD 和 N_CHECK 的值是正确的
    assert M_THRESHOLD == 10
    assert N_CHECK == 10
    
    # 模拟返回 M_THRESHOLD 次相同的历史期号
    mock_results = [MagicMock(returned_period=12345, call_ts=datetime.datetime.utcnow()) for _ in range(M_THRESHOLD)]
    # 修正陷阱一: 返回一个拥有 .result() 方法的模拟对象
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_bq_client.query.return_value = mock_query_job
    
    with pytest.raises(UpstreamStaleException) as excinfo:
        detect_and_handle_upstream_stale("test_collector", 12345)
    
    assert f"Detected {M_THRESHOLD} consecutive identical periods" in str(excinfo.value)
    
    # 验证调用了 log_call 和 mark_stale
    assert mock_bq_client.insert_rows_json.call_count == 2
    calls = mock_bq_client.insert_rows_json.call_args_list
    # 纪律修正: 使用完全限定的表名
    from collector.upstream_detector import UPSTREAM_TABLE, ALERTS_TABLE
    assert calls[0].args[0] == UPSTREAM_TABLE
    assert calls[1].args[0] == ALERTS_TABLE
