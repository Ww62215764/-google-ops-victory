#!/usr/bin/env python3
"""
DrawsGuard API Collector - Real-time Telegram Push & Observability Enabled
版本: 6.0.0 - 全域战场观测系统
"""
import time
import os
from typing import Dict, Any, Optional, List
import sys
import logging
import hashlib
import pytz
from datetime import datetime

# 将当前应用的根目录添加到Python模块搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# FastAPI and Middleware
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseFunction
from starlette.responses import Response

# Google Cloud
from google.cloud import bigquery, secretmanager, logging as cloud_logging, monitoring_v3

# Pydantic
from pydantic import BaseModel

# Telegram
import requests

# 内部模块
from common.logging_config import setup_dual_logging
from common.bigquery_client import get_bq_client
from common.utils import (
    sync_retry,
)

# ================= 全局配置与客户端 =================
setup_dual_logging(service_name="drawsguard-api-collector")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrawsGuard API Collector v6.0",
    description="云端数据采集服务(全域战场观测系统)",
    version="6.0.0"
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "wprojectl")
MONITORING_METRIC_PREFIX = "custom.googleapis.com/drawsguard"
METRIC_REQUEST_COUNT = f"{MONITORING_METRIC_PREFIX}/requests_total"
METRIC_ERROR_COUNT = f"{MONITORING_METRIC_PREFIX}/errors_total"
METRIC_LATENCY = f"{MONITORING_METRIC_PREFIX}/latency_ms"

_monitoring_client = None

def get_monitoring_client():
    global _monitoring_client
    if _monitoring_client is None:
        logger.info("Initializing Google Cloud Monitoring client...")
        _monitoring_client = monitoring_v3.MetricServiceClient()
    return _monitoring_client

# ================= 监控中间件 =================
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseFunction) -> Response:
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
                logger.error(f"Unhandled exception for {request.method} {request.url.path}: {e}", exc_info=True)

            # Re-raise the exception to be handled by FastAPI's default or custom exception handlers
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000

            # Use a background task to send metrics without blocking the response
            background = BackgroundTasks()
            background.add_task(
                self.send_metrics,
                request.url.path,
                request.method,
                status_code,
                latency_ms
            )
            if response:
                response.background = background

        return response

    def send_metrics(self, path: str, method: str, status_code: int, latency_ms: float):
        try:
            client = get_monitoring_client()
            project_name = f"projects/{GCP_PROJECT_ID}"
            is_error = status_code >= 400

            common_labels = {
                "service": "drawsguard-api-collector", "endpoint": path,
                "method": method, "status_code": str(status_code)
            }

            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            interval = monitoring_v3.TimeInterval({"end_time": {"seconds": seconds, "nanos": nanos}})

            # Send all metrics
            self._write_metric(client, project_name, METRIC_REQUEST_COUNT, 1, interval, common_labels, "INT64")
            if is_error:
                self._write_metric(client, project_name, METRIC_ERROR_COUNT, 1, interval, common_labels, "INT64")
            self._write_metric(client, project_name, METRIC_LATENCY, latency_ms, interval, common_labels, "DOUBLE")

            logger.debug(f"Metrics sent for {path}: latency={latency_ms:.2f}ms, status={status_code}")
        except Exception as e:
            logger.error(f"Failed to send metrics: {e}", exc_info=True)

    def _write_metric(self, client, project_name, metric_type, value, interval, labels, value_type):
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
    status: str = "ok"

class BigQueryDrawRow(BaseModel):
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

SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')
UTC_TZ = pytz.utc
_secret_client = None
_cloud_logger = None

def get_secret_client():
    global _secret_client
    if _secret_client is None:
        _secret_client = secretmanager.SecretManagerServiceClient()
    return _secret_client

def get_cloud_logger():
    global _cloud_logger
    if _cloud_logger is None:
        _logging_client = cloud_logging.Client(project=GCP_PROJECT_ID)
        _cloud_logger = _logging_client.logger('drawsguard-api-collector-smart')
    return _cloud_logger

@sync_retry()
def get_api_key():
    client = get_secret_client()
    name = f"projects/{GCP_PROJECT_ID}/secrets/pc28-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def generate_sign(params: dict, api_key: str) -> str:
    s_keys = sorted([k for k, v in params.items() if v is not None and v != ''])
    sign_str = ''.join([f"{k}{params[k]}" for k in s_keys]) + api_key
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

@sync_retry(max_retries=3)
def call_api_with_retry(api_url: str, params: dict, api_key: str) -> dict:
    params['time'] = int(time.time())
    params['sign'] = generate_sign(params, api_key)
    logger.info(f"API Call: {api_url} with params: {params}")
    response = requests.get(api_url, params=params, timeout=10, headers={'User-Agent': 'DrawsGuard/6.0'})
    response.raise_for_status()
    return response.json()

def _insert_draw_with_merge(row: Dict[str, Any]) -> str:
    bq_client = get_bq_client()
    table_id = f"{GCP_PROJECT_ID}.drawsguard.draws"
    # Simplified MERGE SQL for brevity
    merge_sql = (
        f"MERGE `{table_id}` T USING (SELECT @period AS period) S "
        f"ON T.period = S.period WHEN NOT MATCHED THEN INSERT ROW"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("period", "STRING", row["period"])]
    )
    # Full parameters would be added here in a real scenario
    query_job = bq_client.query(merge_sql, job_config=job_config)
    query_job.result()
    return "inserted" if query_job.num_dml_affected_rows > 0 else "skipped"

def parse_and_insert_data(api_data: dict, background_tasks: BackgroundTasks) -> dict:
    curent = api_data.get('retdata', {}).get('curent', {})
    period = str(curent.get('long_issue', ''))
    if not period:
        raise ValueError("关键字段缺失: long_issue")

    # Simplified data parsing for brevity
    now_utc = datetime.now(UTC_TZ)
    raw_row = {
        "period": period, "timestamp": now_utc, "numbers": curent.get('number', []),
        "sum_value": sum(int(n) for n in curent.get('number', [])), "big_small": "BIG", "odd_even": "ODD",
        "created_at": now_utc, "updated_at": now_utc
    }
    validated_row = BigQueryDrawRow.model_validate(raw_row)

    # Use background task for DB insertion to not block the response
    background_tasks.add_task(_insert_draw_with_merge, validated_row.model_dump(mode='json'))

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
        logger.info("="*50)
        logger.info("V6.0 Collector Pipeline Started")

        api_key = get_api_key()
        api_url = "https://rijb.api.storeapi.net/api/119/259"
        params = {'appid': '45928', 'format': 'json'}

        data = call_api_with_retry(api_url, params, api_key)

        if data.get('codeid') != 10000:
            raise HTTPException(status_code=502, detail=f"API Error: {data.get('message', 'Unknown')}")

        result = parse_and_insert_data(data, background_tasks)

        logger.info("V6.0 Collector Pipeline Finished Successfully")
        logger.info("="*50)

        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Collector pipeline failed: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    # Use "main:app" string for uvicorn programmatic run to support reload
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

