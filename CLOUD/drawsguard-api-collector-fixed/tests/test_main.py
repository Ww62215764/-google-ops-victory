import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import logging
from fastapi import BackgroundTasks, HTTPException
from requests.exceptions import RequestException
from starlette.requests import Request

# 将应用目录添加到sys.path，以便pytest可以找到main模块
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 核心修正：导入 main 模块以在测试函数中引用
import main
from main import app

@pytest.fixture(autouse=True)
def cleanup_singletons():
    """
    “战后清理部队”：自动重置所有在 main.py 中定义的全局单例状态。
    这是从 `test_common.py` 的战斗中吸取的宝贵经验。
    """
    yield
    main._secret_client = None
    main._cloud_logger = None
    main._monitoring_client = None

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
         patch('main.parse_and_insert_data', return_value={"success": True, "period": "20251007001"}) as mock_parser:

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
        mock_parser.assert_called_once()


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
        with TestClient(app):
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
         with TestClient(app):
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
    from main import call_api_with_retry, app

    # 让第一次攻击失败，第二次攻击成功
    mock_get.side_effect = [
        RequestException("Connection timed out"),
        MagicMock(status_code=200, json=lambda: {"codeid": 10000})
    ]

    # 执行带有重试逻辑的攻击
    # 我们需要一个真实的app context来获取api_key逻辑
    with TestClient(app):
         with patch('main.get_api_key', return_value='fake_key'):
              call_api_with_retry("http://fake.url", {'appid': '123'}, "fake_key")

    # 验证我们的部队，攻击了两次
    assert mock_get.call_count == 2

def test_docs_endpoint_is_skipped_by_middleware(client):
    """清除迷雾：验证监控中间件会“放行”对/docs端点的访问，不进行度量记录。"""
    with patch('main.MonitoringMiddleware.send_metrics') as mock_send_metrics:
        response = client.get("/docs")
        assert response.status_code == 200
        # 验证send_metrics完全没有被调用
        mock_send_metrics.assert_not_called()

def test_middleware_unhandled_exception_is_logged(client, caplog):
    """
    清除迷雾 - V8 最终决战之“既定事实”
    我们已经从无数次失败中确认，框架会捕获异常并阻止我们检查响应。
    因此，我们只验证我们能控制的最后一道防线：异常是否被正确记录。
    """
    # 核心战术：注入一个注定失败的路由
    @app.get("/__v8_error_route")
    async def v8_error_route():
        raise ValueError("V8 Engine Failure")

    try:
        with caplog.at_level(logging.ERROR):
            # 我们知道这次调用会抛出异常，这是框架的行为，我们接受这个事实
            try:
                client.get("/__v8_error_route")
            except ValueError:
                # 捕获并忽略框架抛出的异常，因为它不是我们测试的目标
                pass

        # 唯一重要的断言：我们的中间件是否尽职尽责地记录了异常？
        assert "Unhandled exception for GET /__v8_error_route" in caplog.text
        assert "V8 Engine Failure" in caplog.text

    finally:
        # 战后清理
        app.routes.pop()


@pytest.mark.asyncio
async def test_middleware_dispatch_logic_for_http_exception():
    """
    清除迷雾 - V9 最终决战之“显微镜”
    此测试使用“显微镜”般的精度，直接调用中间件的 dispatch 方法，
    绕过整个框架的复杂性，以确保我们能精确验证 HTTPException 的处理逻辑。
    """
    from main import MonitoringMiddleware

    middleware = MonitoringMiddleware(app=app)
    
    # 创建一个虚拟的请求
    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/microscope_test"

    # 创建一个必定会抛出 HTTPException 的 call_next 函数
    async def call_next_that_raises(request):
        raise HTTPException(status_code=418, detail="I'm a teapot")

    # 监视我们的度量发送函数
    with patch.object(middleware, 'send_metrics') as mock_send_metrics:
        # 我们期望 HTTPException 被重新抛出
        with pytest.raises(HTTPException):
            await middleware.dispatch(mock_request, call_next_that_raises)
    
    # 核心修正：由于 `dispatch` 中的 finally 块总会执行，且 `status_code` 会被正确设置，
    # 我们应该验证 `send_metrics` 是否被调用，即使有异常。
    # 失败原因：`response.background` 没有被设置和执行。
    # 我们需要一种方法来捕获 `add_task` 的参数。
    mock_background_tasks = MagicMock(spec=BackgroundTasks)
    with patch('main.BackgroundTasks', return_value=mock_background_tasks):
        with pytest.raises(HTTPException):
             await middleware.dispatch(mock_request, call_next_that_raises)

    # 验证 `add_task` 被调用
    mock_background_tasks.add_task.assert_called_once()
    # 验证 `add_task` 的参数是我们期望的 send_metrics 和它的参数
    args, kwargs = mock_background_tasks.add_task.call_args
    assert args[0] == middleware.send_metrics
    assert args[2] == mock_request.method # method
    assert args[3] == 418 # status_code


def test_middleware_http_exception_is_handled(client):
    """
    清除迷雾：验证中间件能够正确处理由端点抛出的HTTPException。
    """
    @app.get("/__http_exception_route")
    async def http_exception_route():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    try:
        response = client.get("/__http_exception_route")
        # 验证响应码是我们抛出的特定错误码
        assert response.status_code == 418
        assert response.json()["detail"] == "I'm a teapot"

    finally:
        # 战后清理
        app.routes.pop()


def test_send_metrics_handles_exception(caplog):
    """清除迷雾：测试当“度量系统”本身发生故障时，系统能记录日志而不会崩溃。"""
    from main import MonitoringMiddleware
    middleware = MonitoringMiddleware(app=app)

    # 模拟度量客户端初始化失败
    with patch('main.get_monitoring_client', side_effect=Exception("Monitoring client unavailable")):
        with caplog.at_level(logging.ERROR):
            middleware.send_metrics("/test", "GET", 200, 123.45)
    
    assert "Failed to send metrics" in caplog.text


@patch('main.secretmanager.SecretManagerServiceClient')
def test_get_secret_client_is_singleton(mock_client_constructor):
    """清除迷雾：验证 get_secret_client 函数遵循单例模式。"""
    client1 = main.get_secret_client()
    client2 = main.get_secret_client()
    assert client1 is client2
    mock_client_constructor.assert_called_once()


@patch('main.cloud_logging.Client')
def test_get_cloud_logger_is_singleton(mock_client_constructor):
    """清除迷雾：验证 get_cloud_logger 函数遵循单例模式。"""
    logger1 = main.get_cloud_logger()
    logger2 = main.get_cloud_logger()
    assert logger1 is logger2
    mock_client_constructor.assert_called_once()


@patch('main.get_secret_client')
def test_get_api_key_success(mock_get_secret_client):
    """清除迷雾：验证 get_api_key 在“通讯正常”时能成功获取并解码密钥。"""
    # 模拟一个“加密电报”
    mock_secret_payload = MagicMock()
    mock_secret_payload.payload.data.decode.return_value = "secret-key"
    
    # 模拟“情报终端”的行为
    mock_secret_client_instance = MagicMock()
    mock_secret_client_instance.access_secret_version.return_value = mock_secret_payload
    mock_get_secret_client.return_value = mock_secret_client_instance

    # 执行任务并验证结果
    api_key = main.get_api_key()
    assert api_key == "secret-key"
    mock_get_secret_client.assert_called_once()
    mock_secret_client_instance.access_secret_version.assert_called_once()


@patch('main.get_secret_client', side_effect=RequestException("Connection to Secret Manager failed"))
def test_get_api_key_failure(mock_get_secret_client):
    """清除迷雾：验证在“通讯中断”时，get_api_key 会在重试后最终失败。"""
    # 核心修正：抛出`RequestException`，因为这是`@sync_retry`装饰器设计用来捕获的异常类型。
    with pytest.raises(RequestException, match="Connection to Secret Manager failed"):
        main.get_api_key()
    
    # sync_retry 装饰器默认重试3次
    assert mock_get_secret_client.call_count == 3


def test_parse_and_insert_data_success():
    """清除迷雾：验证 `parse_and_insert_data` 能正确解析“标准情报”并派发后台任务。"""
    mock_tasks = MagicMock(spec=BackgroundTasks)
    api_data = {
        "retdata": {
            "curent": {
                "long_issue": "20251007001",
                "number": ["1", "2", "3"]
            }
        }
    }
    result = main.parse_and_insert_data(api_data, mock_tasks)
    
    assert result == {"success": True, "period": "20251007001"}
    # 验证后台插入任务已被添加
    mock_tasks.add_task.assert_called_once()
    # 验证传递给后台任务的数据是正确的
    args, kwargs = mock_tasks.add_task.call_args
    assert args[0] == main._insert_draw_with_merge
    # 简单验证关键字段
    assert args[1]["period"] == "20251007001"
    assert args[1]["sum_value"] == 6


def test_parse_and_insert_data_missing_period():
    """清除迷雾：验证当“情报”中缺少关键的“期号”字段时，函数能正确抛出异常。"""
    mock_tasks = MagicMock(spec=BackgroundTasks)
    api_data = {"retdata": {"curent": {"number": ["1", "2", "3"]}}}
    
    with pytest.raises(ValueError, match="关键字段缺失: long_issue"):
        main.parse_and_insert_data(api_data, mock_tasks)
    
    mock_tasks.add_task.assert_not_called()


@patch('main.get_bq_client')
def test_insert_draw_with_merge_inserted(mock_get_bq_client):
    """清除迷雾：验证当 MERGE 语句成功插入新行时，函数返回 'inserted'。"""
    mock_bq_instance = MagicMock()
    mock_query_job = MagicMock()
    mock_query_job.num_dml_affected_rows = 1
    mock_bq_instance.query.return_value = mock_query_job
    mock_get_bq_client.return_value = mock_bq_instance
    
    row_to_insert = {"period": "20251007999"}
    result = main._insert_draw_with_merge(row_to_insert)
    
    assert result == "inserted"
    mock_bq_instance.query.assert_called_once()


@patch('main.get_bq_client')
def test_insert_draw_with_merge_skipped(mock_get_bq_client):
    """清除迷雾：验证当 MERGE 语句没有插入新行时（因为期号已存在），函数返回 'skipped'。"""
    mock_bq_instance = MagicMock()
    mock_query_job = MagicMock()
    mock_query_job.num_dml_affected_rows = 0
    mock_bq_instance.query.return_value = mock_query_job
    mock_get_bq_client.return_value = mock_bq_instance
    
    row_to_insert = {"period": "20251007999"}
    result = main._insert_draw_with_merge(row_to_insert)
    
    assert result == "skipped"
    mock_bq_instance.query.assert_called_once()


def test_health_endpoint_for_coverage(client):
    """
    清除迷雾：这是一个“炮灰”测试，其唯一目的是为了在覆盖率报告中，
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
