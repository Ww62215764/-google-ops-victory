# collector/upstream_detector.py
import os
import uuid
import logging
from datetime import datetime, timezone
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

class UpstreamStaleException(Exception):
    """当上游API被检测到停更时抛出的自定义异常"""
    def __init__(self, message, alert_details=None):
        super().__init__(message)
        self.alert_details = alert_details

logger = logging.getLogger(__name__)

PROJECT = os.environ.get("GCP_PROJECT") or os.environ.get("PROJECT_ID", "wprojectl")
BQ_MONITORING = os.environ.get("BQ_MONITORING_DATASET", "pc28_monitoring")
UPSTREAM_TABLE = f"{PROJECT}.{BQ_MONITORING}.upstream_call_log"
ALERTS_TABLE = f"{PROJECT}.{BQ_MONITORING}.upstream_stale_alerts"

# 配置，可用环境变量覆盖
N_CHECK = int(os.environ.get("UPSTREAM_CHECK_N", "10"))       # 取最近 N 条
M_THRESHOLD = int(os.environ.get("UPSTREAM_M", "10"))        # 连续相同次数阈值
TIME_THRESHOLD_HOURS = int(os.environ.get("UPSTREAM_T_HOURS", "4"))

bq = bigquery.Client(project=PROJECT)

def log_upstream_call(collector_name: str, returned_period: int, response_json: str = None, call_ts: datetime = None):
    """将每次上游响应写入 upstream_call_log（使用 insert_rows_json）"""
    call_ts = call_ts or datetime.now(timezone.utc)
    row = {
        "call_ts": call_ts.isoformat(),
        "returned_period": int(returned_period),
        "collector": collector_name,
        "response_json": response_json or ""
    }
    try:
        errors = bq.insert_rows_json(UPSTREAM_TABLE, [row])
        if errors:
            logger.warning("BQ insert errors: %s", errors)
        else:
            logger.debug("Logged upstream call: %s %s", collector_name, returned_period)
    except GoogleAPIError as e:
        logger.exception("Failed to log upstream call: %s", e)

def get_last_n_returned_periods(collector_name: str, n: int = None):
    """查询最近 n 次 returned_period（按 call_ts 降序）并返回 list[int]"""
    n = n or N_CHECK
    sql = f"""
    SELECT returned_period, call_ts
    FROM `{UPSTREAM_TABLE}`
    WHERE collector = @collector
    ORDER BY call_ts DESC
    LIMIT @n
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("collector", "STRING", collector_name),
            bigquery.ScalarQueryParameter("n", "INT64", n),
        ]
    )
    try:
        q = bq.query(sql, job_config=job_config)
        rows = list(q.result())
        return [(int(r.returned_period), r.call_ts) for r in rows]
    except GoogleAPIError:
        logger.exception("Failed to query last n returned periods")
        return []

def mark_upstream_stale(
    collector_name: str,
    stale_period: int,
    first_seen,
    last_seen,
    consecutive_count: int,
    severity="WARNING",
    note=None,
):
    """写入 upstream_stale_alerts 并返回"""
    alert = {
        "alert_id": str(uuid.uuid4()),
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "collector": collector_name,
        "stale_period": int(stale_period),
        "consecutive_count": int(consecutive_count),
        "first_seen": first_seen.isoformat(),
        "last_seen": last_seen.isoformat(),
        "severity": severity,
        "note": note or ""
    }
    try:
        errors = bq.insert_rows_json(ALERTS_TABLE, [alert])
        if errors:
            logger.warning("Failed to insert stale alert to BQ: %s", errors)
        else:
            logger.info("Inserted upstream_stale_alert: period=%s count=%s", stale_period, consecutive_count)
    except GoogleAPIError:
        logger.exception("Failed to insert stale alert (BQ)")

    return alert


def detect_and_handle_upstream_stale(
    collector_name: str, returned_period: int, response_json: str = None, call_ts=None, send_alert_func=None
):
    """
    主函数：1) log call 2) check last N 3) if last M identical -> mark stale + optional send_alert
    send_alert_func(alert_dict) 由外部传入（例如发送 telegram 或 internal alerting）
    """
    call_ts = call_ts or datetime.now(timezone.utc)
    log_upstream_call(collector_name, returned_period, response_json, call_ts)

    last = get_last_n_returned_periods(collector_name, n=N_CHECK)
    if not last or len(last) < M_THRESHOLD:
        return None  # 不足样本

    # last is list of tuples (period, call_ts) in descending time order
    periods = [p for p, t in last]
    # check if first M are equal to returned_period
    if all(p == returned_period for p in periods[:M_THRESHOLD]):
        # compute first_seen and last_seen timestamps for these M entries
        first_seen = last[M_THRESHOLD - 1][1]  # oldest among the M
        last_seen = last[0][1]
        note = f"Detected {M_THRESHOLD} consecutive identical periods from upstream."
        # determine severity: by default WARNING; caller can escalate based on time window
        alert = mark_upstream_stale(
            collector_name,
            returned_period,
            first_seen,
            last_seen,
            consecutive_count=M_THRESHOLD,
            severity="CRITICAL", # 升级为CRITICAL，因为这将触发熔断
            note=note,
        )
        # optional: send alert (non-blocking)
        if send_alert_func:
            try:
                send_alert_func(alert)
            except Exception:
                logger.exception("send_alert_func failed")

        # 核心改动：抛出异常以触发熔断
        raise UpstreamStaleException(note, alert_details=alert)

    return None
