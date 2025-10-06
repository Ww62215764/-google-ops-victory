#!/usr/bin/env python3
"""
DrawsGuard API Collector - Real-time Telegram Push Version
实时Telegram推送版本:每期开奖即时推送到Telegram

核心功能:
- 智能调度:根据award_countdown动态调整采集频率
- 实时推送:每期开奖结果立即推送到Telegram(真正的异步)
- 零延迟:BackgroundTasks异步推送,零阻塞主流程
- 高可靠性:带重试机制和失败通知

调度逻辑:
- countdown > 60秒:正常模式(由Scheduler触发)
- 0 < countdown ≤ 60秒:密集模式(自动触发3次额外采集)
- countdown ≤ -300秒:节能模式(记录但不额外操作)

作者: 15年数据架构专家
日期: 2025-10-04
版本: 5.2.0 - 结构修复版
"""

import uuid
import json
import os
from typing import Dict, Any, Optional
import sys

# 将当前应用的根目录添加到Python模块搜索路径中
# 这是为了确保在任何环境下都能正确找到 aac_common 和 collector 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 内部模块
from collector.upstream_detector import detect_and_handle_upstream_stale
from common.logging_config import setup_dual_logging
from common.bigquery_client import get_bq_client
from common.utils import (
    async_retry,
    sync_retry,
    get_telegram_config,
    update_telegram_push_stats,
    get_last_issue_from_db,
    PC28Exception,
    get_http_status_code,
)

from google.cloud import bigquery, secretmanager, logging as cloud_logging
import requests
import hashlib
from telegram import Bot
from telegram.constants import ParseMode


# Configure logging at the application's entry point
# This will set up handlers for both console and Google Cloud Logging
setup_dual_logging(service_name="drawsguard-api-collector")

# Get a logger for the current module
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrawsGuard API Collector v5.2",
    description="云端数据采集服务(真正的异步Telegram推送版, 结构已修复)",
    version="5.2.0"
)

# ================= Pydantic Models for Validation =================

class HealthCheckResponse(BaseModel):
    status: str = "ok"

class BigQueryDrawRow(BaseModel):
    period: str = Field(..., description="期号")
    timestamp: datetime = Field(..., description="开奖时间 (UTC)")
    numbers: List[int] = Field(..., min_items=3, max_items=3, description="开奖号码")
    sum_value: int = Field(..., ge=0, le=27, description="和值")
    big_small: str = Field(..., pattern="^(BIG|SMALL)$", description="大小")
    odd_even: str = Field(..., pattern="^(ODD|EVEN)$", description="奇偶")
    next_issue: str | None = Field(None, description="下期期号")
    next_time: datetime | None = Field(None, description="下期时间 (UTC)")
    award_countdown: int | None = Field(None, description="开奖倒计时")
    api_server_time: datetime | None = Field(None, description="API服务器时间 (UTC)")
    clock_drift_ms: int | None = Field(None, description="时钟漂移(毫秒)")
    created_at: datetime = Field(..., description="记录创建时间 (UTC)")
    updated_at: datetime = Field(..., description="记录更新时间 (UTC)")


# ================= Global Clients and Config =================

# 初始化GCP客户端(懒加载)
_bq_client = None
_secret_client = None
_logging_client = None
_cloud_logger = None

# 时区配置
SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')
UTC_TZ = pytz.utc

# 智能调度配置 - 优化延迟
INTENSIVE_MODE_THRESHOLD = 60  # 开奖前60秒进入密集模式
INTENSIVE_INTERVALS = [10, 10, 10]  # 密集模式:每10秒采集一次(减少延迟)
ENERGY_SAVE_THRESHOLD = -300  # 开奖后5分钟进入节能模式(记录但不额外操作)

# 延迟优化配置
MAX_ACCEPTABLE_DELAY = 30  # 最大可接受延迟30秒
DELAY_OPTIMIZATION_THRESHOLD = 45  # 超过45秒时启用额外采集

# Telegram推送优化配置
TELEGRAM_PUSH_CONFIG = {
    "max_retries": 3,                    # 最大重试次数
    "timeout_seconds": 5,               # 请求超时时间
    "retry_backoff_base": 2,            # 重试退避基数(指数退避)
    "failure_notification_enabled": True, # 启用失败通知
    "async_mode": True,                 # 异步模式开关
    "performance_monitoring": True      # 性能监控开关
}

# 全局性能统计
_telegram_push_stats = {
    "total_pushes": 0,
    "successful_pushes": 0,
    "failed_pushes": 0,
    "avg_processing_time": 0.0,
    "max_processing_time": 0.0,
    "min_processing_time": float('inf'),
    "last_push_timestamp": None
}

def get_bq_client():
    """获取BigQuery客户端(懒加载)"""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(
            project='wprojectl',
            location='us-central1'
        )
    return _bq_client

def get_secret_client():
    """获取Secret Manager客户端(懒加载)"""
    global _secret_client
    if _secret_client is None:
        _secret_client = secretmanager.SecretManagerServiceClient()
    return _secret_client

def get_cloud_logger():
    """获取Cloud Logging客户端(懒加载)"""
    global _logging_client, _cloud_logger
    if _cloud_logger is None:
        _logging_client = cloud_logging.Client(project='wprojectl')
        _cloud_logger = _logging_client.logger('drawsguard-api-collector-smart')
    return _cloud_logger


def update_telegram_push_stats(processing_time: float, success: bool):
    """
    更新Telegram推送性能统计

    Args:
        processing_time: 处理耗时(秒)
        success: 是否成功
    """
    global _telegram_push_stats

    if TELEGRAM_PUSH_CONFIG["performance_monitoring"]:
        _telegram_push_stats["total_pushes"] += 1

        if success:
            _telegram_push_stats["successful_pushes"] += 1
        else:
            _telegram_push_stats["failed_pushes"] += 1

        # 更新时间统计
        _telegram_push_stats["max_processing_time"] = max(
            _telegram_push_stats["max_processing_time"], processing_time
        )
        _telegram_push_stats["min_processing_time"] = min(
            _telegram_push_stats["min_processing_time"], processing_time
        )

        # 计算平均值
        total_time = (
            _telegram_push_stats["avg_processing_time"] *
            (_telegram_push_stats["total_pushes"] - 1) +
            processing_time
        )
        _telegram_push_stats["avg_processing_time"] = total_time / _telegram_push_stats["total_pushes"]
        _telegram_push_stats["last_push_timestamp"] = datetime.now(SHANGHAI_TZ).isoformat()


def get_telegram_push_stats() -> Dict[str, Any]:
    """获取Telegram推送性能统计"""
    return _telegram_push_stats.copy()

@sync_retry()
def get_api_key():
    """从Secret Manager获取API密钥"""
    try:
        client = get_secret_client()
        name = "projects/wprojectl/secrets/pc28-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"获取API密钥失败: {e}")
        raise

@sync_retry()
def get_telegram_config():
    """从Secret Manager获取Telegram配置"""
    try:
        client = get_secret_client()

        # 获取bot token
        token_name = "projects/wprojectl/secrets/telegram-bot-token/versions/latest"
        token_response = client.access_secret_version(request={"name": token_name})
        bot_token = token_response.payload.data.decode("UTF-8").strip()  # 去除首尾空白字符和换行

        # 获取chat id
        chat_name = "projects/wprojectl/secrets/telegram-chat-id/versions/latest"
        chat_response = client.access_secret_version(request={"name": chat_name})
        chat_id = chat_response.payload.data.decode("UTF-8").strip()  # 去除首尾空白字符和换行

        return bot_token, chat_id
    except Exception as e:
        logger.warning(f"⚠️ 获取Telegram配置失败: {e}")
        return None, None

async def send_telegram_lottery_result_async(period: str, numbers: list, sum_value: int, big_small: str, odd_even: str):
    """
    异步发送开奖结果到Telegram(使用BackgroundTasks)

    Args:
        period: 期号
        numbers: 开奖号码(3个数字)
        sum_value: 和值
        big_small: 大小
        odd_even: 奇偶
    """
    start_time = time.time()
    trace_id = f"telegram_{period}_{int(start_time)}"

    try:
        logger.info(f"🔄 开始异步Telegram推送: 期号{period} (trace_id: {trace_id})")

        # 获取Telegram配置
        bot_token, chat_id = get_telegram_config()
        if not bot_token or not chat_id:
            logger.info(f"ℹ️ Telegram未配置,跳过推送 (trace_id: {trace_id})")
            return

        # 构造精美的开奖消息
        message = (
            f"🎰 **PC28开奖播报**\n\n"
            f"📅 期号: `{period}`\n"
            f"🎲 号码: `{numbers[0]} + {numbers[1]} + {numbers[2]}`\n"
            f"➕ 和值: `{sum_value}`\n"
            f"📊 大小: `{big_small}`\n"
            f"📈 奇偶: `{odd_even}`\n\n"
            f"⏰ 时间: {datetime.now(SHANGHAI_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)\n"
            f"🔗 追踪ID: `{trace_id}`"
        )

        # 异步发送到Telegram(带重试机制)
        await _send_telegram_with_retry(bot_token, chat_id, message, period, trace_id)

        processing_time = time.time() - start_time
        logger.info(f"✅ Telegram开奖推送成功: 期号{period} (耗时: {processing_time:.2f}秒, trace_id: {trace_id})")

        # 更新性能统计
        update_telegram_push_stats(processing_time, success=True)

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"❌ Telegram推送失败: 期号{period} (耗时: {processing_time:.2f}秒, trace_id: {trace_id}, 错误: {e})"
        )

        # 更新性能统计(失败)
        update_telegram_push_stats(processing_time, success=False)

        # 发送失败通知到备用渠道(可选)
        await _send_failure_notification(period, str(e), trace_id)


async def send_stale_upstream_alert_async(alert: dict):
    """
    异步发送上游停更警告到Telegram
    """
    start_time = time.time()
    period = alert.get("stale_period")
    trace_id = f"stale_alert_{period}_{int(start_time)}"

    try:
        # 1. 格式化告警消息 (安全拼接方式)
        msg_title = "[WARNING] Upstream STALE - rijb.api.storeapi.net"
        msg_time = f"Time: {alert.get('detected_at')}"
        msg_collector = f"Collector: {alert.get('collector')}"
        msg_observed = f"Observed: 连续 {alert.get('consecutive_count')} 次返回期号 {period}（已存在 DB，MERGE skip）"
        msg_action = "Action: 请联系上游确认是否停止更新；若 4 小时内仍未恢复，将 escalate 为 P0。"
        message = f"{msg_title}\n\n{msg_time}\n{msg_collector}\n{msg_observed}\n\n{msg_action}"

        logger.info(f"准备发送上游停更警告: 期号={period} (trace_id: {trace_id})")

        # 2. 获取配置并发送
        bot_token, chat_id = get_telegram_config()
        if not bot_token or not chat_id:
            logger.info(f"ℹ️ Telegram未配置,跳过上游停更警告推送 (trace_id: {trace_id})")
            return

        await _send_telegram_with_retry(bot_token, chat_id, message, str(period), trace_id)

        processing_time = time.time() - start_time
        logger.info(f"✅ 上游停更警告推送成功: 期号={period} (耗时: {processing_time:.2f}秒, trace_id: {trace_id})")

    except Exception as e:
        logger.error(f"❌ 上游停更警告推送失败: 期号={period} (trace_id: {trace_id}, 错误: {e})")


@async_retry(max_retries=3)
async def _send_telegram_with_retry(bot_token: str, chat_id: str, message: str, period: str, trace_id: str):
    """
    带重试机制的Telegram发送(异步)

    Args:
        bot_token: Telegram机器人令牌
        chat_id: 聊天ID
        message: 消息内容
        period: 期号(用于日志)
        trace_id: 追踪ID
        max_retries: 最大重试次数
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_notification': False
    }

    try:
        # 使用aiohttp进行异步HTTP请求(如果可用)
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                if result.get('ok'):
                    logger.info(f"📱 Telegram推送成功: 期号{period} (trace_id: {trace_id})")
                    return True
                else:
                    logger.warning(f"⚠️ Telegram API返回非成功: {result} (trace_id: {trace_id})")
                    raise Exception(f"Telegram API Error: {result}") from None

    except ImportError:
        # 降级使用requests(同步,但仍然是非阻塞的)
        logger.info(f"🔄 使用同步requests发送Telegram (trace_id: {trace_id})")
        response = await asyncio.to_thread(requests.post, url, json=payload, timeout=5)
        response.raise_for_status()

        result = response.json()
        if result.get('ok'):
            logger.info(f"📱 Telegram推送成功: 期号{period}, (trace_id: {trace_id})")
            return True
        else:
            logger.warning(f"⚠️ Telegram API返回非成功: {result} (trace_id: {trace_id})")
            raise Exception(f"Telegram API Error: {result}") from None


async def _send_failure_notification(period: str, error_msg: str, trace_id: str):
    """
    发送推送失败通知到备用渠道(异步)

    Args:
        period: 期号
        error_msg: 错误信息
        trace_id: 追踪ID
    """
    try:
        # 这里可以集成其他通知方式,如邮件、Slack等
        logger.warning(f"🚨 Telegram推送失败通知: 期号{period}, 错误: {error_msg} (trace_id: {trace_id})")

        # 示例:发送到Cloud Logging(结构化日志)
        cloud_logger = get_cloud_logger()
        cloud_logger.log_struct({
            "severity": "WARNING",
            "message": "Telegram推送失败",
            "period": period,
            "error": error_msg,
            "trace_id": trace_id,
            "notification_type": "telegram_failure"
        })

    except Exception as e:
        logger.error(f"❌ 发送失败通知也失败了: {e} (trace_id: {trace_id})")


async def send_prediction_result_async(orders: List[Dict[str, Any]], period: str = None):
    """
    异步发送预测结果到Telegram(使用BackgroundTasks)

    Args:
        orders: 预测订单列表
        period: 期号(可选,用于日志)
    """
    start_time = time.time()
    trace_id = f"prediction_{period or 'batch'}_{int(start_time)}"

    try:
        logger.info(f"🔮 开始异步预测结果推送: 订单数{len(orders)} (trace_id: {trace_id})")

        # 获取Telegram配置
        bot_token, chat_id = get_telegram_config()
        if not bot_token or not chat_id:
            logger.info(f"ℹ️ Telegram未配置,跳过预测结果推送 (trace_id: {trace_id})")
            return

        # 构造预测结果消息
        message = build_prediction_message(orders, period, trace_id)

        # 异步发送预测结果
        await _send_telegram_with_retry(bot_token, chat_id, message, period or "batch", trace_id)

        processing_time = time.time() - start_time
        logger.info(f"✅ 预测结果推送成功: {len(orders)}个订单 (耗时: {processing_time:.2f}秒, trace_id: {trace_id})")

        # 更新性能统计
        update_telegram_push_stats(processing_time, success=True)

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ 预测结果推送失败: {len(orders)}个订单 (耗时: {processing_time:.2f}秒, trace_id: {trace_id}, 错误: {e})")

        # 更新性能统计(失败)
        update_telegram_push_stats(processing_time, success=False)

        # 发送失败通知
        await _send_failure_notification(period or "batch", str(e), trace_id)


def build_prediction_message(orders: List[Dict[str, Any]], period: str = None, trace_id: str = None) -> str:
    """
    构建预测结果消息

    Args:
        orders: 预测订单列表
        period: 期号
        trace_id: 追踪ID

    Returns:
        格式化的消息文本
    """
    if not orders:
        return "🤖 **PC28预测结果**\n\n📭 无预测订单生成\n\n⏰ 请等待下一期预测"

    # 按市场分组统计
    market_stats = {}
    for order in orders:
        market = order.get('market', 'unknown')
        if market not in market_stats:
            market_stats[market] = []
        market_stats[market].append(order)

    # 构建消息
    lines = ["🤖 **PC28预测结果**"]

    if period:
        lines.append(f"\n📅 预测期号: `{period}`")

    lines.append("\n📊 预测订单详情:")
    lines.append(f"📈 总订单数: `{len(orders)}`")

    for market, market_orders in market_stats.items():
        lines.append(f"\n🏪 市场: `{market.upper()}`")
        lines.append(f"📋 订单数量: `{len(market_orders)}`")

        # 显示前3个订单的详细信息
        for i, order in enumerate(market_orders[:3]):
            stake = order.get('stake_u', 0)
            prob = order.get('p_win', 0)
            ev = order.get('ev', 0)
            lines.append(f"  {i+1}. 概率: `{prob:.2%}`, EV: `{ev:.2%}`, 金额: `{stake}`U")

        if len(market_orders) > 3:
            lines.append(f"  ... 还有 {len(market_orders) - 3} 个订单")

    lines.append(f"\n⏰ 时间: {datetime.now(SHANGHAI_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")

    if trace_id:
        lines.append(f"🔗 追踪ID: `{trace_id}`")

    return "\n".join(lines)


# 同步版本(用于兼容性)
def send_prediction_result(orders: List[Dict[str, Any]], period: str = None):
    """
    同步发送预测结果消息(用于非FastAPI环境)

    注意: 此函数是阻塞的,仅用于兼容性
    """
    try:
        bot_token, chat_id = get_telegram_config()
        if not bot_token or not chat_id:
            logger.info("ℹ️ Telegram未配置,跳过预测结果推送")
            return False

        # 构造预测结果消息
        message = build_prediction_message(orders, period)

        # 发送到Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_notification': False
        }

        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()

        logger.info(f"✅ 预测结果推送成功: {len(orders)}个订单")
        return True

    except Exception as e:
        logger.error(f"❌ 预测结果推送失败: {e}")
        return False


# 同步版本(用于兼容性)
def send_telegram_lottery_result(period: str, numbers: list, sum_value: int, big_small: str, odd_even: str):
    """
    同步发送Telegram消息(用于非FastAPI环境)

    注意: 此函数是阻塞的,仅用于兼容性
    """
    try:
        bot_token, chat_id = get_telegram_config()
        if not bot_token or not chat_id:
            logger.info("ℹ️ Telegram未配置,跳过推送")
            return False

        # 构造精美的开奖消息
        message = (
            f"🎰 **PC28开奖播报**\n\n"
            f"📅 期号: `{period}`\n"
            f"🎲 号码: `{numbers[0]} + {numbers[1]} + {numbers[2]}`\n"
            f"➕ 和值: `{sum_value}`\n"
            f"📊 大小: `{big_small}`\n"
            f"📈 奇偶: `{odd_even}`\n\n"
            f"⏰ 时间: {datetime.now(SHANGHAI_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)"
        )

        # 发送到Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_notification': False
        }

        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()

        logger.info(f"✅ Telegram开奖推送成功: 期号{period}")
        return True

    except Exception as e:
        logger.error(f"❌ Telegram推送失败: {e}")
        return False

def generate_sign(params: dict, api_key: str) -> str:
    """生成API签名"""
    filtered_params = {k: v for k, v in params.items() if v is not None and v != ''}
    sorted_keys = sorted(filtered_params.keys())
    sign_string = ''.join([f"{k}{filtered_params[k]}" for k in sorted_keys])
    sign_string += api_key
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest()


@sync_retry(max_retries=3)
def call_api_with_retry(api_url: str, params: dict, api_key: str) -> dict:
    """调用API(带重试机制和签名)"""
    try:
        # 1. 为本次请求加入时间戳，这是签名的一部分
        params['time'] = int(time.time())

        # 2. 生成签名
        sign = generate_sign(params, api_key)

        # 3. 将签名加入到最终的请求参数中
        params['sign'] = sign

        logger.info(f"API调用: params={params}")

        response = requests.get(
            api_url,
            params=params,
            timeout=30,
            headers={'User-Agent': 'DrawsGuard/4.0-Smart'}
        )
        response.raise_for_status()
        data = response.json()
        logger.info("✅ API调用成功")
        return data

    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
        logger.warning(f"⚠️ API调用超时: {str(e)}")
        raise  # Re-raise to be caught by the retry decorator

    except Exception as e:
        logger.error(f"API调用出错: {str(e)}")
        raise  # Re-raise to be caught by the retry decorator


def _insert_draw_with_merge(bq_client: bigquery.Client, row: Dict[str, Any]) -> str:
    """
    Inserts a single draw record into BigQuery using a MERGE statement for atomic upsert.

    Args:
        bq_client: The BigQuery client.
        row: A dictionary representing the row to be inserted.

    Returns:
        A string indicating the result: 'inserted' or 'skipped'.
    """
    table_id = "wprojectl.drawsguard.draws"

    # Using MERGE for atomic "insert if not exists"
    merge_sql = f"""
    MERGE `{table_id}` T
    USING (
        SELECT
            @period AS period,
            @timestamp AS timestamp,
            @numbers AS numbers,
            @sum_value AS sum_value,
            @big_small AS big_small,
            @odd_even AS odd_even,
            @next_issue AS next_issue,
            @next_time AS next_time,
            @award_countdown AS award_countdown,
            @api_server_time AS api_server_time,
            @clock_drift_ms AS clock_drift_ms,
            @created_at AS created_at,
            @updated_at AS updated_at
    ) S
    ON T.period = S.period
    WHEN NOT MATCHED THEN
      INSERT (
          period, timestamp, numbers, sum_value, big_small, odd_even,
          next_issue, next_time, award_countdown, api_server_time,
          clock_drift_ms, created_at, updated_at
      )
      VALUES (
          S.period, S.timestamp, S.numbers, S.sum_value, S.big_small, S.odd_even,
          S.next_issue, S.next_time, S.award_countdown, S.api_server_time,
          S.clock_drift_ms, S.created_at, S.updated_at
      )
    """

    # Pydantic model guarantees correct types, but BQ API needs specific formats
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("period", "STRING", row["period"]),
            bigquery.ScalarQueryParameter("timestamp", "TIMESTAMP", row["timestamp"]),
            bigquery.ArrayQueryParameter("numbers", "INT64", row["numbers"]),
            bigquery.ScalarQueryParameter("sum_value", "INT64", row["sum_value"]),
            bigquery.ScalarQueryParameter("big_small", "STRING", row["big_small"]),
            bigquery.ScalarQueryParameter("odd_even", "STRING", row["odd_even"]),
            bigquery.ScalarQueryParameter("next_issue", "STRING", row["next_issue"]),
            bigquery.ScalarQueryParameter("next_time", "TIMESTAMP", row["next_time"]),
            bigquery.ScalarQueryParameter("award_countdown", "INT64", row["award_countdown"]),
            bigquery.ScalarQueryParameter("api_server_time", "TIMESTAMP", row["api_server_time"]),
            bigquery.ScalarQueryParameter("clock_drift_ms", "INT64", row["clock_drift_ms"]),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", row["created_at"]),
            bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", row["updated_at"]),
        ]
    )

    query_job = bq_client.query(merge_sql, job_config=job_config)
    query_job.result()  # Wait for the job to complete

    if query_job.num_dml_affected_rows > 0:
        return "inserted"
    else:
        return "skipped"

def parse_and_insert_data(api_data: dict, bq_client: bigquery.Client, cloud_logger, background_tasks: BackgroundTasks, collection_mode: str = "normal") -> dict:
    """
    解析API数据并插入BigQuery
    
    Args:
        api_data: API返回数据
        bq_client: BigQuery客户端
        cloud_logger: Cloud Logging客户端
        collection_mode: 采集模式(normal/intensive/energy_save)
        
    Returns:
        执行结果统计
    """
    try:
        # 提取数据
        curent = api_data.get('retdata', {}).get('curent', {})
        next_data = api_data.get('retdata', {}).get('next', {})

        # 基础字段
        period = str(curent.get('long_issue', ''))
        kjtime_str = curent.get('kjtime', '')
        numbers = curent.get('number', [])

        # 🛡️ 上游停更检测器 (Upstream Stale Detector)
        # 在解析核心数据后立刻执行,但不阻塞主流程
        try:
            # 仅当期号有效时才运行检测器
            if period and period.isdigit():
                returned_period_int = int(period)
                response_json_str = json.dumps(api_data)

                # 同步执行检测和BQ日志记录
                alert = detect_and_handle_upstream_stale(
                    collector_name="drawsguard-api-collector",
                    returned_period=returned_period_int,
                    response_json=response_json_str
                )

                # 如果检测到停更,则异步发送警告
                if alert:
                    logger.warning(f"⚠️ 检测到上游停更,已生成警告: {alert}")
                    background_tasks.add_task(send_stale_upstream_alert_async, alert)
            else:
                logger.debug(f"跳过上游停更检测，无效的期号: '{period}'")

        except (ValueError, TypeError) as e:
            logger.warning(f"无法为上游停更检测器准备数据: period='{period}', error={e}")
        except Exception as e:
            logger.error(f"上游停更检测器任务调度失败: {e}", exc_info=True)

        # 新增字段
        next_issue = str(next_data.get('next_issue', ''))
        next_time_str = next_data.get('next_time', '')
        award_countdown = int(next_data.get('award_time', 0))

        # curtime字段处理(100%字段利用率)- 优化时钟漂移检测
        api_curtime = api_data.get('curtime', 0)
        local_timestamp = datetime.now(UTC_TZ)

        if api_curtime:
            api_server_time = datetime.fromtimestamp(int(api_curtime), tz=UTC_TZ)
            raw_drift_ms = int((local_timestamp.timestamp() - api_server_time.timestamp()) * 1000)

            # 优化时钟漂移计算:考虑网络延迟,减少误报
            # 假设网络延迟在0-1000ms之间,时钟漂移不应超过±2000ms
            if abs(raw_drift_ms) <= 2000:
                clock_drift_ms = raw_drift_ms
            else:
                # 超过阈值时,取网络延迟的中位数作为漂移估计
                clock_drift_ms = 500 if raw_drift_ms > 0 else -500  # 保守估计
                drift_warning = f"⚠️ 时钟漂移异常: {raw_drift_ms}ms → 校正为{clock_drift_ms}ms (本地={local_timestamp.isoformat()}, API={api_server_time.isoformat()})"
                logger.warning(drift_warning)
                cloud_logger.log_text(drift_warning, severity='WARNING')

            # 时钟漂移告警(仅对显著漂移告警)
            if abs(clock_drift_ms) > 1000:
                drift_info = f"时钟漂移: {clock_drift_ms}ms"
                logger.info(f"⏰ {drift_info}")
        else:
            api_server_time = None
            clock_drift_ms = None

        if not period or not kjtime_str or not numbers:
            raise ValueError("关键字段缺失")

        # 时间转换(上海时区 → UTC)
        naive_dt = datetime.strptime(kjtime_str, "%Y-%m-%d %H:%M:%S")
        aware_dt = SHANGHAI_TZ.localize(naive_dt)
        timestamp_utc = aware_dt.astimezone(UTC_TZ)

        # next_time转换
        if next_time_str:
            next_naive = datetime.strptime(next_time_str, "%Y-%m-%d %H:%M:%S")
            next_aware = SHANGHAI_TZ.localize(next_naive)
            next_time_utc = next_aware.astimezone(UTC_TZ)
        else:
            next_time_utc = None

        # 号码处理
        numbers_int = [int(n) for n in numbers]
        sum_value = sum(numbers_int)
        big_small = "BIG" if sum_value >= 14 else "SMALL"  # 优化:使用大写(符合TECHNICAL_SPECS规范)
        odd_even = "EVEN" if sum_value % 2 == 0 else "ODD"  # 优化:使用大写

        # 构造行数据(100%字段利用率)
        raw_row = {
            "period": period,
            "timestamp": timestamp_utc,
            "numbers": numbers_int,
            "sum_value": sum_value,
            "big_small": big_small,
            "odd_even": odd_even,
            "next_issue": next_issue,
            "next_time": next_time_utc,
            "award_countdown": award_countdown,
            "api_server_time": api_server_time,
            "clock_drift_ms": clock_drift_ms,
            "created_at": local_timestamp,
            "updated_at": local_timestamp,
        }

        # 🛡️ 在插入前进行严格的数据验证
        try:
            validated_row = BigQueryDrawRow.model_validate(raw_row)
            # 使用经过验证和序列化的数据进行插入，确保类型安全
            row_to_insert = validated_row.model_dump(mode='json')
        except ValidationError as e:
            error_msg = f"数据验证失败: period={period}, errors={e}"
            logger.error(error_msg)
            cloud_logger.log_text(error_msg, severity='CRITICAL') # 提升告警等级
            return {"success": False, "error": "Data validation failed", "details": str(e)}


        # Atomically insert the row using a MERGE statement
        insert_status = _insert_draw_with_merge(bq_client, row_to_insert)

        if insert_status == "skipped":
            duplicate_warning = f"⚠️ 期号重复(已通过MERGE跳过): period={period}"
            logger.warning(duplicate_warning)
            cloud_logger.log_text(duplicate_warning, severity='WARNING')

            return {
                "success": True,
                "period": period,
                "status": "duplicate_skipped",
                "next_issue": next_issue,
                "award_countdown": award_countdown,
                "collection_mode": collection_mode
            }

        # 根据模式记录日志(包含时钟漂移信息)
        mode_emoji = {"normal": "🟢", "intensive": "🔴", "energy_save": "🔵"}.get(collection_mode, "⚪")
        drift_info = f", drift={clock_drift_ms}ms" if clock_drift_ms is not None else ""
        logger.info(
            f"{mode_emoji} 数据插入成功 [{collection_mode.upper()}]: "
            f"期号={period}, next={next_issue}, countdown={award_countdown}s{drift_info}"
        )
        cloud_logger.log_text(
            f"[{collection_mode}] period={period}, next={next_issue}, countdown={award_countdown}, clock_drift={clock_drift_ms}ms",
            severity='INFO'
        )

        # 🎰 实时推送开奖结果到Telegram(真正的异步,不阻塞主流程)
        # 使用BackgroundTasks实现真正的非阻塞推送
        background_tasks.add_task(
            send_telegram_lottery_result_async,
            period,
            numbers_int,
            sum_value,
            big_small,
            odd_even
        )
        logger.info(f"📱 Telegram推送任务已加入后台队列: 期号{period} (主流程继续执行)")

        # 连续性检查
        continuity_status = "pass"
        if next_issue:
            expected_next = str(int(period) + 1)
            if next_issue != expected_next:
                warning_msg = f"⚠️ 期号不连续！当前={period}, 预期={expected_next}, 实际={next_issue}"
                logger.warning(warning_msg)
                cloud_logger.log_text(warning_msg, severity='WARNING')
                continuity_status = "warning"

        return {
            "success": True,
            "period": period,
            "next_issue": next_issue,
            "award_countdown": award_countdown,
            "continuity_check": continuity_status,
            "collection_mode": collection_mode,
            "clock_drift_ms": clock_drift_ms
        }

    except Exception as e:
        error_msg = f"数据处理失败: {str(e)}"
        logger.error(error_msg)
        cloud_logger.log_text(error_msg, severity='ERROR')
        return {"success": False, "error": str(e)}

def schedule_intensive_collection(countdown: int, api_key: str, bq_client, cloud_logger, background_tasks: BackgroundTasks):
    """
    密集采集模式:在开奖前60秒触发额外采集(优化延迟)

    Args:
        countdown: 当前距离开奖的秒数
        api_key: API密钥
        bq_client: BigQuery客户端
        cloud_logger: Cloud Logging客户端
        background_tasks: FastAPI后台任务
    """
    logger.info(f"🔴 进入密集采集模式(countdown={countdown}秒)")
    cloud_logger.log_text(f"进入密集采集模式: countdown={countdown}", severity='INFO')

    # 优化采集策略:基于倒计时动态调整间隔
    intervals = []
    if countdown > 50:
        intervals = [10, 10, 10]  # 在50秒、40秒、30秒时采集
    elif countdown > 30:
        intervals = [countdown - 30, 10, 10]  # 在30秒、20秒、10秒时采集
    elif countdown > 15:
        intervals = [countdown - 15, 10]  # 在15秒、5秒时采集
    else:
        intervals = [max(countdown - 3, 1)]  # 立即采集

    logger.info(f"📅 密集采集计划: {len(intervals)}次, 间隔={intervals}")

    # 执行密集采集(带延迟监控)
    api_url = "https://rijb.api.storeapi.net/api/119/259"
    for i, wait_time in enumerate(intervals):
        time.sleep(wait_time)

        # 采集前记录时间
        collect_start = time.time()

        try:
            current_time = str(int(time.time()))
            params = {
                'appid': '45928',
                'format': 'json',
                'time': current_time
            }
            params['sign'] = generate_sign(params, api_key)

            data = call_api_with_retry(api_url, params, api_key)

            if data.get('codeid') == 10000:
                result = parse_and_insert_data(data, bq_client, cloud_logger, background_tasks, collection_mode="intensive")

                # 计算采集延迟
                collect_delay = time.time() - collect_start
                logger.info(f"✅ 密集采集 {i+1}/{len(intervals)} 完成 (延迟: {collect_delay:.1f}秒)")

                # 如果延迟过大,记录警告
                if collect_delay > MAX_ACCEPTABLE_DELAY:
                    delay_warning = f"⚠️ 密集采集延迟较大: {collect_delay:.1f}秒 > {MAX_ACCEPTABLE_DELAY}秒"
                    logger.warning(delay_warning)
                    cloud_logger.log_text(delay_warning, severity='WARNING')
            else:
                logger.warning(f"⚠️ 密集采集 {i+1}/{len(intervals)} API返回错误: {data.get('message')}")

        except Exception as e:
            logger.error(f"❌ 密集采集 {i+1}/{len(intervals)} 失败: {str(e)}")

    logger.info("🔴 密集采集模式结束")

@app.get("/telegram-stats")
async def get_telegram_stats():
    """
    获取Telegram推送性能统计
    用于监控异步推送的性能表现
    """
    stats = get_telegram_push_stats()

    # 计算成功率
    success_rate = 0.0
    if stats["total_pushes"] > 0:
        success_rate = (stats["successful_pushes"] / stats["total_pushes"]) * 100

    return {
        "service": "DrawsGuard API Collector v5.2",
        "version": "5.2.0",
        "telegram_push_stats": {
            "total_pushes": stats["total_pushes"],
            "successful_pushes": stats["successful_pushes"],
            "failed_pushes": stats["failed_pushes"],
            "success_rate_percent": round(success_rate, 2),
            "avg_processing_time_seconds": round(stats["avg_processing_time"], 3),
            "max_processing_time_seconds": round(stats["max_processing_time"], 3),
            "min_processing_time_seconds": round(stats["min_processing_time"], 3) if stats["min_processing_time"] != float('inf') else 0,
            "last_push_timestamp": stats["last_push_timestamp"],
            "config": TELEGRAM_PUSH_CONFIG
        },
        "features": [
            "🎰 Real-time Telegram push (true async with BackgroundTasks)",
            "🔄 Retry mechanism with exponential backoff",
            "📊 Performance monitoring and statistics",
            "🚨 Failure notification system",
            "⚡ Zero-blocking main process",
            "🤖 Prediction results push to Telegram"
        ],
        "timestamp": datetime.now(SHANGHAI_TZ).isoformat()
    }

@app.get("/health", response_model=HealthCheckResponse, tags=["Monitoring"])
async def health_check():
    """
    Provides a simple health check endpoint.

    This endpoint can be used by load balancers or uptime monitors (like Google
    Cloud Monitoring liveness probes) to verify that the service is running
    and responsive. It returns a simple JSON response with a 200 OK status.
    """
    return HealthCheckResponse(status="ok")

@app.get("/heartbeat")
async def heartbeat():
    """
    心跳监控端点
    
    检查项:
    1. BigQuery连接状态
    2. 最近10分钟数据插入情况
    3. 最近30分钟期号连续性
    4. 服务健康度评分
    
    Returns:
        JSON响应,包含详细的健康状态
    """
    try:
        bq_client = get_bq_client()

        # 1. 测试BigQuery连接
        test_query = "SELECT 1 AS test"
        list(bq_client.query(test_query).result())
        bq_connection = "healthy"

        # 2. 检查最近插入情况
        recent_insert_query = """
        SELECT 
          COUNT(*) AS recent_count,
          MAX(created_at) AS last_insert,
          TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(created_at), SECOND) AS seconds_since_last
        FROM `wprojectl.drawsguard.draws`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
        """

        insert_result = list(bq_client.query(recent_insert_query).result())[0]
        recent_count = insert_result['recent_count']
        seconds_since_last = insert_result['seconds_since_last']
        last_insert = insert_result['last_insert'].isoformat() if insert_result['last_insert'] else None

        # 3. 检查期号连续性(最近30分钟)
        continuity_query = """
        WITH recent AS (
          SELECT CAST(period AS INT64) AS period_int
          FROM `wprojectl.drawsguard.draws`
          WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE)
          ORDER BY period_int
        ),
        gaps AS (
          SELECT 
            period_int,
            LEAD(period_int) OVER (ORDER BY period_int) - period_int - 1 AS gap
          FROM recent
        )
        SELECT COUNT(*) AS gap_count
        FROM gaps
        WHERE gap > 0
        """

        continuity_result = list(bq_client.query(continuity_query).result())
        gap_count = continuity_result[0]['gap_count'] if continuity_result else 0

        # 4. 评估健康状态
        health_score = 100
        issues = []

        if seconds_since_last > 600:  # 10分钟无数据
            health_score -= 50
            issues.append("10分钟内无新数据")
        elif seconds_since_last > 300:  # 5分钟无数据
            health_score -= 20
            issues.append("5分钟内无新数据")

        if gap_count > 0:
            health_score -= 30
            issues.append(f"最近30分钟发现{gap_count}个缺口")

        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "service": "drawsguard-api-collector",
            "version": "5.2.0",
            "health_score": health_score,
            "bigquery_connection": bq_connection,
            "recent_inserts": recent_count,
            "seconds_since_last_insert": seconds_since_last,
            "last_insert": last_insert,
            "gap_count_30min": gap_count,
            "issues": issues if issues else None,
            "telegram_push": "enabled",
            "timestamp": datetime.now(SHANGHAI_TZ).isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "service": "drawsguard-api-collector",
            "error": str(e),
            "timestamp": datetime.now(SHANGHAI_TZ).isoformat()
        }

@app.post("/collect")
async def collect(background_tasks: BackgroundTasks):
    """智能采集端点"""
    try:
        logger.info("="*60)
        logger.info("开始智能采集")
        logger.info("="*60)

        # 1. 获取API密钥
        api_key = get_api_key()
        logger.info("✅ API密钥获取成功")

        # 2. 准备API参数
        current_time = str(int(time.time()))
        params = {
            'appid': '45928',
            'format': 'json',
            'time': current_time
        }
        params['sign'] = generate_sign(params, api_key)

        # 3. 调用API(带重试)
        api_url = "https://rijb.api.storeapi.net/api/119/259"
        data = call_api_with_retry(api_url, params, api_key)

        # 4. 验证返回数据
        if data.get('codeid') != 10000:
            error_msg = f"API返回错误: {data.get('message', '未知错误')}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg) from None

        # 5. 解析并插入数据
        bq_client = get_bq_client()
        cloud_logger = get_cloud_logger()

        # 确定采集模式
        countdown = data.get('retdata', {}).get('next', {}).get('award_time', 999)
        if 0 < countdown <= INTENSIVE_MODE_THRESHOLD:
            collection_mode = "intensive"
        elif countdown <= ENERGY_SAVE_THRESHOLD:
            collection_mode = "energy_save"
        else:
            collection_mode = "normal"

        result = parse_and_insert_data(data, bq_client, cloud_logger, background_tasks, collection_mode=collection_mode)

        # 6. 智能调度逻辑
        if result.get('success'):
            countdown = result.get('award_countdown', 999)

            # 密集采集模式(开奖前60秒)
            if 0 < countdown <= INTENSIVE_MODE_THRESHOLD:
                # 使用后台任务避免阻塞
                logger.info(f"触发密集采集后台任务 (countdown={countdown}s)")
                background_tasks.add_task(
                    schedule_intensive_collection,
                    countdown,
                    api_key,
                    bq_client,
                    cloud_logger,
                    background_tasks
                )

            # 节能模式(开奖后5分钟)
            elif countdown <= ENERGY_SAVE_THRESHOLD:
                logger.info(f"🔵 节能模式:countdown={countdown}秒,无需额外操作")
                cloud_logger.log_text(f"节能模式: countdown={countdown}", severity='INFO')

        # 7. 同步到pc28.draws (优化: 后台任务)
        background_tasks.add_task(sync_to_pc28_draws, result.get('period'))

        logger.info("="*60)
        logger.info("智能采集完成")
        logger.info("="*60)

        return {
            "status": "success",
            "timestamp": datetime.now(UTC_TZ).isoformat(),
            "result": result
        }

    except Exception as e:
        logger.error(f"采集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e

async def sync_to_pc28_draws(period: str):
    """
    异步同步单期数据到 pc28.draws (后台任务)
    """
    if not period:
        return

    try:
        bq_client = get_bq_client()
        sync_query = """
        MERGE `wprojectl.pc28.draws` AS target
        USING (
          SELECT * FROM `wprojectl.drawsguard.draws`
          WHERE period = @period
          ORDER BY timestamp DESC
          LIMIT 1
        ) AS source
        ON target.period = source.period
        WHEN NOT MATCHED THEN
          INSERT (period, timestamp, numbers, sum_value, big_small, odd_even)
          VALUES (source.period, source.timestamp, source.numbers, source.sum_value, source.big_small, source.odd_even)
        WHEN MATCHED THEN
          UPDATE SET
            timestamp = source.timestamp,
            numbers = source.numbers,
            sum_value = source.sum_value,
            big_small = source.big_small,
            odd_even = source.odd_even
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("period", "STRING", period)
            ]
        )
        query_job = bq_client.query(sync_query, job_config=job_config)
        await asyncio.to_thread(query_job.result) # 异步等待结果

        logger.info(f"✅ [后台同步] pc28.draws成功: 期号={period}")
    except Exception as e:
        logger.warning(f"⚠️ [后台同步] pc28.draws失败: 期号={period}, 错误: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

