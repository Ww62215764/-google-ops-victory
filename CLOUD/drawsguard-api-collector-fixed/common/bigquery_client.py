from google.cloud import bigquery
import os

_bq_client = None

def get_bq_client():
    """获取BigQuery客户端(懒加载)"""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(
            project=os.environ.get("GCP_PROJECT", "wprojectl"),
            location=os.environ.get("GCP_LOCATION", "us-central1")
        )
    return _bq_client
