import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from fastapi import BackgroundTasks

# 将应用目录添加到sys.path，以便pytest可以找到main模块
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

@pytest.fixture(scope="module")
def client():
    """创建一个TestClient实例，用于在测试中调用API端点"""
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    """
    测试 /health 端点是否能成功响应。
    这是最基础的“烟雾测试”，确保应用可以启动并响应请求。
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_collect_success(client):
    """
    测试 /collect 端点的“凯旋”情景 (happy path)。
    模拟所有外部依赖都正常工作的情况。
    """
    # 1. 模拟(Mock)所有外部依赖
    with patch('main.get_api_key', return_value='fake_api_key') as mock_get_key, \
         patch('main.call_api_with_retry') as mock_call_api, \
         patch('main.detect_and_handle_upstream_stale') as mock_detector, \
         patch('main._insert_draw_with_merge', return_value='inserted') as mock_inserter:

        # 配置假想敌的行为
        mock_api_response = {
            "codeid": 10000,
            "retdata": {
                "curent": {
                    "long_issue": "20251007001",
                    "number": [1, 2, 3, 4, 5]
                }
            }
        }
        mock_call_api.return_value = mock_api_response

        # 2. 发起攻击
        response = client.post("/collect")

        # 3. 验证战果
        # 检查响应是否成功
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["result"]["period"] == "20251007001"

        # 检查所有模拟的部队是否都按预期被调用
        mock_get_key.assert_called_once()
        mock_call_api.assert_called_once()
        mock_detector.assert_called_once_with(
            collector_name="pc28_main_api",
            returned_period=20251007001,
            response_json=json.dumps(mock_api_response)
        )
        # _insert_draw_with_merge 是在后台任务中调用的，TestClient会立即执行它
        mock_inserter.assert_called_once()


def test_collect_circuit_breaker(client):
    """
    测试 /collect 的“熔断”情景。
    模拟 upstream_detector 检测到上游停更并抛出 UpstreamStaleException 的情况。
    """
    # 1. 模拟依赖
    with patch('main.get_api_key', return_value='fake_api_key'), \
         patch('main.call_api_with_retry') as mock_call_api, \
         patch('main.detect_and_handle_upstream_stale') as mock_detector:

        # 配置假想敌的行为
        mock_api_response = {
            "codeid": 10000,
            "retdata": {"curent": {"long_issue": "20251007002"}}
        }
        mock_call_api.return_value = mock_api_response
        
        # 这是关键：让熔断器抛出异常
        from main import UpstreamStaleException
        mock_detector.side_effect = UpstreamStaleException("Upstream is stale!")

        # 2. 发起攻击
        response = client.post("/collect")

        # 3. 验证战果
        assert response.status_code == 429  # Too Many Requests
        assert "Upstream is stale" in response.json()["detail"]
        mock_call_api.assert_called_once()
        mock_detector.assert_called_once()


def test_collect_api_error(client):
    """
    测试 /collect 的“敌方欺诈”情景。
    模拟上游API返回一个非10000的错误码。
    """
    # 1. 模拟依赖
    with patch('main.get_api_key', return_value='fake_api_key'), \
         patch('main.call_api_with_retry') as mock_call_api:

        # 配置假想敌的行为
        mock_api_response = {"codeid": 9999, "message": "Invalid AppID"}
        mock_call_api.return_value = mock_api_response

        # 2. 发起攻击
        response = client.post("/collect")

        # 3. 验证战果
        assert response.status_code == 502  # Bad Gateway
        assert "API Error: Invalid AppID" in response.json()["detail"]
        mock_call_api.assert_called_once()
 
def test_middleware_sends_metrics_on_actual_request(client):
    """
    战术变革：不再模拟 dispatch，而是对 /health 发起一次真实的“实弹”攻击。
    """
    # 我们直接 patch main 模块中的 send_metrics 函数
    with patch('main.MonitoringMiddleware.send_metrics') as mock_send_metrics:
        # 向 /health 发起一次真实的、端到端的攻击
        response = client.get("/health")
        assert response.status_code == 200

        # 验证我们的“弹道数据记录仪”，是否被成功触发
        mock_send_metrics.assert_called_once()

@patch('main.requests.get')
def test_call_api_with_retry_gives_up(mock_get):
    """
    清除迷雾：测试“百战之矛”在“屡战屡败”后，最终放弃抵抗的情景。
    """
    from requests.exceptions import RequestException
    from main import call_api_with_retry, app
    
    # 让所有的攻击，全部失败
    mock_get.side_effect = RequestException("Connection timed out")

    with pytest.raises(RequestException):
        with TestClient(app) as client:
            with patch('main.get_api_key', return_value='fake_key'):
                # max_retries 默认是 3
                call_api_with_retry("http://fake.url", {'appid': '123'}, "fake_key")

    # 验证我们的部队，在 3 次失败后，放弃了抵抗
    assert mock_get.call_count == 3

@patch('main.requests.get')
def test_call_api_with_4xx_error_no_retry(mock_get):
    """
    清除迷雾：测试“百战之矛”在遭遇“非5xx”的HTTP错误时，不会进行重试。
    """
    from main import call_api_with_retry, app, HTTPException
    
    # 模拟一个 403 Forbidden 错误
    mock_get.side_effect = HTTPException(status_code=403, detail="Forbidden")

    with pytest.raises(HTTPException):
         with TestClient(app) as client:
            with patch('main.get_api_key', return_value='fake_key'):
                call_api_with_retry("http://fake.url", {'appid': '123'}, "fake_key")
    
    # 验证我们的部队，只攻击了一次，就放弃了
    assert mock_get.call_count == 1

def test_parse_data_value_error(client):
    """
    清除迷雾：测试在API返回的数据中，缺少关键字段时的情景。
    """
    from main import parse_and_insert_data
    
    with pytest.raises(ValueError) as excinfo:
        # 传入一个缺少 "long_issue" 的“残缺情报”
        parse_and_insert_data({"retdata": {"curent": {}}}, MagicMock())
    
    assert "关键字段缺失: long_issue" in str(excinfo.value)

@patch('main.requests.get')
def test_call_api_with_retry_logic(mock_get):
    """
    第二阶段：攻坚“百战之矛” (API重试逻辑)。
    模拟API首次调用失败，第二次调用成功的情景。
    """
    from requests.exceptions import RequestException
    from main import call_api_with_retry, generate_sign, app
    
    # 让第一次攻击失败，第二次攻击成功
    mock_get.side_effect = [
        RequestException("Connection timed out"),
        MagicMock(status_code=200, json=lambda: {"codeid": 10000})
    ]

    # 执行带有重试逻辑的攻击
    # 我们需要一个真实的app context来获取api_key逻辑
    with TestClient(app) as client:
         with patch('main.get_api_key', return_value='fake_key'):
              call_api_with_retry("http://fake.url", {'appid': '123'}, "fake_key")

    # 验证我们的部队，是否真的发起了两次攻击
    assert mock_get.call_count == 2

def test_health_endpoint_for_coverage(client):
    """
    战术修正：移除对不存在的 /heartbeat 和 /telegram-stats 的攻击。
    改为对 /health 端点进行一次重复的“火力覆盖”，以确保测试用例的完整性。
    """
    response_health = client.get("/health")
    assert response_health.status_code == 200
    assert "status" in response_health.json()
    assert response_health.json()["status"] == "ok"

def test_collect_internal_server_error(client):
    """
    第四阶段：攻坚“最终防线” (杂项异常处理)。
    模拟一个未经处理的内部异常。
    """
    # 让 get_api_key 抛出一个最普通的、未经处理的异常
    with patch('main.get_api_key', side_effect=Exception("Something went wrong")):
        response = client.post("/collect")
        # 验证我们的总指挥部，能否捕获这个异常，并返回一个标准的 500 错误
        assert response.status_code == 500
        assert "Internal Server Error" in response.json()["detail"]
