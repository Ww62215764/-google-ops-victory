import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

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
