#!/usr/bin/env python3
"""
AI Industrial Evolution Game (AIEG) - Data Collector
AI工业进化预测小游戏 - 数据采集服务
版本: 7.1.0 - Evolution (进化)

这是一个自主开奖、自主预测的彩票类型小游戏系统
"""

import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, List, Optional

import pytz
import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from google.cloud import bigquery, secretmanager
from google.cloud import logging as cloud_logging
from google.cloud import monitoring_v3
from pydantic import BaseModel
from requests.exceptions import RequestException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from collector.upstream_detector import (  # noqa: E402
    UpstreamStaleException,
    detect_and_handle_upstream_stale,
)
from common.bigquery_client import get_bq_client  # noqa: E402
from common.logging_config import setup_dual_logging  # noqa: E402

# Telegram
# from common.utils import sync_retry # No longer needed
# 内部模块
# FastAPI and Middleware
# Google Cloud
# Pydantic

# ================= 创世：内置重试装饰器 =================

def sync_retry(max_retries=3, delay_seconds=1, backoff_factor=2):
    """
    一个内置的、自给自足的同步重试装饰器，现在能够精确处理网络异常。
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = delay_seconds
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (RequestException, HTTPException) as e:
                    # 只对网络错误和5xx系列的服务端错误进行重试
                    if isinstance(e, HTTPException) and e.status_code < 500:
                        raise  # 对于4xx客户端错误，不应重试，直接抛出

                    retries += 1
                    if retries >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries.",
                            exc_info=True,
                        )
                        raise
                    log_msg = (
                        f"Function {func.__name__} failed ({retries}/{max_retries}) "
                        f"due to network/server error. Retrying in {delay:.2f} seconds..."
                    )
                    logger.warning(log_msg, exc_info=True)
                    time.sleep(delay)
                    delay *= backoff_factor
                    delay += random.uniform(0, 0.1)  # Jitter

        return wrapper

    return decorator


# ================= 应用程序上下文与单例管理 =================

class AppContext:
    """
    一个用于管理应用程序生命周期内的单例客户端的容器。
    这避免了全局变量，并使依赖关系更加明确。
    """
    def __init__(self):
        self._secret_client = None
        self._monitoring_client = None
        self._cloud_logger = None

    @property
    def secret_client(self):
        if self._secret_client is None:
            self._secret_client = secretmanager.SecretManagerServiceClient()
        return self._secret_client

    @property
    def monitoring_client(self):
        if self._monitoring_client is None:
            logger.info("Initializing Google Cloud Monitoring client...")
            self._monitoring_client = monitoring_v3.MetricServiceClient()
        return self._monitoring_client

    @property
    def cloud_logger(self):
        if self._cloud_logger is None:
            _logging_client = cloud_logging.Client(project=GCP_PROJECT_ID)
            self._cloud_logger = _logging_client.logger("drawsguard-api-collector-smart")
        return self._cloud_logger

# 在应用程序启动时创建上下文的单个实例
app_context = AppContext()

# ================= 全局配置与客户端 =================
setup_dual_logging(service_name="drawsguard-api-collector")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrawsGuard API Collector v7.0 (Phoenix)",
    description="云端数据采集服务(全域战场观测系统 - 不死鸟版)",
    version="7.0.0",
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "wprojectl")
MONITORING_METRIC_PREFIX = "custom.googleapis.com/drawsguard"
METRIC_REQUEST_COUNT = f"{MONITORING_METRIC_PREFIX}/requests_total"
METRIC_ERROR_COUNT = f"{MONITORING_METRIC_PREFIX}/errors_total"
METRIC_LATENCY = f"{MONITORING_METRIC_PREFIX}/latency_ms"


# ================= 监控中间件 =================
class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to capture and send monitoring metrics for each request.

    This middleware records the total number of requests, errors, and the
    latency for each endpoint, sending this data to Google Cloud Monitoring.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        start_time = time.time()
        if request.url.path in ["/docs", "/openapi.json"]:
            return await call_next(request)
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            if isinstance(e, HTTPException):
                status_code = e.status_code
            else:
                logger.error(
                    f"Unhandled exception for {request.method} {request.url.path}: {e}",
                    exc_info=True,
                )
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            background = BackgroundTasks()
            background.add_task(
                self.send_metrics,
                request.url.path,
                request.method,
                status_code,
                latency_ms,
            )
            if response:
                response.background = background
        return response

    def send_metrics(self, path: str, method: str, status_code: int, latency_ms: float):
        """Sends request metrics to Google Cloud Monitoring."""
        try:
            client = app_context.monitoring_client
            project_name = f"projects/{GCP_PROJECT_ID}"
            is_error = status_code >= 400
            common_labels = {
                "service": "drawsguard-api-collector",
                "endpoint": path,
                "method": method,
                "status_code": str(status_code),
            }
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            self._write_metric(
                client,
                project_name,
                METRIC_REQUEST_COUNT,
                1,
                interval,
                common_labels,
                "INT64",
            )
            if is_error:
                self._write_metric(
                    client,
                    project_name,
                    METRIC_ERROR_COUNT,
                    1,
                    interval,
                    common_labels,
                    "INT64",
                )
            self._write_metric(
                client,
                project_name,
                METRIC_LATENCY,
                latency_ms,
                interval,
                common_labels,
                "DOUBLE",
            )
            logger.debug(
                f"Metrics sent for {path}: latency={latency_ms:.2f}ms, status={status_code}"
            )
        except Exception as e:
            logger.error(f"Failed to send metrics: {e}", exc_info=True)

    def _write_metric(
        self, client, project_name, metric_type, value, interval, labels, value_type
    ):
        """Constructs and writes a TimeSeries metric to Google Cloud Monitoring."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = metric_type
        series.metric.labels.update(labels)
        series.resource.type = "global"
        point = monitoring_v3.Point({"interval": interval})
        if value_type == "INT64":
            point.value.int64_value = int(value)
        elif value_type == "DOUBLE":
            point.value.double_value = float(value)
        series.points = [point]
        client.create_time_series(name=project_name, time_series=[series])


app.add_middleware(MonitoringMiddleware)


# ================= Pydantic Models & Global Config =================
class HealthCheckResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str = "ok"


class BigQueryDrawRow(BaseModel):
    """Defines the schema for a draw data row in BigQuery."""

    period: str
    timestamp: datetime
    numbers: List[int]
    sum_value: int
    big_small: str
    odd_even: str
    next_issue: Optional[str] = None
    next_time: Optional[datetime] = None
    award_countdown: Optional[int] = None
    api_server_time: Optional[datetime] = None
    clock_drift_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime


SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")
UTC_TZ = pytz.utc


@sync_retry()
def get_api_key():
    """Retrieves the API key from Google Cloud Secret Manager with retry logic."""
    client = app_context.secret_client
    name = f"projects/{GCP_PROJECT_ID}/secrets/aieg-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def generate_sign(params: dict, api_key: str) -> str:
    """Generates the required MD5 signature for an API call."""
    s_keys = sorted([k for k, v in params.items() if v is not None and v != ""])
    sign_str = "".join([f"{k}{params[k]}" for k in s_keys]) + api_key
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


@sync_retry(max_retries=3)
def call_api_with_retry(api_url: str, params: dict, api_key: str) -> dict:
    """
    Calls the external API with retry logic.

    Args:
        api_url: The URL of the API endpoint.
        params: A dictionary of query parameters.
        api_key: The API key for signing the request.

    Returns:
        The JSON response from the API as a dictionary.
    """
    params["time"] = int(time.time())
    params["sign"] = generate_sign(params, api_key)
    logger.info(f"API Call: {api_url} with params: {params}")
    response = requests.get(
        api_url, params=params, timeout=10, headers={"User-Agent": "DrawsGuard/7.0"}
    )
    response.raise_for_status()
    return response.json()


def _insert_draw_with_merge(row: Dict[str, Any]) -> str:
    """
    Inserts a data row into BigQuery using a MERGE statement to prevent duplicates.

    Args:
        row: A dictionary representing the data row to be inserted.

    Returns:
        A string indicating whether the row was 'inserted' or 'skipped'.
    """
    bq_client = get_bq_client()
    table_id = f"{GCP_PROJECT_ID}.drawsguard.draws"
    merge_sql = (
        f"MERGE `{table_id}` T USING (SELECT @period AS period) S "
        f"ON T.period = S.period WHEN NOT MATCHED THEN INSERT ROW"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("period", "STRING", row["period"])
        ]
    )
    query_job = bq_client.query(merge_sql, job_config=job_config)
    query_job.result()
    return "inserted" if query_job.num_dml_affected_rows > 0 else "skipped"


def parse_and_insert_data(api_data: dict, background_tasks: BackgroundTasks) -> dict:
    """
    Parses the API response, validates the data, and queues it for background insertion.

    Args:
        api_data: The raw dictionary data from the API response.
        background_tasks: The FastAPI BackgroundTasks instance to queue the insertion.

    Returns:
        A dictionary indicating the success and the processed period number.
    """
    curent = api_data.get("retdata", {}).get("curent", {})
    period = str(curent.get("long_issue", ""))
    if not period:
        raise ValueError("关键字段缺失: long_issue")
    now_utc = datetime.now(UTC_TZ)
    raw_row = {
        "period": period,
        "timestamp": now_utc,
        "numbers": curent.get("number", []),
        "sum_value": sum(int(n) for n in curent.get("number", [])),
        "big_small": "BIG",
        "odd_even": "ODD",
        "created_at": now_utc,
        "updated_at": now_utc,
    }
    validated_row = BigQueryDrawRow.model_validate(raw_row)
    background_tasks.add_task(
        _insert_draw_with_merge, validated_row.model_dump(mode="json")
    )
    logger.info(f"Data for period {period} processed and insertion queued.")
    return {"success": True, "period": period}


# ================= Endpoints =================
@app.get("/health", response_model=HealthCheckResponse, tags=["Monitoring"])
async def health_check():
    """Provides a simple health check endpoint."""
    return HealthCheckResponse(status="ok")


@app.post("/collect", tags=["Core"])
async def collect(background_tasks: BackgroundTasks):
    """Triggers the data collection and processing pipeline."""
    try:
        logger.info("=" * 50)
        logger.info("V7.0 (Phoenix) Collector Pipeline Started")
        api_key = get_api_key()
        api_url = "https://rijb.api.storeapi.net/api/119/259"
        params = {"appid": "45928", "format": "json"}
        data = call_api_with_retry(api_url, params, api_key)
        if data.get("codeid") != 10000:
            raise HTTPException(
                status_code=502, detail=f"API Error: {data.get('message', 'Unknown')}"
            )
        current_period_str = data.get("retdata", {}).get("curent", {}).get("long_issue")
        if current_period_str:
            detect_and_handle_upstream_stale(
                collector_name="aieg_main_api",
                returned_period=int(current_period_str),
                response_json=json.dumps(data),
            )
        result = parse_and_insert_data(data, background_tasks)
        logger.info("V7.0 (Phoenix) Collector Pipeline Finished Successfully")
        logger.info("=" * 50)
        return {"status": "success", "result": result}
    except UpstreamStaleException as e:
        logger.warning(f"CIRCUIT BREAKER TRIPPED: {e}")
        raise HTTPException(
            status_code=429, detail=f"Upstream is stale, halting requests: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Collector pipeline failed: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Internal Server Error") from e


@app.on_event("shutdown")
def shutdown_event():
    """Logs a message when the application is shutting down."""
    logger.info("服务关闭。")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
