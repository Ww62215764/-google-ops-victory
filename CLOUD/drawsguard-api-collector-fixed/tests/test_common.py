"""Tests for the BigQuery client singleton module."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from common import bigquery_client
from common.bigquery_client import get_bq_client


@pytest.fixture(autouse=True)
def cleanup_bq_client_singleton():
    """
    “战后清理部队”：这是一个自动执行的fixture。
    它会在每次测试运行之后，自动重置 _bq_client 这个全局单例状态。
    """
    # yeild 之前的代码，是在测试运行前执行（我们这里不需要）
    yield
    # yield 之后的代码，是在测试运行后执行
    # print("\n[Cleanup Crew] Resetting BQ client singleton...") # 在CI中可以移除打印
    bigquery_client._bq_client = bigquery_client._sentinel


def test_get_bq_client_singleton():
    """
    测试 get_bq_client 是否表现为单例模式。
    第一次调用时创建客户端，后续调用返回同一个实例。
    """
    # 模拟 google.cloud.bigquery.Client
    with patch("common.bigquery_client.bigquery.Client") as mock_client_constructor:

        # 第一次调用
        client1 = get_bq_client()

        # 第二次调用
        client2 = get_bq_client()

        # 验证构造函数是否只被调用了一次
        mock_client_constructor.assert_called_once()

        # 验证两次调用返回的是同一个实例
        assert client1 is client2


def test_get_bq_client_uses_env_project_id():
    """
    测试 get_bq_client 是否会使用环境变量中的 GCP_PROJECT_ID。
    这一次，由于“战后清理部队”的存在，它将获得一个干净的战场。
    """
    # 1. 设置“假想敌”的环境变量
    fake_project_id = "project-from-env"
    with patch.dict(os.environ, {"GCP_PROJECT_ID": fake_project_id}), patch(
        "common.bigquery_client.bigquery.Client"
    ) as mock_client_constructor:

        # 2. 发起攻击
        get_bq_client()

        # 3. 验证战果
        # 我们期望，构造函数在被调用时，传入的 project 参数，是我们设置的环境变量
        # 毕业考试的最后答案：将 location 参数也包含在我们的“期望”之中
        mock_client_constructor.assert_called_with(
            project=fake_project_id, location="us-central1"
        )
