from google.cloud import bigquery
import os

# “授权改造”：使用一个独特的对象作为未初始化的标记
_sentinel = object()
_bq_client = _sentinel

def get_bq_client():
    """获取BigQuery客户端(懒加载)"""
    global _bq_client
    if _bq_client is _sentinel:
        # 优先使用环境变量，如果不存在，则让GCP库自动发现
        project_id = os.environ.get("GCP_PROJECT_ID")
        _bq_client = bigquery.Client(
            project=project_id or os.environ.get("GCP_PROJECT", "wprojectl"),
            location=os.environ.get("GCP_LOCATION", "us-central1")
        )
    return _bq_client
