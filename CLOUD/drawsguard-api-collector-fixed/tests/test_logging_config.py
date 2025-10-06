import pytest
import logging
from unittest.mock import patch, MagicMock
import sys
import os

# 将应用目录添加到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.logging_config import setup_dual_logging
# 修正情报错误：正确的“弹药”名称是 'from google.auth.exceptions import DefaultCredentialsError'
from google.auth.exceptions import DefaultCredentialsError

@pytest.fixture(autouse=True)
def cleanup_logging_handlers():
    """在每次测试后，自动清理root logger上的所有handler，防止状态污染"""
    yield
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

def test_setup_dual_logging_standard():
    """
    测试“标准战况”：
    在有云端凭证的情况下，是否能同时配置好 Console 和 Cloud Logging handlers。
    """
    # 1. 模拟“卫星通讯”模块
    with patch('common.logging_config.cloud_logging.Client') as mock_gcp_client, \
         patch('common.logging_config.CloudLoggingHandler') as mock_cloud_handler_constructor:

        # 为我们的“假想敌”佩戴上正确的“军衔”
        mock_handler_instance = MagicMock()
        mock_handler_instance.level = logging.INFO
        mock_cloud_handler_constructor.return_value = mock_handler_instance

        # 2. 发起攻击（初始化情报系统）
        setup_dual_logging("test-service")

        # 3. 验证战果
        root_logger = logging.getLogger()

        # 验证“本地电台”和“卫星通讯”都已就位
        assert len(root_logger.handlers) == 2

        # 验证“本地电台”是正确的类型
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

        # 验证“卫星通讯”模块被正确调用
        mock_gcp_client.assert_called_once()
        mock_cloud_handler_constructor.assert_called_once_with(mock_gcp_client.return_value, name="test-service")

def test_setup_dual_logging_no_credentials():
    """
    测试“通讯中断”情景：
    在没有云端凭证时，“卫星通讯”会优雅失败，但“本地电台”依然正常工作。
    """
    # 1. 模拟“卫星通讯”模块，并让它在启动时就“坠毁”
    patch_target = 'common.logging_config.cloud_logging.Client'
    with patch(patch_target, side_effect=DefaultCredentialsError("No credentials")) as mock_gcp_client:

        # 2. 发起攻击
        setup_dual_logging("test-service-no-creds")

        # 3. 验证战果
        root_logger = logging.getLogger()

        # 验证最终只有一个“本地电台”在工作，我们的部队没有陷入通讯瘫痪
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

        # 验证我们的确尝试过启动“卫星通讯”
        mock_gcp_client.assert_called_once()
